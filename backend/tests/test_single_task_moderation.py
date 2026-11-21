"""Single-item task moderation: Admins and Moderators delete one task with confirmation and audit."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('single-task-moderation-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import PersonalLearningTask, RefreshSession, SecurityEvent, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"
REASON = "Off-topic content reported."


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def staff_headers(role: str) -> dict:
    email = f"single-{role}-{uuid.uuid4().hex[:10]}@example.com"
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
            revoked_at=None, replaced_by=None, user_agent="single-task-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def register_tutor():
    email = f"single-tutor-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post("/api/auth/register/tutor", json={
        "full_name": "Single Tutor", "email": email, "password": PASSWORD,
        "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500,
    })
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def group_task(tutor_headers) -> int:
    group = client.post("/api/groups", headers=tutor_headers, json={"name": "Single Batch", "description": ""}).json()
    task = client.post(f"/api/groups/{group['id']}/tasks", headers=tutor_headers,
                       json={"title": "Off-topic task", "description": "", "video_url": None})
    assert task.status_code == 201, task.text
    return task.json()["id"]


def test_admin_deletes_one_group_task_with_reason_and_it_is_gone_on_repeat():
    tutor = register_tutor()
    task_id = group_task(tutor)
    admin = staff_headers("admin")
    removed = client.request("DELETE", f"/api/admin/group-tasks/{task_id}", headers=admin,
                             json={"confirm": True, "reason": REASON})
    assert removed.status_code == 200, removed.text
    assert removed.json() == {"deleted": True, "task_id": task_id}
    again = client.request("DELETE", f"/api/admin/group-tasks/{task_id}", headers=admin,
                           json={"confirm": True, "reason": REASON})
    assert again.status_code == 404


def test_single_delete_requires_explicit_confirmation():
    tutor = register_tutor()
    task_id = group_task(tutor)
    admin = staff_headers("admin")
    response = client.request("DELETE", f"/api/admin/group-tasks/{task_id}", headers=admin,
                              json={"reason": REASON})
    assert response.status_code == 422


def test_moderator_can_delete_a_single_personal_task_but_students_cannot():
    moderator = staff_headers("moderator")
    with SessionLocal() as db:
        owner = UserAccount(email=f"single-owner-{uuid.uuid4().hex[:10]}@example.com",
                            password_hash=hash_password(PASSWORD), role="student", is_first_admin=False,
                            status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(owner)
        db.flush()
        task = PersonalLearningTask(owner_account_id=owner.id, title="Spam task", description="",
                                    completed=False, created_at=timestamp(), updated_at=timestamp())
        db.add(task)
        db.commit()
        task_id = task.id
    student = staff_headers("student")
    assert client.request("DELETE", f"/api/admin/tasks/{task_id}", headers=student,
                          json={"confirm": True, "reason": REASON}).status_code == 403
    removed = client.request("DELETE", f"/api/admin/tasks/{task_id}", headers=moderator,
                             json={"confirm": True, "reason": REASON})
    assert removed.status_code == 200, removed.text
