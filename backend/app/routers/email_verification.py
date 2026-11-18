from datetime import timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import enforce_auth_rate_limit, record_security_event, timestamp, token_hash, utc_now
from ..database import get_db
from ..models import EmailVerificationToken, UserAccount
from ..notifications import send_email_verification_link
from ..schemas import EmailVerificationCompleteInput, EmailVerificationRequestInput

router = APIRouter(tags=["Email verification"])
GENERIC_MESSAGE = "If an eligible TutorInn account matches that email, a verification link will be sent when delivery is available."


@router.post("/api/auth/email-verification/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(
    payload: EmailVerificationRequestInput,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    enforce_auth_rate_limit(
        db, request, "email_verification_request",
        limit_env="EMAIL_VERIFICATION_REQUEST_MAX_ATTEMPTS",
        window_env="EMAIL_VERIFICATION_REQUEST_WINDOW_SECONDS",
        default_limit=5, default_window_seconds=3600,
        attempted_email=payload.email,
    )
    account = db.scalar(select(UserAccount).where(UserAccount.email == payload.email))
    if account is None or account.role not in {"student", "tutor"} or account.status != "active" or account.email_verified_at is not None:
        return {"message": GENERIC_MESSAGE}

    now = timestamp()
    raw_token = secrets.token_urlsafe(48)
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.account_id == account.id,
        EmailVerificationToken.used_at.is_(None),
        EmailVerificationToken.invalidated_at.is_(None),
    ).update({"invalidated_at": now}, synchronize_session=False)
    db.add(EmailVerificationToken(
        account_id=account.id, email=account.email, token_hash=token_hash(raw_token),
        created_at=now, expires_at=(utc_now() + timedelta(minutes=30)).isoformat(),
        used_at=None, invalidated_at=None,
    ))
    db.flush()
    try:
        delivered = send_email_verification_link(account.email, raw_token)
    except Exception:
        db.rollback()
        delivered = False
    if not delivered:
        db.rollback()
        record_security_event(db, "email_verification_delivery_unavailable", request, account_id=account.id)
        return {"message": GENERIC_MESSAGE}
    db.commit()
    record_security_event(db, "email_verification_sent", request, account_id=account.id)
    return {"message": GENERIC_MESSAGE}


@router.post("/api/auth/email-verification/complete")
def complete_email_verification(
    payload: EmailVerificationCompleteInput,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    enforce_auth_rate_limit(
        db, request, "email_verification_complete",
        limit_env="EMAIL_VERIFICATION_COMPLETE_MAX_ATTEMPTS",
        window_env="EMAIL_VERIFICATION_COMPLETE_WINDOW_SECONDS",
        default_limit=10, default_window_seconds=3600,
    )
    now = timestamp()
    item = db.scalar(select(EmailVerificationToken).where(
        EmailVerificationToken.token_hash == token_hash(payload.token),
    ).with_for_update())
    if item is None or item.used_at is not None or item.invalidated_at is not None or item.expires_at <= now:
        record_security_event(db, "email_verification_token_rejected", request)
        raise HTTPException(status_code=400, detail="This verification link is invalid, expired or already used.")
    account = db.get(UserAccount, item.account_id)
    if account is None or account.email != item.email or account.status != "active":
        item.invalidated_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="This verification link is invalid, expired or already used.")
    item.used_at = now
    account.email_verified_at = now
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.account_id == account.id,
        EmailVerificationToken.id != item.id,
        EmailVerificationToken.used_at.is_(None),
        EmailVerificationToken.invalidated_at.is_(None),
    ).update({"invalidated_at": now}, synchronize_session=False)
    db.commit()
    record_security_event(db, "email_verified", request, account_id=account.id)
    return {"message": "Email address verified successfully. You can now request a password reset if needed."}
