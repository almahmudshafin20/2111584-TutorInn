from datetime import timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import (
    enforce_auth_rate_limit, hash_password, record_security_event,
    require_roles, timestamp, token_hash, utc_now, verify_password,
)
from ..database import get_db
from ..models import PasswordResetRequest, PasswordResetToken, RefreshSession, UserAccount
from ..notifications import send_password_reset_link
from ..schemas import PasswordResetCompleteInput, PasswordResetRequestInput, PasswordResetReviewInput

router = APIRouter(tags=["Password reset"])
GENERIC_REQUEST_MESSAGE = (
    "If an eligible TutorInn account matches that email, a password-reset request has been submitted for review."
)


@router.post("/api/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    payload: PasswordResetRequestInput,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    enforce_auth_rate_limit(
        db, request, "password_reset_request",
        limit_env="PASSWORD_RESET_REQUEST_MAX_ATTEMPTS",
        window_env="PASSWORD_RESET_REQUEST_WINDOW_SECONDS",
        default_limit=5,
        default_window_seconds=3600,
        attempted_email=payload.email,
    )
    account = db.scalar(select(UserAccount).where(UserAccount.email == payload.email))
    if account is not None and account.role in {"student", "tutor"} and account.status == "active" and account.email_verified_at is not None:
        pending = db.scalar(select(PasswordResetRequest).where(
            PasswordResetRequest.account_id == account.id,
            PasswordResetRequest.status == "pending",
        ).order_by(PasswordResetRequest.requested_at.desc()).limit(1))
        if pending is None:
            db.add(PasswordResetRequest(
                account_id=account.id,
                account_email=account.email,
                account_role=account.role,
                status="pending",
                requested_at=timestamp(),
                requested_ip=(request.client.host if request.client else "")[:64],
                requested_user_agent=request.headers.get("user-agent", "")[:512],
            ))
            db.commit()
        record_security_event(
            db, "password_reset_requested", request,
            account_id=account.id, attempted_email=account.email,
        )
    return {"message": GENERIC_REQUEST_MESSAGE}


@router.get("/api/admin/password-reset-requests")
def list_password_reset_requests(
    status_filter: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|completed|all)$"),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: UserAccount = Depends(require_roles("admin", "moderator")),
) -> dict:
    statement = select(PasswordResetRequest)
    if status_filter != "all":
        statement = statement.where(PasswordResetRequest.status == status_filter)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(
        PasswordResetRequest.requested_at.desc(),
        PasswordResetRequest.id.desc(),
    ).offset(offset).limit(limit)).all()
    items = []
    for row in rows:
        reviewer = db.get(UserAccount, row.reviewed_by_account_id) if row.reviewed_by_account_id else None
        items.append({
            "id": row.id,
            "account_id": row.account_id,
            "account_email": row.account_email,
            "account_role": row.account_role,
            "status": row.status,
            "requested_at": row.requested_at,
            "requested_ip": row.requested_ip,
            "reviewed_at": row.reviewed_at,
            "reviewer_email": reviewer.email if reviewer else None,
            "review_note": row.review_note,
        })
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.patch("/api/admin/password-reset-requests/{request_id}")
def review_password_reset_request(
    request_id: int,
    payload: PasswordResetReviewInput,
    request: Request,
    db: Session = Depends(get_db),
    actor: UserAccount = Depends(require_roles("admin", "moderator")),
) -> dict[str, str | int]:
    item = db.scalar(select(PasswordResetRequest).where(
        PasswordResetRequest.id == request_id,
    ).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Password-reset request not found.")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="This password-reset request has already been reviewed.")

    target = db.get(UserAccount, item.account_id)
    if target is None or target.status != "active" or target.role not in {"student", "tutor"} or target.email_verified_at is None:
        raise HTTPException(status_code=409, detail="The target account is no longer eligible for password reset.")

    now = timestamp()
    if payload.status == "rejected":
        item.status = "rejected"
        item.reviewed_by_account_id = actor.id
        item.reviewed_at = now
        item.review_note = payload.review_note
        db.commit()
        record_security_event(
            db, "password_reset_rejected", request,
            account_id=actor.id, attempted_email=target.email,
            details=f"request_id={item.id}; target_account_id={target.id}; reviewer_role={actor.role}",
        )
        return {"id": item.id, "status": item.status, "delivery_status": "not_applicable"}

    raw_token = secrets.token_urlsafe(48)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.account_id == target.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.invalidated_at.is_(None),
    ).update({"invalidated_at": now}, synchronize_session=False)
    db.add(PasswordResetToken(
        request_id=item.id,
        account_id=target.id,
        token_hash=token_hash(raw_token),
        created_at=now,
        expires_at=(utc_now() + timedelta(minutes=30)).isoformat(),
        used_at=None,
        invalidated_at=None,
    ))
    item.status = "approved"
    item.reviewed_by_account_id = actor.id
    item.reviewed_at = now
    item.review_note = payload.review_note
    db.flush()

    try:
        delivered = send_password_reset_link(target.email, raw_token)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="The reset email could not be delivered. No approval or reset token was saved; check the email-provider configuration and try again.") from exc
    if not delivered:
        db.rollback()
        raise HTTPException(status_code=503, detail="Password-reset email delivery is not configured. No approval or reset token was saved.")

    db.commit()
    record_security_event(
        db, "password_reset_approved", request,
        account_id=actor.id, attempted_email=target.email,
        details=f"request_id={item.id}; target_account_id={target.id}; reviewer_role={actor.role}; delivery=sent",
    )
    return {"id": item.id, "status": "approved", "delivery_status": "sent"}


