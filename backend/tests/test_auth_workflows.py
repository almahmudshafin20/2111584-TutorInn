import os
import sys
import uuid
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).with_name('issue27-test.db')}"
os.environ["ADMIN_API_KEY"] = "issue-27-test-admin-key"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-with-at-least-thirty-two-characters"
os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-only-admin-bootstrap-token-with-more-than-32-chars"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import jwt
import main

client = TestClient(main.app)


def register_student(email: str):
    return client.post("/api/auth/register/student", json={
        "full_name": "Auth Student",
        "email": email,
        "password": "correct-horse-battery-staple-42",
        "education_level": "University",
        "subjects": ["Mathematics", "Physics"],
    })


def test_student_registration_password_hash_login_and_current_account():
    suffix = uuid.uuid4().hex[:10]
    email = f"student-auth-{suffix}@example.com"
    password = "correct-horse-battery-staple-42"
    registered = register_student(email)
    assert registered.status_code == 201, registered.text
    payload = registered.json()
    assert payload["account"]["email"] == email
    assert payload["account"]["role"] == "student"
    assert payload["expires_in"] == 900
    assert payload["csrf_token"]
    assert "password_hash" not in payload["account"]
    assert "tutorinn_refresh" in registered.cookies
    assert "tutorinn_csrf" in registered.cookies

    from models import Student, UserAccount
    from database import SessionLocal
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(email=email).one()
        profile = db.query(Student).filter_by(email=email).one()
        assert profile.account_id == account.id
        assert account.password_hash != password
        assert account.password_hash.startswith("$argon2")

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    current = client.get("/api/auth/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["role"] == "student"

    login = client.post("/api/auth/login", json={"email": email.upper(), "password": password})
    assert login.status_code == 200, login.text
    assert login.json()["account"]["id"] == payload["account"]["id"]


def test_tutor_registration_and_duplicate_account_email_are_rejected():
    suffix = uuid.uuid4().hex[:10]
    email = f"tutor-auth-{suffix}@example.com"
    payload = {
        "full_name": "Auth Tutor",
        "email": email,
        "password": "correct-horse-battery-staple-42",
        "subjects": ["English", "Bangla"],
        "teaching_level": "HSC",
        "experience_years": 3,
        "hourly_rate": 600,
    }
    created = client.post("/api/auth/register/tutor", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["account"]["role"] == "tutor"
    duplicate = client.post("/api/auth/register/student", json={
        "full_name": "Another Profile",
        "email": email,
        "password": "correct-horse-battery-staple-42",
        "education_level": "HSC",
        "subjects": ["English"],
    })
    assert duplicate.status_code == 409


def test_invalid_and_tampered_access_tokens_are_rejected():
    missing = client.get("/api/auth/me")
    assert missing.status_code == 401

    suffix = uuid.uuid4().hex[:10]
    registered = register_student(f"tamper-{suffix}@example.com")
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["role"] = "admin"
    forged = jwt.encode(claims, "attacker-controlled-secret", algorithm="HS256")
    denied = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert denied.status_code == 401


def test_first_admin_requires_bootstrap_secret_and_uses_shared_authentication():
    denied = client.post("/api/auth/admin/bootstrap", json={
        "email": "first-admin@example.com",
        "password": "correct-horse-battery-staple-42",
    })
    assert denied.status_code == 403

    created = client.post(
        "/api/auth/admin/bootstrap",
        headers={"X-Admin-Bootstrap-Token": os.environ["ADMIN_BOOTSTRAP_TOKEN"]},
        json={"email": "first-admin@example.com", "password": "correct-horse-battery-staple-42"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "admin"

    login = client.post("/api/auth/login", json={
        "email": "first-admin@example.com",
        "password": "correct-horse-battery-staple-42",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]
    admin_check = client.get("/api/auth/admin/check", headers={"Authorization": f"Bearer {token}"})
    assert admin_check.status_code == 200

    student_token = register_student(f"role-check-{uuid.uuid4().hex[:10]}@example.com").json()["access_token"]
    student_check = client.get("/api/auth/admin/check", headers={"Authorization": f"Bearer {student_token}"})
    assert student_check.status_code == 403


def test_refresh_rotation_reuse_detection_revokes_entire_session_family():
    suffix = uuid.uuid4().hex[:10]
    registered = register_student(f"refresh-{suffix}@example.com")
    assert registered.status_code == 201, registered.text
    old_refresh = client.cookies.get("tutorinn_refresh")
    old_csrf = client.cookies.get("tutorinn_csrf")
    old_access = registered.json()["access_token"]

    rotated = client.post("/api/auth/refresh", headers={"X-CSRF-Token": old_csrf})
    assert rotated.status_code == 200, rotated.text
    new_access = rotated.json()["access_token"]
    assert client.cookies.get("tutorinn_refresh") != old_refresh
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"}).status_code == 200

    replay = client.post(
        "/api/auth/refresh",
        cookies={"tutorinn_refresh": old_refresh, "tutorinn_csrf": old_csrf},
        headers={"X-CSRF-Token": old_csrf},
    )
    assert replay.status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_access}"}).status_code == 401


def test_logout_revokes_access_session_and_clears_auth_cookies():
    suffix = uuid.uuid4().hex[:10]
    registered = register_student(f"logout-{suffix}@example.com")
    assert registered.status_code == 201, registered.text
    access = registered.json()["access_token"]
    csrf = client.cookies.get("tutorinn_csrf")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 200

    logged_out = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logged_out.status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401


def test_account_can_list_and_revoke_only_its_own_sessions():
    suffix = uuid.uuid4().hex[:10]
    registered = register_student(f"sessions-{suffix}@example.com")
    assert registered.status_code == 201, registered.text
    access = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {access}"}
    sessions = client.get("/api/auth/sessions", headers=headers)
    assert sessions.status_code == 200
    assert len(sessions.json()) == 1
    session_id = sessions.json()[0]["id"]
    revoked = client.delete(f"/api/auth/sessions/{session_id}", headers=headers)
    assert revoked.status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
