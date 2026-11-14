import hmac
import json
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
    from backend.auth import (
        create_access_token, failed_login_count, get_current_account, hash_password,
        record_security_event, require_roles, timestamp, utc_now, verify_password,
    )
    from backend.database import get_db
    from backend.models import Student, Tutor, UserAccount
    from backend.schemas import (
        AccountRead, AdminBootstrapInput, AuthTokenResponse, LoginInput,
        StudentRegistrationInput, TutorRegistrationInput,
    )
except ModuleNotFoundError:
    from auth import (
        create_access_token, failed_login_count, get_current_account, hash_password,
        record_security_event, require_roles, timestamp, utc_now, verify_password,
    )
    from database import get_db
    from models import Student, Tutor, UserAccount
    from schemas import (
        AccountRead, AdminBootstrapInput, AuthTokenResponse, LoginInput,
        StudentRegistrationInput, TutorRegistrationInput,
    )

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _token_response(account: UserAccount) -> AuthTokenResponse:
    access_token, expires_in = create_access_token(account)
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        account=AccountRead.model_validate(account),
    )


def _new_account(db: Session, email: str, password: str, role: str) -> UserAccount:
    account = UserAccount(
        email=email,
        password_hash=hash_password(password),
        role=role,
        status="active",
        created_at=timestamp(),
        updated_at=timestamp(),
    )
    db.add(account)
    db.flush()
    return account


@router.post("/register/student", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_student(payload: StudentRegistrationInput, db: Session = Depends(get_db)) -> AuthTokenResponse:
    if db.scalar(select(UserAccount).where(UserAccount.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if db.scalar(select(Student).where(Student.email == payload.email)):
        raise HTTPException(status_code=409, detail="A legacy Student profile already uses this email. Contact an administrator to link it safely.")
    account = None
    try:
        account = _new_account(db, payload.email, payload.password, "student")
        subjects = payload.subjects
        profile = Student(
            account_id=account.id,
            full_name=payload.full_name,
            email=payload.email,
            phone_number=payload.phone_number,
            education_level=payload.education_level,
            preferred_subjects=", ".join(subjects),
            subjects_json=json.dumps(subjects, ensure_ascii=False),
        )
        db.add(profile)
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account or profile with this email already exists.") from exc
    return _token_response(account)


@router.post("/register/tutor", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_tutor(payload: TutorRegistrationInput, db: Session = Depends(get_db)) -> AuthTokenResponse:
    if db.scalar(select(UserAccount).where(UserAccount.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if db.scalar(select(Tutor).where(Tutor.email == payload.email)):
        raise HTTPException(status_code=409, detail="A legacy Tutor profile already uses this email. Contact an administrator to link it safely.")
    account = None
    try:
        account = _new_account(db, payload.email, payload.password, "tutor")
        profile = Tutor(
            account_id=account.id,
            full_name=payload.full_name,
            email=payload.email,
            phone_number=payload.phone_number,
            subject=payload.subjects[0],
            teaching_level=payload.teaching_level,
            experience_years=payload.experience_years,
            hourly_rate=payload.hourly_rate,
            bio=payload.bio,
            subjects_json=json.dumps(payload.subjects, ensure_ascii=False),
        )
        db.add(profile)
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account or profile with this email already exists.") from exc
    return _token_response(account)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginInput, request: Request, db: Session = Depends(get_db)) -> AuthTokenResponse:
    try:
        max_attempts = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
        lockout_minutes = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Login lockout settings must be integers.") from exc
    if not 1 <= max_attempts <= 20 or not 1 <= lockout_minutes <= 1440:
        raise HTTPException(status_code=503, detail="Login lockout settings are outside their allowed range.")
    if failed_login_count(db, payload.email, lockout_minutes) >= max_attempts:
        record_security_event(db, "login_locked", request, attempted_email=payload.email)
        raise HTTPException(status_code=429, detail="Too many failed sign-in attempts. Try again later.")

    account = db.scalar(select(UserAccount).where(UserAccount.email == payload.email))
    if account is None or not verify_password(payload.password, account.password_hash):
        record_security_event(
            db, "login_failed", request,
            account_id=account.id if account else None,
            attempted_email=payload.email,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if account.status != "active":
        record_security_event(db, "blocked_inactive_account", request, account_id=account.id)
        raise HTTPException(status_code=403, detail="This account is suspended or inactive.")

    record_security_event(db, "login_succeeded", request, account_id=account.id)
    return _token_response(account)


@router.get("/me", response_model=AccountRead)
def read_current_account(account: UserAccount = Depends(get_current_account)) -> UserAccount:
    return account


@router.get("/admin/check", response_model=AccountRead)
def admin_authentication_check(account: UserAccount = Depends(require_roles("admin"))) -> UserAccount:
    return account


@router.post("/admin/bootstrap", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def bootstrap_first_admin(payload: AdminBootstrapInput, request: Request, db: Session = Depends(get_db)) -> UserAccount:
    configured_token = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "")
    supplied_token = request.headers.get("X-Admin-Bootstrap-Token", "")
    if len(configured_token) < 32:
        raise HTTPException(status_code=503, detail="Configure a strong ADMIN_BOOTSTRAP_TOKEN before bootstrapping an Admin account.")
    if not supplied_token or not hmac.compare_digest(configured_token, supplied_token):
        record_security_event(db, "admin_bootstrap_denied", request, attempted_email=payload.email)
        raise HTTPException(status_code=403, detail="Invalid Admin bootstrap credential.")
    if db.scalar(select(UserAccount.id).where(UserAccount.role == "admin")) is not None:
        raise HTTPException(status_code=409, detail="An Admin account has already been bootstrapped.")
    if db.scalar(select(UserAccount.id).where(UserAccount.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    account = _new_account(db, payload.email, payload.password, "admin")
    try:
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    record_security_event(db, "admin_bootstrapped", request, account_id=account.id)
    return account
