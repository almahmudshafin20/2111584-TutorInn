import os
import sys
import uuid
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).with_name('admin-test.db')}"
os.environ["JWT_SECRET"] = "admin-test-jwt-secret-with-at-least-thirty-two-characters"
os.environ["PASSWORD_PEPPER"] = "admin-test-password-pepper-with-at-least-32-characters"
os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "admin-test-bootstrap-token-with-at-least-32-characters"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import main
from app.database import initialize_database, SessionLocal
from app.models import RefreshSession, UserAccount

initialize_database()
client = TestClient(main.app)
bootstrap = client.post("/api/auth/admin/bootstrap",
    headers={"X-Admin-Bootstrap-Token": os.environ["ADMIN_BOOTSTRAP_TOKEN"]},
    json={"email": "admin-management@example.test", "password": "long-admin-test-password-123"})
assert bootstrap.status_code in {201, 409}, bootstrap.text
admin_login = client.post("/api/auth/login", json={
    "email": "admin-management@example.test", "password": "long-admin-test-password-123"})
assert admin_login.status_code == 200, admin_login.text
ADMIN_HEADERS = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}


def student_payload(email):
    return {"full_name": "Admin Test Student", "email": email,
            "password": "long-student-test-password-123", "education_level": "University",
            "subjects": ["Mathematics"]}


def test_admin_overview_and_users_are_role_protected():
    created = client.post("/api/auth/register/student", json=student_payload(f"s-{uuid.uuid4().hex[:8]}@example.test"))
    assert created.status_code == 201, created.text
    assert client.get("/api/admin/overview").status_code == 401
    student_headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
    assert client.get("/api/admin/overview", headers=student_headers).status_code == 403
    overview = client.get("/api/admin/overview", headers=ADMIN_HEADERS)
    assert overview.status_code == 200, overview.text
    assert overview.json()["students"] >= 1
    users = client.get("/api/admin/users?role=student", headers=ADMIN_HEADERS)
    assert users.status_code == 200, users.text
    assert users.json()["total"] >= 1


def test_admin_suspension_revokes_sessions_and_blocks_login():
    email = f"moderate-{uuid.uuid4().hex[:8]}@example.test"
    created = client.post("/api/auth/register/student", json=student_payload(email))
    assert created.status_code == 201, created.text
    account_id = created.json()["account"]["id"]
    changed = client.patch(f"/api/admin/users/{account_id}/status", headers=ADMIN_HEADERS,
        json={"status": "suspended", "reason": "Repeated policy violations"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "suspended"
    with SessionLocal() as db:
        sessions = db.query(RefreshSession).filter_by(account_id=account_id).all()
        assert sessions and all(item.revoked_at for item in sessions)
        account = db.get(UserAccount, account_id)
        assert account.status == "suspended"
    login = client.post("/api/auth/login", json={
        "email": email, "password": "long-student-test-password-123"})
    assert login.status_code == 403


def test_admin_can_review_tutor_without_changing_role():
    email = f"review-{uuid.uuid4().hex[:8]}@example.test"
    created = client.post("/api/auth/register/tutor", json={
        "full_name": "Review Tutor", "email": email, "password": "long-tutor-test-password-123",
        "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 4, "hourly_rate": 700,
    })
    assert created.status_code == 201, created.text
    tutor_id = created.json()["profile"]["id"]
    reviewed = client.patch(f"/api/admin/tutors/{tutor_id}/verification", headers=ADMIN_HEADERS,
        json={"status": "approved", "note": "Qualification checked"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "approved"
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {created.json()['access_token']}"}).json()["role"] == "tutor"
    listing = client.get("/api/admin/tutors?verification_status=approved", headers=ADMIN_HEADERS)
    assert listing.status_code == 200
    assert any(item["id"] == tutor_id for item in listing.json()["items"])


def test_admin_bulk_moderation_reports_each_result_and_limits_batch_size():
    email = f"bulk-{uuid.uuid4().hex[:8]}@example.test"
    created = client.post("/api/auth/register/student", json=student_payload(email))
    account_id = created.json()["account"]["id"]
    response = client.post("/api/admin/users/bulk-status", headers=ADMIN_HEADERS, json={
        "account_ids": [account_id, 99999999], "status": "banned", "reason": "Repeated abuse reports",
    })
    assert response.status_code == 200, response.text
    assert response.json()["succeeded"] == 1
    assert response.json()["failed"] == 1
    oversized = client.post("/api/admin/users/bulk-status", headers=ADMIN_HEADERS, json={
        "account_ids": list(range(1, 52)), "status": "banned", "reason": "Repeated abuse reports",
    })
    assert oversized.status_code == 422
