import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

try:
    from backend.database import get_db
    from backend.models import Student, Tutor
except ModuleNotFoundError:
    from database import get_db
    from models import Student, Tutor


def demo_mode_enabled() -> bool:
    configured = os.getenv("ENABLE_DEMO_MODE")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    is_deployed = os.getenv("ENVIRONMENT", "").lower() == "production" or os.getenv("VERCEL") == "1"
    return not is_deployed


def require_demo_mode() -> None:
    if not demo_mode_enabled():
        raise HTTPException(
            status_code=403,
            detail="The legacy demo workflow is disabled. Sign in with a TutorInn account.",
        )


def require_admin_key(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    require_demo_mode()
    configured_key = os.getenv("ADMIN_API_KEY")
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="Legacy demo Admin actions are disabled until ADMIN_API_KEY is configured.",
        )
    if not x_admin_key or x_admin_key != configured_key:
        raise HTTPException(status_code=403, detail="Valid Admin API key required.")


def require_demo_profile(
    x_profile_id: int | None = Header(default=None, alias="X-TutorInn-Profile-ID"),
    x_profile_type: str | None = Header(default=None, alias="X-TutorInn-Profile-Type"),
    db: Session = Depends(get_db),
) -> tuple[str, int]:
    require_demo_mode()
    if x_profile_type not in {"student", "tutor"} or x_profile_id is None:
        raise HTTPException(
            status_code=403,
            detail="Select a Student or Tutor demo profile before performing this action.",
        )
    model = Student if x_profile_type == "student" else Tutor
    if db.get(model, x_profile_id) is None:
        raise HTTPException(
            status_code=409,
            detail="The selected profile no longer exists. Select another profile.",
        )
    return x_profile_type, x_profile_id
