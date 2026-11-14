import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.database import get_db
    from backend.dependencies import require_admin_key
    from backend.auth import record_security_event, require_roles, timestamp, token_hash
    from backend.models import InterestResponse, Student, Tutor, UserAccount
    from backend.schemas import LegacyClaimIssueInput, ResponseRead
except ModuleNotFoundError:
    import crud
    from database import get_db
    from dependencies import require_admin_key
    from auth import record_security_event, require_roles, timestamp, token_hash
    from models import InterestResponse, Student, Tutor, UserAccount
    from schemas import LegacyClaimIssueInput, ResponseRead

router = APIRouter(tags=["Admin"])


@router.get("/api/admin/matches")
def list_admin_matches(
    review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected)$"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> list[dict]:
    return crud.list_admin_matches(review_status=review_status, db=db)


@router.get("/api/admin/responses", response_model=list[ResponseRead])
def list_admin_responses(
    review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> list[InterestResponse]:
    return crud.list_admin_responses(review_status=review_status, db=db, _=_)


@router.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(
    response_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> InterestResponse:
    return crud.approve_interest(response_id=response_id, db=db, _=_)


@router.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(
    response_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> InterestResponse:
    return crud.reject_interest(response_id=response_id, db=db, _=_)


@router.post("/api/admin/legacy-profile-claims/{role}/{profile_id}")
def issue_legacy_profile_claim(
    role: str,
    profile_id: int,
    payload: LegacyClaimIssueInput,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("admin")),
) -> dict[str, str]:
    """Issue a short-lived, one-time claim code after an Admin verifies ownership out of band."""
    if role not in {"student", "tutor"}:
        raise HTTPException(status_code=422, detail="Role must be student or tutor.")
    model = Student if role == "student" else Tutor
    profile = db.get(model, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Legacy profile not found.")
    if profile.account_id is not None:
        raise HTTPException(status_code=409, detail="This profile is already linked to an account.")
    if db.scalar(select(UserAccount.id).where(UserAccount.email == profile.email)) is not None:
        raise HTTPException(status_code=409, detail="An account already uses this email.")
    raw_code = secrets.token_urlsafe(32)
    profile.claim_token_hash = token_hash(raw_code)
    profile.claim_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    db.commit()
    record_security_event(db, "legacy_profile_claim_issued", request, account_id=admin.id, details=f"Role={role}; profile_id={profile_id}; verification={payload.verification_note}; expires_in_minutes=15")
    return {"claim_token": raw_code, "expires_in": "15 minutes", "instruction": "Share this code with the verified profile owner. It can be used once during registration."}
