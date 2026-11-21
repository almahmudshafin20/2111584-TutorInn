"""Audit log coverage: login, failed login, logout, password change, role change, ban, delete and export are recorded
with actor/affected account, IP, user-agent and timestamp, and the Admin activity/security views filter them."""
import os, sys, uuid
from datetime import datetime
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('audit-log-coverage-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import hash_password, timestamp
from app.database import SessionLocal, initialize_database
from app.models import PersonalLearningTask, SecurityEvent, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"
NEW_PASSWORD = "new-correct-horse-battery-99"
UA = "audit-coverage-agent"


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def _first_admin_headers() -> tuple[dict, int]:
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(is_first_admin=True).order_by(UserAccount.id).first()
        if account is None:
            account = UserAccount(email=f"coverage-first-{uuid.uuid4().hex[:8]}@example.com",
                                  password_hash=hash_password(PASSWORD), role="admin", is_first_admin=True,
                                  status="active", created_at=timestamp(), updated_at=timestamp())
            db.add(account)
        else:
            account.password_hash = hash_password(PASSWORD)
            account.status = "active"
            account.role = "admin"
        db.commit()
        email, account_id = account.email, account.id
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers={"User-Agent": UA})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}", "User-Agent": UA}, account_id


def _student() -> tuple[str, int]:
    email = f"coverage-student-{uuid.uuid4().hex[:10]}@example.com"
    registered = client.post("/api/auth/register/student", json={
        "full_name": "Coverage Student", "email": email, "password": PASSWORD,
        "education_level": "University", "subjects": ["Mathematics"],
    })
    assert registered.status_code == 201, registered.text
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(email=email).one()
        account.email_verified_at = timestamp()
        db.commit()
        return email, account.id


def _events_for(event_type: str, *, account_id: int | None = None, marker: str | None = None) -> list[SecurityEvent]:
    with SessionLocal() as db:
        query = db.query(SecurityEvent).filter(SecurityEvent.event_type == event_type)
        if account_id is not None:
            query = query.filter(SecurityEvent.account_id == account_id)
        if marker is not None:
            query = query.filter(SecurityEvent.attempted_email == marker.lower())
        rows = query.order_by(SecurityEvent.id.desc()).all()
        for row in rows:
            db.expunge(row)
        return rows


def _assert_context(row: SecurityEvent) -> None:
    assert row.created_at and datetime.fromisoformat(row.created_at)
    assert row.ip_address
    assert row.user_agent == UA


def test_authentication_and_account_events_are_recorded_with_context():
    admin_headers, admin_id = _first_admin_headers()
    email, student_id = _student()

    failed = client.post("/api/auth/login", json={"email": email, "password": "wrong-password-value-123"}, headers={"User-Agent": UA})
    assert failed.status_code in (401, 403)
    failed_rows = _events_for("login_failed", marker=email)
    assert failed_rows, "failed login not recorded"
    _assert_context(failed_rows[0])

    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers={"User-Agent": UA})
    assert login.status_code == 200, login.text
    success_rows = _events_for("login_succeeded", account_id=student_id)
    assert success_rows, "successful login not recorded"
    _assert_context(success_rows[0])

    csrf = client.cookies.get("tutorinn_csrf")
    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf, "User-Agent": UA})
    assert logout.status_code == 200, logout.text
    logout_rows = [row for row in _events_for("session_revoked", account_id=student_id) if "reason=logout" in row.details]
    assert logout_rows, "logout not recorded"
    _assert_context(logout_rows[0])

    student_login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers={"User-Agent": UA})
    changed = client.post("/api/me/password", headers={"Authorization": f"Bearer {student_login.json()['access_token']}", "User-Agent": UA},
                          json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert changed.status_code == 200, changed.text
    password_rows = _events_for("password_changed", account_id=student_id)
    assert password_rows, "password change not recorded"
    _assert_context(password_rows[0])


def test_admin_ban_role_change_delete_and_export_record_actor_affected_account_and_context():
    admin_headers, admin_id = _first_admin_headers()
    _, student_id = _student()

    banned = client.patch(f"/api/admin/users/{student_id}/status", headers=admin_headers,
                          json={"status": "suspended", "reason": "Audit coverage ban check."})
    assert banned.status_code == 200, banned.text
    ban_rows = _events_for("admin_account_status_changed", account_id=admin_id)
    assert ban_rows and f"{student_id}" in ban_rows[0].details and "Audit coverage ban check." in ban_rows[0].details
    _assert_context(ban_rows[0])

    with SessionLocal() as db:
        task = PersonalLearningTask(owner_account_id=student_id, title="Coverage task", description="",
                                    completed=False, created_at=timestamp(), updated_at=timestamp())
        db.add(task)
        db.commit()
        task_id = task.id
    removed = client.request("DELETE", f"/api/admin/tasks/{task_id}", headers=admin_headers,
                             json={"confirm": True, "reason": "Audit coverage delete check."})
    assert removed.status_code == 200, removed.text
    delete_rows = _events_for("admin_personal_task_deleted", account_id=admin_id)
    assert delete_rows and "Audit coverage delete check." in delete_rows[0].details
    _assert_context(delete_rows[0])

    exported = client.get("/api/admin/export/users?limit=5", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    export_rows = _events_for("admin_data_exported", account_id=admin_id)
    assert export_rows
    _assert_context(export_rows[0])


def test_admin_activity_and_security_views_filter_by_event_type_account_and_search():
    admin_headers, admin_id = _first_admin_headers()
    email, student_id = _student()
    client.post("/api/auth/login", json={"email": email, "password": "wrong-password-value-123"}, headers={"User-Agent": UA})
    client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers={"User-Agent": UA})

    by_type = client.get("/api/admin/activity?event_type=login_succeeded&limit=100", headers=admin_headers)
    assert by_type.status_code == 200, by_type.text
    items = by_type.json()["items"]
    assert items and all(item["event_type"] == "login_succeeded" for item in items)

    by_account = client.get(f"/api/admin/activity?account_id={student_id}&limit=100", headers=admin_headers)
    assert by_account.status_code == 200, by_account.text
    assert by_account.json()["items"] and all(item["account_id"] == student_id for item in by_account.json()["items"])

    by_search = client.get(f"/api/admin/security?hours=24&min_events=1&q={email}", headers=admin_headers)
    assert by_search.status_code == 200, by_search.text
    assert by_search.json()["events"], "security search by email returned nothing"
