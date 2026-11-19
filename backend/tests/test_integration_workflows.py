"""End-to-end API + database workflow: group work, video link and account deletion.

Covers the Milestone 7 integration requirement across real HTTP routes, the
Admin approval path and the resulting database state. Uses disposable accounts
and synthetic data only.
"""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('integration-workflow-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import LearningGroup, LearningGroupMember, RefreshSession, SecurityEvent, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"
VIDEO = "https://drive.google.com/file/d/integration_ID-1/view?usp=sharing"


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def register(role: str):
    email = f"integ-{role}-{uuid.uuid4().hex[:10]}@example.com"
    if role == "student":
        response = client.post("/api/auth/register/student", json={
            "full_name": "Integration Student", "email": email, "password": PASSWORD,
            "education_level": "University", "subjects": ["Mathematics"],
        })
    else:
        response = client.post("/api/auth/register/tutor", json={
            "full_name": "Integration Tutor", "email": email, "password": PASSWORD,
            "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500,
        })
    assert response.status_code == 201, response.text
    data = response.json()
    return data, {"Authorization": f"Bearer {data['access_token']}"}


def admin_headers():
    email = f"integ-admin-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        account = UserAccount(email=email, password_hash=hash_password(PASSWORD), role="admin",
                              status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(account)
        db.flush()
        now = timestamp()
        session = RefreshSession(
            account_id=account.id, token_hash=token_hash(secrets.token_urlsafe(48)),
            family_id=str(uuid.uuid4()), csrf_token_hash=token_hash(secrets.token_urlsafe(32)),
            created_at=now, last_used_at=now, expires_at=(utc_now() + timedelta(days=1)).isoformat(),
            revoked_at=None, replaced_by=None, user_agent="integration-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def test_group_video_work_survives_member_deletion_and_deleted_account_loses_access():
    tutor, tutor_headers = register("tutor")
    student, student_headers = register("student")
    student_account_id = student["account"]["id"]
    student_email = student["account"]["email"]

    # 1. Tutor builds a group, adds the student and attaches a Drive video task.
    group = client.post("/api/groups", headers=tutor_headers, json={"name": "Integration Batch", "description": ""})
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]
    added = client.post(f"/api/groups/{group_id}/members", headers=tutor_headers, json={"student_email": student_email})
    assert added.status_code == 201, added.text
    task = client.post(f"/api/groups/{group_id}/tasks", headers=tutor_headers,
                       json={"title": "Shared lesson", "description": "Watch", "video_url": VIDEO})
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    # 2. The student sees the task and its validated video link.
    view = client.get(f"/api/groups/{group_id}", headers=student_headers)
    assert view.status_code == 200, view.text
    assert any(row["id"] == task_id and row["video_url"] == VIDEO for row in view.json()["tasks"])

    # 3. The student requests deletion; the Admin approves with the complete option.
    requested = client.post("/api/me/deletion-request", headers=student_headers, json={
        "current_password": PASSWORD, "reason": "Integration test deletion.", "deletion_option": "complete",
    })
    assert requested.status_code == 201, requested.text
    approved = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}",
                            headers=admin_headers(),
                            json={"status": "approved", "deletion_option": "complete", "review_note": "Integration approval."})
    assert approved.status_code == 200, approved.text
    assert approved.json()["deleted"] is True

    # 4. Database state: the student's account and membership are gone, the group and tutor's task remain.
    with SessionLocal() as db:
        assert db.get(UserAccount, student_account_id) is None
        assert db.query(LearningGroupMember).filter_by(student_account_id=student_account_id).count() == 0
        assert db.get(LearningGroup, group_id) is not None

    # 5. Access is revoked end to end: the deleted student cannot log in or use the old token.
    assert client.post("/api/auth/login", json={"email": student_email, "password": PASSWORD}).status_code != 200
    assert client.get("/api/auth/me", headers=student_headers).status_code >= 400

    # 6. The tutor still sees the group and its video task unchanged.
    tutor_view = client.get(f"/api/groups/{group_id}", headers=tutor_headers)
    assert tutor_view.status_code == 200, tutor_view.text
    assert any(row["id"] == task_id and row["video_url"] == VIDEO for row in tutor_view.json()["tasks"])


def test_pending_deletion_blocks_access_and_rejection_restores_group_membership():
    tutor, tutor_headers = register("tutor")
    student, student_headers = register("student")
    student_email = student["account"]["email"]
    group = client.post("/api/groups", headers=tutor_headers, json={"name": "Restore Batch", "description": ""}).json()
    client.post(f"/api/groups/{group['id']}/members", headers=tutor_headers, json={"student_email": student_email})

    requested = client.post("/api/me/deletion-request", headers=student_headers, json={
        "current_password": PASSWORD, "reason": "Pending check.", "deletion_option": "complete",
    })
    assert requested.status_code == 201, requested.text
    assert client.get("/api/auth/me", headers=student_headers).status_code >= 400

    rejected = client.patch(f"/api/admin/account-deletion-requests/{requested.json()['id']}", headers=admin_headers(),
                            json={"status": "rejected", "review_note": "Integration rejection."})
    assert rejected.status_code == 200, rejected.text

    login = client.post("/api/auth/login", json={"email": student_email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    restored = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get(f"/api/groups/{group['id']}", headers=restored).status_code == 200
