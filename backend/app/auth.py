import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RefreshSession, SecurityEvent, UserAccount

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
bearer_scheme = HTTPBearer(auto_error=False)
ACCESS_ALGORITHM = "HS256"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp() -> str:
    return utc_now().isoformat()


def _jwt_settings() -> tuple[str, str, str, int]:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="JWT_SECRET must be configured with at least 32 characters before authentication is enabled.",
        )
    try:
        minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="ACCESS_TOKEN_MINUTES must be an integer.") from exc
    if not 1 <= minutes <= 60:
        raise HTTPException(status_code=503, detail="ACCESS_TOKEN_MINUTES must be between 1 and 60.")
    return secret, os.getenv("JWT_ISSUER", "tutorinn"), os.getenv("JWT_AUDIENCE", "tutorinn-web"), minutes


def validate_jwt_settings() -> None:
    _jwt_settings()


def refresh_token_days() -> int:
    try:
        days = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="REFRESH_TOKEN_DAYS must be an integer.") from exc
    if not 1 <= days <= 30:
        raise HTTPException(status_code=503, detail="REFRESH_TOKEN_DAYS must be between 1 and 30.")
    return days


def token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


PASSWORD_HASH_PREFIX = "tutorinn$argon2id$pepper-v1$"


def _password_pepper(*, required: bool = True) -> bytes | None:
    value = os.getenv("PASSWORD_PEPPER", "")
    if not value:
        if required:
            raise HTTPException(
                status_code=503,
                detail="PASSWORD_PEPPER must be configured with at least 32 characters before password authentication is enabled.",
            )
        return None
    if len(value) < 32:
        raise HTTPException(
            status_code=503,
            detail="PASSWORD_PEPPER must contain at least 32 characters.",
        )
    return value.encode("utf-8")


def _peppered_password(password: str, pepper: bytes) -> str:
    # HMAC keeps the deployment-only pepper out of the database and lets Argon2
    # continue to provide a unique random salt for every stored password.
    return hmac.new(pepper, password.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    pepper = _password_pepper()
    assert pepper is not None
    return PASSWORD_HASH_PREFIX + password_hasher.hash(_peppered_password(password, pepper))


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith(PASSWORD_HASH_PREFIX):
            pepper = _password_pepper()
            assert pepper is not None
            encoded_hash = password_hash[len(PASSWORD_HASH_PREFIX):]
            return password_hasher.verify(encoded_hash, _peppered_password(password, pepper))
        # Backward-compatible verification for accounts created before the
        # server-side pepper was introduced. Successful logins are upgraded
        # by the login route before a session is issued.
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_hash_needs_upgrade(password_hash: str) -> bool:
    if not password_hash.startswith(PASSWORD_HASH_PREFIX):
        return True
    encoded_hash = password_hash[len(PASSWORD_HASH_PREFIX):]
    try:
        return password_hasher.check_needs_rehash(encoded_hash)
    except (VerificationError, InvalidHashError):
        return True


def create_access_token(account: UserAccount, session_id: int) -> tuple[str, int]:
    secret, issuer, audience, minutes = _jwt_settings()
    now = utc_now()
    payload = {
        "sub": str(account.id),
        "role": account.role,
        "sid": str(session_id),
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, secret, algorithm=ACCESS_ALGORITHM), minutes * 60


def decode_access_token(token: str) -> dict:
    secret, issuer, audience, _ = _jwt_settings()
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ACCESS_ALGORITHM],
            issuer=issuer,
            audience=audience,
            options={"require": ["sub", "role", "sid", "iss", "aud", "iat", "exp", "jti"]},
        )
        if not str(claims.get("sub", "")).isdigit() or not str(claims.get("sid", "")).isdigit():
            raise jwt.InvalidTokenError("Invalid account or session subject.")
        return claims
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.") from exc


def record_security_event(
    db: Session,
    event_type: str,
    request: Request,
    *,
    account_id: int | None = None,
    attempted_email: str = "",
    details: str = "",
) -> None:
    db.add(SecurityEvent(
        account_id=account_id,
        event_type=event_type,
        attempted_email=attempted_email[:255],
        ip_address=(request.client.host if request.client else "")[:64],
        user_agent=request.headers.get("user-agent", "")[:512],
        details=details[:2000],
        created_at=timestamp(),
    ))
    db.commit()


def get_current_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserAccount:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    claims = decode_access_token(credentials.credentials)
    account = db.get(UserAccount, int(claims["sub"]))
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.", headers={"WWW-Authenticate": "Bearer"})
    session = db.get(RefreshSession, int(claims["sid"]))
    if (
        session is None
        or session.account_id != account.id
        or session.revoked_at is not None
        or session.expires_at <= timestamp()
    ):
        raise HTTPException(status_code=401, detail="Your session is no longer active. Sign in again.")
    if account.status != "active":
        record_security_event(db, "blocked_inactive_account", request, account_id=account.id)
        raise HTTPException(status_code=403, detail="This account is suspended or inactive.")
    # The role claim is informational. Current database role/status is authoritative.
    return account


def require_roles(*roles: str) -> Callable:
    def role_dependency(
        request: Request,
        account: UserAccount = Depends(get_current_account),
        db: Session = Depends(get_db),
    ) -> UserAccount:
        if account.role not in roles:
            record_security_event(
                db, "access_denied", request, account_id=account.id,
                details=f"Required role: {', '.join(roles)}; current role: {account.role}",
            )
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return account
    return role_dependency


def failed_login_count(db: Session, email: str, lockout_minutes: int) -> int:
    cutoff = (utc_now() - timedelta(minutes=lockout_minutes)).isoformat()
    return int(db.scalar(
        select(func.count()).select_from(SecurityEvent).where(
            SecurityEvent.event_type == "login_failed",
            SecurityEvent.attempted_email == email,
            SecurityEvent.created_at >= cutoff,
        )
    ) or 0)
