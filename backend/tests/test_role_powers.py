"""Role powers: Moderators get content-moderation access only; purge is First-Admin-only."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('role-powers-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import RefreshSession, SecurityEvent, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def headers_for(role: str) -> dict:
    email = f"role-{role}-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        account = UserAccount(email=email, password_hash=hash_password(PASSWORD), role=role,
                              is_first_admin=False, status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(account)
        db.flush()
        now = timestamp()
        session = RefreshSession(
            account_id=account.id, token_hash=token_hash(secrets.token_urlsafe(48)),
            family_id=str(uuid.uuid4()), csrf_token_hash=token_hash(secrets.token_urlsafe(32)),
            created_at=now, last_used_at=now, expires_at=(utc_now() + timedelta(days=1)).isoformat(),
            revoked_at=None, replaced_by=None, user_agent="role-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
        account_id = account.id
    return {"Authorization": f"Bearer {access}", "_account_id": account_id}


def strip(headers: dict) -> dict:
    return {key: value for key, value in headers.items() if not key.startswith("_")}


def test_moderator_can_review_requests_and_moderate_learning_content():
    moderator = strip(headers_for("moderator"))
    assert client.get("/api/admin/requests", headers=moderator).status_code == 200
    assert client.get("/api/admin/groups", headers=moderator).status_code == 200


def test_moderator_cannot_manage_accounts_roles_exports_or_activity_cleanup():
    moderator_headers = headers_for("moderator")
    moderator = strip(moderator_headers)
    target = headers_for("student")
    assert client.get("/api/admin/users", headers=moderator).status_code == 403
    assert client.post(f"/api/admin/users/{target['_account_id']}/admin-role", headers=moderator,
                       json={"reason": "Attempting to grant an Admin role."}).status_code == 403
    assert client.get("/api/admin/export/users", headers=moderator).status_code == 403
    purge = client.request("DELETE", "/api/admin/activity/purge", headers=moderator, json={
        "before": "2000-01-01T00:00:00Z", "reason": "Attempting activity cleanup.", "confirm": True,
    })
    assert purge.status_code == 403


def test_ordinary_admin_cannot_run_activity_cleanup_because_only_the_first_admin_can():
    admin = strip(headers_for("admin"))
    purge = client.request("DELETE", "/api/admin/activity/purge", headers=admin, json={
        "before": "2000-01-01T00:00:00Z", "reason": "Attempting activity cleanup.", "confirm": True,
    })
    assert purge.status_code == 403
    assert "First Admin" in purge.json()["detail"]
