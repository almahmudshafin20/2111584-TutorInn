import os, sys, uuid
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('issue27-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import main
from app.database import initialize_database

initialize_database()
client = TestClient(main.app)


def student_headers():
    email = f"personal-task-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post("/api/auth/register/student", json={
        "full_name": "Task Student", "email": email,
        "password": "correct-horse-battery-staple-42",
        "education_level": "University", "subjects": ["Math"],
    })
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_personal_tasks_crud_filters_summary_and_owner_isolation():
    owner = student_headers()
    other = student_headers()
    created = client.post("/api/me/tasks", headers=owner, json={
        "title": "  Algebra revision  ", "description": "Practice equations",
        "category": "Math", "due_date": (date.today() - timedelta(days=1)).isoformat(),
    })
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Algebra revision"
    assert task["status"] == "overdue"
    task_id = task["id"]

    assert client.get("/api/me/tasks", headers=owner).json()[0]["id"] == task_id
    assert client.get("/api/me/tasks", headers=other).json() == []
    assert client.get(f"/api/me/tasks/{task_id}", headers=other).status_code == 404
    assert client.put(f"/api/me/tasks/{task_id}", headers=other, json={
        "title": "Hijack", "description": "", "category": None,
        "due_date": None, "completed": False,
    }).status_code == 404
    assert client.delete(f"/api/me/tasks/{task_id}", headers=other).status_code == 404

    filtered = client.get("/api/me/tasks?q=equations&category=math&status=overdue", headers=owner)
    assert filtered.status_code == 200 and [row["id"] for row in filtered.json()] == [task_id]
    summary = client.get("/api/me/tasks/summary", headers=owner).json()
    assert summary["total_count"] == 1 and summary["overdue_count"] == 1
    assert summary["categories"] == ["Math"]

    updated = client.put(f"/api/me/tasks/{task_id}", headers=owner, json={
        "title": "Algebra revision", "description": "Practice equations",
        "category": "Math", "due_date": None, "completed": True,
    })
    assert updated.status_code == 200 and updated.json()["status"] == "completed"
    assert client.get("/api/me/tasks/summary", headers=owner).json()["completed_count"] == 1
    assert client.delete(f"/api/me/tasks/{task_id}", headers=owner).status_code == 204
    assert client.get("/api/me/tasks", headers=owner).json() == []


def test_personal_task_validation_and_uncategorized_filter():
    owner = student_headers()
    invalid = client.post("/api/me/tasks", headers=owner, json={"title": "   "})
    assert invalid.status_code == 422
    created = client.post("/api/me/tasks", headers=owner, json={
        "title": "Read chapter", "description": "", "category": "   ",
        "due_date": None, "completed": False,
    })
    assert created.status_code == 201 and created.json()["category"] is None
    filtered = client.get("/api/me/tasks?uncategorized=true", headers=owner)
    assert filtered.status_code == 200 and len(filtered.json()) == 1
