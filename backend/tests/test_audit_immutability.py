"""Audit immutability: no API edits or deletes security evidence; the First Admin purge removes only rate-limit counters."""
import os, sys, uuid
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('audit-immutability-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import hash_password, timestamp
from app.database import SessionLocal, initialize_database
from app.models import SecurityEvent, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"
MUTATING = {"PUT", "PATCH", "DELETE"}


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def first_admin_headers() -> dict:
    """Use the existing First Admin identity, or create one, with a known password for this test only."""
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(is_first_admin=True).order_by(UserAccount.id).first()
        if account is None:
            account = UserAccount(email=f"audit-first-admin-{uuid.uuid4().hex[:8]}@example.com",
                                  password_hash=hash_password(PASSWORD), role="admin", is_first_admin=True,
                                  status="active", created_at=timestamp(), updated_at=timestamp())
            db.add(account)
        else:
            account.password_hash = hash_password(PASSWORD)
            account.status = "active"
            account.role = "admin"
        db.commit()
        email = account.email
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_no_api_route_can_edit_or_delete_security_or_audit_records():
    offenders = []
    for route in main.app.routes:
        path = getattr(route, "path", "")
        methods = set(getattr(route, "methods", set()) or set())
        if any(word in path for word in ("security", "audit", "event")) and methods & MUTATING:
            offenders.append((path, sorted(methods & MUTATING)))
    assert offenders == []


def test_purge_removes_only_old_rate_limit_counters_and_keeps_login_history_incidents_and_admin_audit():
    marker = uuid.uuid4().hex
    old = "1999-12-31T00:00:00+00:00"
    rows = {
        "login_succeeded": "login_succeeded",
        "rate_limit": "auth_attempt_login",
        "incident": "login_failed",
        "password_reset": "password_reset_completed",
        "admin_audit": "admin_role_granted",
    }
    with SessionLocal() as db:
        for label, event_type in rows.items():
            db.add(SecurityEvent(event_type=event_type, attempted_email=f"{label}-{marker}@example.com",
                                 ip_address="127.0.0.1", user_agent="audit-test", details=f"marker={marker}",
                                 created_at=old))
        db.commit()

    response = client.request("DELETE", "/api/admin/activity/purge", headers=first_admin_headers(), json={
        "before": "2000-01-01T00:00:00Z", "reason": "Audit immutability regression check.", "confirm": True,
    })
    assert response.status_code == 200, response.text

    with SessionLocal() as db:
        remaining = {
            row.attempted_email.split("-", 1)[0]
            for row in db.query(SecurityEvent).filter(SecurityEvent.details == f"marker={marker}").all()
        }
        assert remaining == {"login_succeeded", "incident", "password_reset", "admin_audit"}
        cleanup_record = db.query(SecurityEvent).filter(
            SecurityEvent.event_type == "admin_activity_retention_cleanup",
        ).order_by(SecurityEvent.id.desc()).first()
        assert cleanup_record is not None
        assert "Audit immutability regression check." in cleanup_record.details


def _register_verified_student() -> int:
    email = f"audit-student-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post("/api/auth/register/student", json={
        "full_name": "Audit Student", "email": email, "password": PASSWORD,
        "education_level": "University", "subjects": ["Mathematics"],
    })
    assert response.status_code == 201, response.text
    with SessionLocal() as db:
        return db.query(UserAccount).filter_by(email=email).one().id


def test_audit_records_identify_actor_affected_account_and_capture_ip_user_agent_and_timestamp():
    from datetime import datetime
    from app.database import SessionLocal
    from app.models import SecurityEvent

    actor_headers = first_admin_headers()
    with SessionLocal() as db:
        actor_id = db.query(UserAccount).filter_by(is_first_admin=True).order_by(UserAccount.id).first().id
    target_id = _register_verified_student()
    granted = client.post(f"/api/admin/users/{target_id}/admin-role", headers={**actor_headers, "User-Agent": "audit-verify-agent"},
                          json={"reason": "Audit verification role grant."})
    assert granted.status_code == 200, granted.text
    exported = client.get("/api/admin/export/users?limit=5", headers={**actor_headers, "User-Agent": "audit-verify-agent"})
    assert exported.status_code == 200, exported.text

    with SessionLocal() as db:
        grant = db.query(SecurityEvent).filter_by(event_type="admin_admin_role_granted").order_by(SecurityEvent.id.desc()).first()
        assert grant is not None
        assert grant.account_id == actor_id                      # acting user
        assert f"target={target_id};" in grant.details           # affected account
        assert "Audit verification role grant." in grant.details # reason
        assert grant.user_agent == "audit-verify-agent"
        assert grant.ip_address                                   # IP address captured
        datetime.fromisoformat(grant.created_at)                  # parseable timestamp

        export = db.query(SecurityEvent).filter_by(event_type="admin_data_exported").order_by(SecurityEvent.id.desc()).first()
        assert export is not None
        assert export.account_id == actor_id
        assert export.user_agent == "audit-verify-agent"
        assert export.ip_address
        datetime.fromisoformat(export.created_at)
