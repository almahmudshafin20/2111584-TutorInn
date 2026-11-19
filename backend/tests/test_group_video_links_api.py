"""API-level coverage for Google Drive video links on Group Learning tasks."""
import os, sys, uuid
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('group-video-link-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.database import initialize_database
initialize_database()
client = TestClient(main.app)

VALID_LINK = "https://drive.google.com/file/d/abc_123-XYZ/view?usp=sharing"


@pytest.fixture(autouse=True)
def reset_test_auth_attempts():
    from app.models import SecurityEvent
    from app.database import SessionLocal
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(
            SecurityEvent.event_type.like("auth_attempt_%"),
        ).delete(synchronize_session=False)
        db.commit()
    yield


def account(role):
    email = f"video-{role}-{uuid.uuid4().hex[:10]}@example.com"
    if role == "student":
        payload = {"full_name": "Video Student", "email": email, "password": "correct-horse-battery-staple-42", "education_level": "University", "subjects": ["Math"]}
        response = client.post("/api/auth/register/student", json=payload)
    else:
        payload = {"full_name": "Video Tutor", "email": email, "password": "correct-horse-battery-staple-42", "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500}
        response = client.post("/api/auth/register/tutor", json=payload)
    assert response.status_code == 201, response.text
    return email, {"Authorization": "Bearer " + response.json()["access_token"]}


def create_group(headers):
    response = client.post("/api/groups", headers=headers, json={"name": "Video Batch", "description": ""})
    assert response.status_code == 201, response.text
    return response.json()


def add_student(group_id, tutor_headers, email):
    response = client.post(f"/api/groups/{group_id}/members", headers=tutor_headers, json={"student_email": email})
    assert response.status_code == 201, response.text


def test_owner_attaches_a_drive_video_and_members_receive_the_same_link():
    _, tutor = account("tutor")
    student_email, student = account("student")
    group = create_group(tutor)
    add_student(group["id"], tutor, student_email)

    created = client.post(f"/api/groups/{group['id']}/tasks", headers=tutor,
                          json={"title": "Lesson 1", "description": "Watch first", "video_url": VALID_LINK})
    assert created.status_code == 201, created.text
    assert created.json()["video_url"] == VALID_LINK

    # Members see a task only when they are assigned to it, so assign the whole group first.
    assigned = client.post(f"/api/groups/{group['id']}/tasks/{created.json()['id']}/assignments", headers=tutor,
                           json={"all_members": True, "student_account_ids": []})
    assert assigned.status_code == 200, assigned.text

    # Assigned members can read the task and see the same validated share link.
    group_view = client.get(f"/api/groups/{group['id']}", headers=student)
    assert group_view.status_code == 200, group_view.text
    member_tasks = {task["title"]: task for task in group_view.json()["tasks"]}
    assert member_tasks["Lesson 1"]["video_url"] == VALID_LINK


def test_invalid_video_link_is_rejected_by_the_api_and_no_task_is_created():
    _, tutor = account("tutor")
    group = create_group(tutor)
    response = client.post(f"/api/groups/{group['id']}/tasks", headers=tutor,
                           json={"title": "Bad link", "description": "", "video_url": "https://evil.example/file/d/abc123/view"})
    assert response.status_code == 422, response.text

    tasks_before = client.get(f"/api/groups/{group['id']}", headers=tutor).json()
    assert all(task.get("title") != "Bad link" for task in tasks_before.get("tasks", []))


def test_owner_can_replace_and_remove_a_task_video_link():
    _, tutor = account("tutor")
    group = create_group(tutor)
    task = client.post(f"/api/groups/{group['id']}/tasks", headers=tutor,
                       json={"title": "Lesson 2", "description": "", "video_url": VALID_LINK}).json()

    replacement = "https://drive.google.com/open?id=replacement_ID-9"
    updated = client.put(f"/api/groups/{group['id']}/tasks/{task['id']}", headers=tutor,
                         json={"title": "Lesson 2", "description": "", "video_url": replacement, "due_date": None})
    assert updated.status_code == 200, updated.text
    assert updated.json()["video_url"] == replacement

    removed = client.put(f"/api/groups/{group['id']}/tasks/{task['id']}", headers=tutor,
                         json={"title": "Lesson 2", "description": "", "video_url": None, "due_date": None})
    assert removed.status_code == 200, removed.text
    assert removed.json()["video_url"] is None


def test_student_cannot_attach_or_change_a_video_on_a_group_task():
    _, tutor = account("tutor")
    student_email, student = account("student")
    group = create_group(tutor)
    add_student(group["id"], tutor, student_email)
    task = client.post(f"/api/groups/{group['id']}/tasks", headers=tutor,
                       json={"title": "Lesson 3", "description": "", "video_url": None}).json()

    attempt = client.put(f"/api/groups/{group['id']}/tasks/{task['id']}", headers=student,
                         json={"title": "Lesson 3", "description": "", "video_url": VALID_LINK, "due_date": None})
    assert attempt.status_code == 403, attempt.text


def test_non_member_cannot_read_a_group_or_its_video_task():
    _, tutor = account("tutor")
    _, stranger = account("student")
    group = create_group(tutor)
    client.post(f"/api/groups/{group['id']}/tasks", headers=tutor,
                json={"title": "Private lesson", "description": "", "video_url": VALID_LINK})
    assert client.get(f"/api/groups/{group['id']}", headers=stranger).status_code == 404
