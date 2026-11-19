"""Role protections: other Admins and Moderators cannot touch the First Admin; Admins cannot revoke their own role;
role grants and revocations are audited with actor, affected account and reason."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('role-protections-test.db')}")
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


def headers_for(role: str, *, first: bool = False) -> tuple[dict, int]:
    email = f"protect-{role}-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        account = UserAccount(email=email, password_hash=hash_password(PASSWORD), role=role,
                              is_first_admin=first, status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(account)
        db.flush()
        now = timestamp()
        session = RefreshSession(
            account_id=account.id, token_hash=token_hash(secrets.token_urlsafe(48)),
            family_id=str(uuid.uuid4()), csrf_token_hash=token_hash(secrets.token_urlsafe(32)),
            created_at=now, last_used_at=now, expires_at=(utc_now() + timedelta(days=1)).isoformat(),
            revoked_at=None, replaced_by=None, user_agent="protect-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
        return {"Authorization": f"Bearer {access}"}, account.id


def first_admin_id() -> int:
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(is_first_admin=True).order_by(UserAccount.id).first()
        if account is None:
            account = UserAccount(email=f"protect-first-{uuid.uuid4().hex[:8]}@example.com",
                                  password_hash=hash_password(PASSWORD), role="admin", is_first_admin=True,
                                  status="active", created_at=timestamp(), updated_at=timestamp())
            db.add(account)
            db.commit()
        return account.id


def test_other_admins_and_moderators_cannot_suspend_or_demote_the_first_admin():
    target = first_admin_id()
    ordinary_admin, _ = headers_for("admin")
    moderator, _ = headers_for("moderator")
    suspend = {"status": "suspended", "reason": "Attempting to suspend the First Admin."}
    for headers in (ordinary_admin, moderator):
        blocked = client.patch(f"/api/admin/users/{target}/status", headers=headers, json=suspend)
        assert blocked.status_code == 403, blocked.text
    demote = client.request("DELETE", f"/api/admin/users/{target}/admin-role", headers=ordinary_admin,
                            json={"reason": "Attempting to demote the First Admin."})
    assert demote.status_code == 403
    assert "protected" in demote.json()["detail"]


def test_an_admin_cannot_revoke_their_own_admin_role():
    ordinary_admin, admin_id = headers_for("admin")
    attempt = client.request("DELETE", f"/api/admin/users/{admin_id}/admin-role", headers=ordinary_admin,
                             json={"reason": "Attempting to remove my own Admin role."})
    assert attempt.status_code in (403, 409)
    with SessionLocal() as db:
        assert db.get(UserAccount, admin_id).role == "admin"


def test_role_grant_and_revocation_are_audited_with_actor_affected_account_and_reason():
    first_headers, first_id = headers_for("admin", first=True)
    _, student_id = headers_for("student")
    with SessionLocal() as db:
        student = db.get(UserAccount, student_id)
        student.email_verified_at = timestamp()
        db.commit()
    granted = client.post(f"/api/admin/users/{student_id}/admin-role", headers=first_headers,
                          json={"reason": "Role audit regression grant."})
    assert granted.status_code == 200, granted.text
    revoked = client.request("DELETE", f"/api/admin/users/{student_id}/admin-role", headers=first_headers,
                             json={"reason": "Role audit regression revoke."})
    assert revoked.status_code == 200, revoked.text
    with SessionLocal() as db:
        revoke_event = db.query(SecurityEvent).filter_by(event_type="admin_admin_role_revoked",
                                                          attempted_email=str(student_id)).order_by(SecurityEvent.id.desc()).first()
        assert revoke_event is not None
        assert revoke_event.account_id == first_id
        assert "Role audit regression revoke." in revoke_event.details
        assert revoke_event.ip_address and revoke_event.created_at
