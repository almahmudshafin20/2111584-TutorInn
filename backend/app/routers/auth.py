import hmac
import json
import os
import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token, decode_access_token, enforce_auth_rate_limit, failed_login_count, get_current_account, hash_password, password_hash_needs_upgrade,
    record_security_event, refresh_token_days, require_roles, timestamp, token_hash,
    utc_now, validate_jwt_settings, verify_password,
)
from ..database import get_db
from ..models import RefreshSession, Student, Tutor, UserAccount
from ..schemas import (
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
    enforce_auth_rate_limit(db, request, "registration", limit_env="REGISTER_MAX_ATTEMPTS", window_env="REGISTER_WINDOW_SECONDS", default_limit=8, default_window_seconds=3600, attempted_email=payload.email)
    if db.scalar(select(UserAccount).where(UserAccount.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    legacy_student = db.scalar(select(Student).where(Student.email == payload.email))
    legacy_tutor = db.scalar(select(Tutor.id).where(Tutor.email == payload.email))
    if legacy_tutor is not None:
        raise HTTPException(status_code=409, detail="This email belongs to a legacy Tutor profile.")
    if legacy_student is not None:
        raise HTTPException(status_code=409, detail="A Student profile with this email already exists.")
    try:
        account = _new_account(db, payload.email, payload.password, "student")
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
    record_security_event(db, "registration_succeeded", request, account_id=account.id, attempted_email=account.email, details="role=student")
    return _token_response(account, request, response, db)


@router.post("/register/tutor", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_tutor(
    payload: TutorRegistrationInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    validate_jwt_settings()
    enforce_auth_rate_limit(db, request, "registration", limit_env="REGISTER_MAX_ATTEMPTS", window_env="REGISTER_WINDOW_SECONDS", default_limit=8, default_window_seconds=3600, attempted_email=payload.email)
    if db.scalar(select(UserAccount).where(UserAccount.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    legacy_tutor = db.scalar(select(Tutor).where(Tutor.email == payload.email))
    legacy_student = db.scalar(select(Student.id).where(Student.email == payload.email))
    if legacy_student is not None:
        raise HTTPException(status_code=409, detail="This email belongs to a legacy Student profile.")
    if legacy_tutor is not None:
        raise HTTPException(status_code=409, detail="A Tutor profile with this email already exists.")
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
            availability=payload.availability,
            subjects_json=json.dumps(payload.subjects, ensure_ascii=False),
        )
        db.add(profile)
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account or profile with this email already exists.") from exc
    record_security_event(db, "registration_succeeded", request, account_id=account.id, attempted_email=account.email, details="role=tutor")
    return _token_response(account, request, response, db)


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    validate_jwt_settings()
    enforce_auth_rate_limit(db, request, "login", limit_env="LOGIN_IP_MAX_ATTEMPTS", window_env="LOGIN_IP_WINDOW_SECONDS", default_limit=30, default_window_seconds=900, attempted_email=payload.email)
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

    # Upgrade pre-pepper Argon2 hashes only after the supplied password has
    # been verified successfully. The replacement keeps the existing account
    # and profile records intact and takes effect before issuing a session.
    if password_hash_needs_upgrade(account.password_hash):
        account.password_hash = hash_password(payload.password)
        account.updated_at = timestamp()
        db.commit()

    record_security_event(db, "login_succeeded", request, account_id=account.id)
    return _token_response(account, request, response, db)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh_session(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    enforce_auth_rate_limit(db, request, "refresh", limit_env="REFRESH_MAX_ATTEMPTS", window_env="REFRESH_WINDOW_SECONDS", default_limit=30, default_window_seconds=60)
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
        record_security_event(db, "refresh_token_rejected", request, details="reason=unknown_session")
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
    record_security_event(db, "refresh_succeeded", request, account_id=account.id)
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
            record_security_event(db, "session_revoked", request, account_id=session.account_id, details="reason=logout")
    _clear_auth_cookies(response)
    return {"message": "Logged out."}


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(
    request: Request,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> list[SessionRead]:
    authorization = request.headers.get("authorization", "")
    scheme, _, access_token = authorization.partition(" ")
    claims = decode_access_token(access_token) if scheme.lower() == "bearer" and access_token else {}
    current_session_id = int(claims["sid"]) if claims.get("sid") else None
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
            current=item.id == current_session_id,
        )
        for item in sessions
    ]


@router.delete("/sessions/others", status_code=status.HTTP_204_NO_CONTENT)
def revoke_other_sessions(
    request: Request,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> None:
    """Revoke every active session except the session used for this request."""
    authorization = request.headers.get("authorization", "")
    scheme, _, access_token = authorization.partition(" ")
    claims = decode_access_token(access_token) if scheme.lower() == "bearer" and access_token else {}
    current_session_id = int(claims["sid"]) if claims.get("sid") else None
    if current_session_id is None:
        raise HTTPException(status_code=401, detail="The current session could not be identified.")
    active_sessions = db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == account.id,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > timestamp(),
        RefreshSession.id != current_session_id,
    )).all()
    now = timestamp()
    for item in active_sessions:
        item.revoked_at = now
    db.commit()
    record_security_event(
        db, "other_sessions_revoked", request, account_id=account.id,
        details=f"Revoked {len(active_sessions)} other active session(s).",
    )


@router.delete("/sessions/all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_sessions(
    request: Request,
    response: Response,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> None:
    """Revoke every active session, including the session used for this request."""
    active_sessions = db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == account.id,
        RefreshSession.revoked_at.is_(None),
    )).all()
    now = timestamp()
    for item in active_sessions:
        item.revoked_at = now
    db.commit()
    record_security_event(
        db, "all_sessions_revoked", request, account_id=account.id,
        details=f"Revoked {len(active_sessions)} session(s), including the current session.",
    )
    _clear_auth_cookies(response)


@router.get("/admin/accounts/{account_id}/sessions", response_model=list[SessionRead])
def admin_list_account_sessions(
    account_id: int,
    request: Request,
    account: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[SessionRead]:
    """List safe metadata for active sessions belonging to a selected account."""
    target = db.get(UserAccount, account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    sessions = db.scalars(
        select(RefreshSession).where(
            RefreshSession.account_id == account_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > timestamp(),
        ).order_by(RefreshSession.created_at.desc())
    ).all()
    record_security_event(
        db,
        "admin_sessions_listed",
        request,
        account_id=account.id,
        details=f"Admin inspected active sessions for account {account_id}.",
    )
    return [
        SessionRead(
            id=item.id,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            user_agent=item.user_agent,
            ip_address=item.ip_address,
            current=False,
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
    authorization = request.headers.get("authorization", "")
    scheme, _, access_token = authorization.partition(" ")
    claims = decode_access_token(access_token) if scheme.lower() == "bearer" and access_token else {}
    if claims.get("sid") and int(claims["sid"]) == session_id:
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
    enforce_auth_rate_limit(
        db, request, "admin_bootstrap",
        limit_env="ADMIN_BOOTSTRAP_MAX_ATTEMPTS",
        window_env="ADMIN_BOOTSTRAP_WINDOW_SECONDS",
        default_limit=5, default_window_seconds=3600,
        attempted_email=payload.email,
    )
    configured_email = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "").strip().lower()
    if not configured_email:
        raise HTTPException(status_code=503, detail="Configure ADMIN_BOOTSTRAP_EMAIL before bootstrapping the First Admin.")
    if payload.email != configured_email:
        record_security_event(db, "admin_bootstrap_denied", request, attempted_email=payload.email,
                              details="reason=designated_first_admin_email_mismatch")
        raise HTTPException(status_code=403, detail="This email is not the designated First Admin address.")
    configured_token = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "")
    supplied_token = request.headers.get("X-Admin-Bootstrap-Token", "")
    if len(configured_token) < 32:
        raise HTTPException(status_code=503, detail="Configure a strong ADMIN_BOOTSTRAP_TOKEN before bootstrapping an Admin account.")
    if not supplied_token or not hmac.compare_digest(configured_token, supplied_token):
        record_security_event(db, "admin_bootstrap_denied", request, attempted_email=payload.email)
        raise HTTPException(status_code=403, detail="Invalid Admin bootstrap credential.")
    # A transaction-scoped advisory lock serializes first-admin bootstrap attempts
    # even while the Admin table is empty (where SELECT FOR UPDATE locks nothing).
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(2111584)"))
    if db.scalar(select(UserAccount.id).where(UserAccount.role == "admin").with_for_update()) is not None:
        raise HTTPException(status_code=409, detail="An Admin account has already been bootstrapped.")
    if db.scalar(select(UserAccount.id).where(UserAccount.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    account = _new_account(db, payload.email, payload.password, "admin")
    account.is_first_admin = True
    try:
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    record_security_event(db, "admin_bootstrapped", request, account_id=account.id)
    return account
