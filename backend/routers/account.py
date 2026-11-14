import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from backend.auth import get_current_account, hash_password, record_security_event, require_roles, timestamp, verify_password
    from backend.database import get_db
    from backend.models import RefreshSession, Student, Tutor, UserAccount
    from backend.schemas import (
        PasswordChangeInput, StudentPrivateRead, StudentProfileUpdate,
        TutorPrivateRead, TutorProfileUpdate,
    )
except ModuleNotFoundError:
    from auth import get_current_account, hash_password, record_security_event, require_roles, timestamp, verify_password
    from database import get_db
    from models import RefreshSession, Student, Tutor, UserAccount
    from schemas import PasswordChangeInput, StudentPrivateRead, StudentProfileUpdate, TutorPrivateRead, TutorProfileUpdate

router = APIRouter(tags=["Account profiles and security"])


@router.get("/api/me/profile", response_model=StudentPrivateRead | TutorPrivateRead)
def read_my_profile(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> Student | Tutor:
    if account.role == "student":
        profile = db.scalar(select(Student).where(Student.account_id == account.id))
    else:
        profile = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active profile.")
    return profile


@router.put("/api/me/profile/student", response_model=StudentPrivateRead)
def update_my_student_profile(
    payload: StudentProfileUpdate,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> Student:
    profile = db.scalar(select(Student).where(Student.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active Student profile.")
    profile.full_name = payload.full_name
    profile.phone_number = payload.phone_number
    profile.education_level = payload.education_level
    profile.preferred_subjects = ", ".join(payload.subjects)
    profile.subjects_json = json.dumps(payload.subjects, ensure_ascii=False)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/api/me/profile/tutor", response_model=TutorPrivateRead)
def update_my_tutor_profile(
    payload: TutorProfileUpdate,
    account: UserAccount = Depends(require_roles("tutor")),
    db: Session = Depends(get_db),
) -> Tutor:
    profile = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active Tutor profile.")
    profile.full_name = payload.full_name
    profile.phone_number = payload.phone_number
    profile.subject = payload.subjects[0]
    profile.subjects_json = json.dumps(payload.subjects, ensure_ascii=False)
    profile.teaching_level = payload.teaching_level
    profile.experience_years = payload.experience_years
    profile.hourly_rate = payload.hourly_rate
    profile.bio = payload.bio
    profile.availability = payload.availability
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/api/me/password")
def change_my_password(
    payload: PasswordChangeInput,
    request: Request,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if verify_password(payload.new_password, account.password_hash):
        raise HTTPException(status_code=422, detail="Choose a new password different from your current password.")

    account.password_hash = hash_password(payload.new_password)
    account.updated_at = timestamp()
    now = timestamp()
    active_sessions = list(db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == account.id,
        RefreshSession.revoked_at.is_(None),
    )).all())
    for session in active_sessions:
        session.revoked_at = now
    db.commit()
    record_security_event(db, "password_changed", request, account_id=account.id)
    return {"message": "Password updated. All active sessions were revoked; sign in again."}
