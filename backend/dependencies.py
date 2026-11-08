import os
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
try:
    from backend.database import get_db
    from backend.models import Student, Tutor
except ModuleNotFoundError:
    from database import get_db
    from models import Student, Tutor

def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    configured_key = os.getenv("ADMIN_API_KEY")
    if not configured_key:
        raise HTTPException(status_code=503, detail="Admin actions are disabled until ADMIN_API_KEY is configured on the backend.")
    if not x_admin_key or x_admin_key != configured_key:
        raise HTTPException(status_code=403, detail="Valid Admin API key required.")

def require_demo_profile(
    x_profile_id: int | None = Header(default=None, alias="X-TutorInn-Profile-ID"),
    x_profile_type: str | None = Header(default=None, alias="X-TutorInn-Profile-Type"),
    db: Session = Depends(get_db),
