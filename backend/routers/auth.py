import hmac
import json
import os
import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
    from backend.auth import (
        create_access_token, failed_login_count, get_current_account, hash_password,
        record_security_event, refresh_token_days, require_roles, timestamp, token_hash,
        utc_now, validate_jwt_settings, verify_password,
    )
    from backend.database import get_db
    from backend.models import RefreshSession, Student, Tutor, UserAccount
    from backend.schemas import (
        AccountRead, AdminBootstrapInput, AuthTokenResponse, LoginInput, SessionRead,
        StudentRegistrationInput, TutorRegistrationInput,
    )
except ModuleNotFoundError:
    from auth import (
        create_access_token, failed_login_count, get_current_account, hash_password,
        record_security_event, refresh_token_days, require_roles, timestamp, token_hash,
        utc_now, validate_jwt_settings, verify_password,
    )
    from database import get_db
    from models import RefreshSession, Student, Tutor, UserAccount
    from schemas import (
        AccountRead, AdminBootstrapInput, AuthTokenResponse, LoginInput, SessionRead,
        StudentRegistrationInput, TutorRegistrationInput,
    )

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
REFRESH_COOKIE = "tutorinn_refresh"
CSRF_COOKIE = "tutorinn_csrf"
CSRF_HEADER = "X-CSRF-Token"
COOKIE_PATH = "/api/auth"
CSRF_COOKIE_PATH = "/"


def _cookie_settings() -> tuple[bool, str]:
    secure_setting = os.getenv("COOKIE_SECURE")
    is_deployed = os.getenv("ENVIRONMENT", "").lower() == "production" or os.getenv("VERCEL") == "1"
    secure = secure_setting.strip().lower() in {"1", "true", "yes", "on"} if secure_setting is not None else is_deployed
    if is_deployed and not secure:
        raise HTTPException(status_code=503, detail="Secure authentication cookies cannot be disabled in a production deployment.")
    same_site = os.getenv("COOKIE_SAMESITE", "lax").lower()
    if same_site not in {"lax", "strict", "none"}:
        raise HTTPException(status_code=503, detail="COOKIE_SAMESITE must be lax, strict, or none.")
    if same_site == "none" and not secure:
        raise HTTPException(status_code=503, detail="SameSite=None cookies require COOKIE_SECURE=true.")
    return secure, same_site


def _set_auth_cookies(response: Response, refresh_token: str, csrf_token: str) -> None:
    secure, same_site = _cookie_settings()
    max_age = refresh_token_days() * 24 * 60 * 60
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, max_age=max_age, httponly=True,
        secure=secure, samesite=same_site, path=COOKIE_PATH,
    )
    response.set_cookie(
        CSRF_COOKIE, csrf_token, max_age=max_age, httponly=False,
        secure=secure, samesite=same_site, path=CSRF_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    secure, same_site = _cookie_settings()
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, secure=secure, httponly=True, samesite=same_site)
    response.delete_cookie(CSRF_COOKIE, path=CSRF_COOKIE_PATH, secure=secure, httponly=False, samesite=same_site)


def _require_csrf(request: Request) -> str:
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get(CSRF_HEADER, "")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="A valid CSRF token is required.")
    return cookie_token


def _create_refresh_session(
    db: Session,
    account: UserAccount,
    request: Request,
    *,
    family_id: str | None = None,
) -> tuple[RefreshSession, str, str, str, int]:
    now = utc_now()
    days = refresh_token_days()
    raw_refresh = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    refresh_hash = token_hash(raw_refresh)
    session = RefreshSession(
        account_id=account.id,
        token_hash=refresh_hash,
        family_id=family_id or str(uuid.uuid4()),
        csrf_token_hash=token_hash(csrf_token),
        created_at=now.isoformat(),
        last_used_at=now.isoformat(),
        expires_at=(now + timedelta(days=days)).isoformat(),
        revoked_at=None,
        replaced_by=None,
        user_agent=request.headers.get("user-agent", "")[:512],
        ip_address=(request.client.host if request.client else "")[:64],
    )
    db.add(session)
    db.flush()
    access_token, expires_in = create_access_token(account, session.id)
    return session, raw_refresh, csrf_token, access_token, expires_in