@router.post("/api/auth/password-reset/complete")
def complete_password_reset(
    payload: PasswordResetCompleteInput,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    enforce_auth_rate_limit(
        db, request, "password_reset_complete",
        limit_env="PASSWORD_RESET_COMPLETE_MAX_ATTEMPTS",
        window_env="PASSWORD_RESET_COMPLETE_WINDOW_SECONDS",
        default_limit=10,
        default_window_seconds=3600,
    )
    now = timestamp()
    reset = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash(payload.token),
    ).with_for_update())
    if (
        reset is None or reset.used_at is not None
        or reset.invalidated_at is not None or reset.expires_at <= now
    ):
        record_security_event(db, "password_reset_token_rejected", request)
        raise HTTPException(status_code=400, detail="This password-reset link is invalid, expired or already used.")

    account = db.get(UserAccount, reset.account_id)
    if account is None or account.status != "active" or account.role not in {"student", "tutor"} or account.email_verified_at is None:
        reset.invalidated_at = now
        db.commit()
        record_security_event(db, "password_reset_token_rejected", request, account_id=reset.account_id)
        raise HTTPException(status_code=400, detail="This password-reset link is invalid, expired or already used.")
    if verify_password(payload.new_password, account.password_hash):
        raise HTTPException(status_code=422, detail="Choose a new password different from your current password.")

    account.password_hash = hash_password(payload.new_password)
    account.updated_at = now
    reset.used_at = now
    db.query(PasswordResetToken).filter(
        PasswordResetToken.account_id == account.id,
        PasswordResetToken.id != reset.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.invalidated_at.is_(None),
    ).update({"invalidated_at": now}, synchronize_session=False)
    sessions = db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == account.id,
        RefreshSession.revoked_at.is_(None),
    )).all()
    for session in sessions:
        session.revoked_at = now
    reset_request = db.get(PasswordResetRequest, reset.request_id)
    if reset_request is not None:
        reset_request.status = "completed"
    db.commit()
    record_security_event(db, "password_reset_completed", request, account_id=account.id)
    return {"message": "Your password has been reset. All active sessions were revoked; sign in again."}
