import os

from fastapi import Header, HTTPException


def require_demo_role(x_tutorinn_role: str | None = Header(default=None, alias="X-TutorInn-Role")) -> str:
    if x_tutorinn_role not in {"student", "tutor"}:
        raise HTTPException(status_code=403, detail="Select Student or Tutor before performing this action.")
    return x_tutorinn_role


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    configured_key = os.getenv("ADMIN_API_KEY")
    if not configured_key:
        raise HTTPException(status_code=503, detail="Admin actions are disabled until ADMIN_API_KEY is configured on the backend.")
    if not x_admin_key or x_admin_key != configured_key:
        raise HTTPException(status_code=403, detail="Valid Admin API key required.")