def _token_response(
    account: UserAccount,
    request: Request,
    response: Response,
    db: Session,
    *,
    family_id: str | None = None,
) -> AuthTokenResponse:
    session, raw_refresh, csrf_token, access_token, expires_in = _create_refresh_session(
        db, account, request, family_id=family_id,
    )
    db.commit()
    _set_auth_cookies(response, raw_refresh, csrf_token)
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        csrf_token=csrf_token,
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
def register_student(
    payload: StudentRegistrationInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    validate_jwt_settings()
    if db.scalar(select(UserAccount).where(UserAccount.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    legacy_student = db.scalar(select(Student).where(Student.email == payload.email))
    legacy_tutor = db.scalar(select(Tutor.id).where(Tutor.email == payload.email))
    if legacy_tutor is not None:
        raise HTTPException(status_code=409, detail="This email belongs to a legacy Tutor profile.")
    if legacy_student is not None:
        if legacy_student.account_id is not None:
            raise HTTPException(status_code=409, detail="This legacy profile is already linked.")
        if not payload.claim_token or not legacy_student.claim_token_hash or not hmac.compare_digest(token_hash(payload.claim_token), legacy_student.claim_token_hash) or not legacy_student.claim_expires_at or legacy_student.claim_expires_at <= timestamp():
            raise HTTPException(status_code=403, detail="A valid, unexpired Admin-issued profile claim code is required.")
    elif payload.claim_token:
        raise HTTPException(status_code=400, detail="This claim code does not match an existing legacy profile.")
    try:
        account = _new_account(db, payload.email, payload.password, "student")
        if legacy_student is not None:
            profile = legacy_student
            profile.account_id = account.id
            profile.claim_token_hash = None
            profile.claim_expires_at = None
        else:
            profile = Student(
                account_id=account.id,
                full_name=payload.full_name,
                email=payload.email,
                phone_number=payload.phone_number,
                education_level=payload.education_level,
                preferred_subjects=", ".join(payload.subjects),
                subjects_json=json.dumps(payload.subjects, ensure_ascii=False),
            )
            db.add(profile)
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account or profile with this email already exists.") from exc
    return _token_response(account, request, response, db)


@router.post("/register/tutor", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_tutor(
    payload: TutorRegistrationInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    validate_jwt_settings()
    if db.scalar(select(UserAccount).where(UserAccount.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    legacy_tutor = db.scalar(select(Tutor).where(Tutor.email == payload.email))
    legacy_student = db.scalar(select(Student.id).where(Student.email == payload.email))
    if legacy_student is not None:
        raise HTTPException(status_code=409, detail="This email belongs to a legacy Student profile.")
    if legacy_tutor is not None:
        if legacy_tutor.account_id is not None:
            raise HTTPException(status_code=409, detail="This legacy profile is already linked.")
        if not payload.claim_token or not legacy_tutor.claim_token_hash or not hmac.compare_digest(token_hash(payload.claim_token), legacy_tutor.claim_token_hash) or not legacy_tutor.claim_expires_at or legacy_tutor.claim_expires_at <= timestamp():
            raise HTTPException(status_code=403, detail="A valid, unexpired Admin-issued profile claim code is required.")
    elif payload.claim_token:
        raise HTTPException(status_code=400, detail="This claim code does not match an existing legacy profile.")
    try:
        account = _new_account(db, payload.email, payload.password, "tutor")
        if legacy_tutor is not None:
            profile = legacy_tutor
            profile.account_id = account.id
            profile.claim_token_hash = None
            profile.claim_expires_at = None
        else:
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
                availability=payload.availability,
                subjects_json=json.dumps(payload.subjects, ensure_ascii=False),
            )
            db.add(profile)
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account or profile with this email already exists.") from exc
    return _token_response(account, request, response, db)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    validate_jwt_settings()
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
    return _token_response(account, request, response, db)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh_session(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    csrf_token = _require_csrf(request)
    raw_refresh = request.cookies.get(REFRESH_COOKIE, "")
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh session is missing. Sign in again.")
    current_hash = token_hash(raw_refresh)
    session = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == current_hash)
        .with_for_update()
    )
    if session is None:
        raise HTTPException(status_code=401, detail="Refresh session is invalid. Sign in again.")

    now = timestamp()
    if not hmac.compare_digest(session.csrf_token_hash, token_hash(csrf_token)):
        raise HTTPException(status_code=403, detail="CSRF token does not match this session.")

    if session.revoked_at is not None:
        if session.replaced_by:
            family_sessions = list(db.scalars(select(RefreshSession).where(
                RefreshSession.family_id == session.family_id,
                RefreshSession.revoked_at.is_(None),
            )).all())
            for item in family_sessions:
                item.revoked_at = now
            record_security_event(
                db, "refresh_token_reuse", request, account_id=session.account_id,
                details="A rotated refresh token was reused; the session family was revoked.",
            )
        raise HTTPException(status_code=401, detail="Refresh session has already been revoked. Sign in again.")

    if session.expires_at <= now:
        session.revoked_at = now
        db.commit()
        record_security_event(db, "refresh_token_expired", request, account_id=session.account_id)
        raise HTTPException(status_code=401, detail="Refresh session expired. Sign in again.")

    account = db.get(UserAccount, session.account_id)
    if account is None or account.status != "active":
        family_sessions = list(db.scalars(select(RefreshSession).where(
            RefreshSession.family_id == session.family_id,
            RefreshSession.revoked_at.is_(None),
        )).all())
        for item in family_sessions:
            item.revoked_at = now
        db.commit()
        record_security_event(db, "refresh_blocked_inactive_account", request, account_id=session.account_id)
        raise HTTPException(status_code=403, detail="This account is suspended or inactive.")

    old_family = session.family_id
    new_session, new_raw, new_csrf, access_token, expires_in = _create_refresh_session(
        db, account, request, family_id=old_family,
    )
    session.revoked_at = now
    session.last_used_at = now
    session.replaced_by = new_session.token_hash
    db.commit()
    _set_auth_cookies(response, new_raw, new_csrf)
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        csrf_token=new_csrf,
        account=AccountRead.model_validate(account),
    )


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    raw_refresh = request.cookies.get(REFRESH_COOKIE, "")
    if raw_refresh:
        csrf_token = _require_csrf(request)
        session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(raw_refresh)))
        if session and session.revoked_at is None:
            if not hmac.compare_digest(session.csrf_token_hash, token_hash(csrf_token)):
                raise HTTPException(status_code=403, detail="CSRF token does not match this session.")
            session.revoked_at = timestamp()
            session.last_used_at = timestamp()
            db.commit()
            record_security_event(db, "logout", request, account_id=session.account_id)
    _clear_auth_cookies(response)
    return {"message": "Logged out."}


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(
    request: Request,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> list[SessionRead]:
    current_hash = token_hash(request.cookies.get(REFRESH_COOKIE, "")) if request.cookies.get(REFRESH_COOKIE) else ""
    sessions = db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == account.id,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > timestamp(),
    ).order_by(RefreshSession.created_at.desc())).all()
    return [
        SessionRead(
            id=item.id,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            user_agent=item.user_agent,
            ip_address=item.ip_address,
            current=bool(current_hash and hmac.compare_digest(item.token_hash, current_hash)),
        )
        for item in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: int,
    request: Request,
    response: Response,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> None:
    session = db.get(RefreshSession, session_id)
    if session is None or session.account_id != account.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.revoked_at is None:
        session.revoked_at = timestamp()
        db.commit()
        record_security_event(db, "session_revoked", request, account_id=account.id, details=f"Session {session_id} revoked.")
    raw_refresh = request.cookies.get(REFRESH_COOKIE, "")
    if raw_refresh and hmac.compare_digest(session.token_hash, token_hash(raw_refresh)):
        _clear_auth_cookies(response)


@router.delete("/admin/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_revoke_session(
    session_id: int,
    request: Request,
    account: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> None:
    session = db.get(RefreshSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.revoked_at is None:
        session.revoked_at = timestamp()
        db.commit()
        record_security_event(
            db,
            "admin_session_revoked",
            request,
            account_id=account.id,
            details=f"Admin revoked session {session_id} belonging to account {session.account_id}.",
        )


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
