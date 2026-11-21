"""Bulk learning-group moderation: capped, confirmed, reasoned, partial-failure reporting and audit per group."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('bulk-group-moderation-test.db')}")
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
REASON = "Bulk moderation regression check."


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def staff_headers(role: str) -> dict:
    email = f"bulk-group-{role}-{uuid.uuid4().hex[:10]}@example.com"
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
            revoked_at=None, replaced_by=None, user_agent="bulk-group-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def make_group() -> int:
    email = f"bulk-group-tutor-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post("/api/auth/register/tutor", json={
        "full_name": "Bulk Tutor", "email": email, "password": PASSWORD,
        "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500,
    })
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    group = client.post("/api/groups", headers=headers, json={"name": f"Bulk {uuid.uuid4().hex[:6]}", "description": ""})
    assert group.status_code in (200, 201), group.text
    return group.json()["id"]


def bulk_delete(headers: dict, payload: dict):
    return client.request("DELETE", "/api/admin/groups/bulk", headers=headers, json=payload)


def test_bulk_delete_reports_partial_failures_and_audits_each_removed_group():
    admin = staff_headers("admin")
    first, second = make_group(), make_group()
    response = bulk_delete(admin, {"group_ids": [first, second, 999999999], "confirm": True, "reason": REASON})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["succeeded"] == 2 and body["failed"] == 1
    assert [item["success"] for item in body["results"]] == [True, True, False]
    with SessionLocal() as db:
        audited = db.query(SecurityEvent).filter_by(event_type="admin_learning_group_deleted").all()
        assert sum(1 for row in audited if REASON in row.details) >= 2


def test_bulk_delete_requires_confirmation_reason_and_a_bounded_unique_list():
    admin = staff_headers("admin")
    group = make_group()
    assert bulk_delete(admin, {"group_ids": [group], "reason": REASON}).status_code == 422
    assert bulk_delete(admin, {"group_ids": [group], "confirm": True, "reason": "no"}).status_code == 422
    assert bulk_delete(admin, {"group_ids": [group, group], "confirm": True, "reason": REASON}).status_code == 422
    assert bulk_delete(admin, {"group_ids": list(range(1, 52)), "confirm": True, "reason": REASON}).status_code == 422


def test_moderators_can_bulk_delete_groups_but_students_cannot():
    group = make_group()
    assert bulk_delete(staff_headers("student"), {"group_ids": [group], "confirm": True, "reason": REASON}).status_code == 403
    moderator = staff_headers("moderator")
    assert bulk_delete(moderator, {"group_ids": [group], "confirm": True, "reason": REASON}).json()["succeeded"] == 1
