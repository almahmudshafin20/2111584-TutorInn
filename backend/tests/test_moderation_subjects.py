import os
import secrets
import sys
import uuid
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('issue27-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import LearningPost, RefreshSession, Student, Tutor, UserAccount

initialize_database()
client = TestClient(main.app)


def register_student(email: str):
    response = client.post("/api/auth/register/student", json={
        "full_name": "Report Student", "email": email, "password": "correct-horse-battery-staple-42",
        "education_level": "University", "subjects": ["Mathematics"],
    })
    assert response.status_code == 201, response.text
    data = response.json()
    return data, {"Authorization": f"Bearer {data['access_token']}"}


def register_tutor(email: str):
    response = client.post("/api/auth/register/tutor", json={
        "full_name": "Report Tutor", "email": email, "password": "correct-horse-battery-staple-42",
        "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500,
    })
    assert response.status_code == 201, response.text
    data = response.json()
    return data, {"Authorization": f"Bearer {data['access_token']}"}


def admin_headers():
    email = f"moderation-admin-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        account = UserAccount(email=email, password_hash=hash_password("correct-horse-battery-staple-42"),
                              role="admin", status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(account)
        db.flush()
        now = timestamp()
        session = RefreshSession(
            account_id=account.id, token_hash=token_hash(secrets.token_urlsafe(48)),
            family_id=str(uuid.uuid4()), csrf_token_hash=token_hash(secrets.token_urlsafe(32)),
            created_at=now, last_used_at=now, expires_at=(utc_now() + timedelta(days=1)).isoformat(),
            revoked_at=None, replaced_by=None, user_agent="moderation-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def test_reports_cover_profiles_tutoring_posts_and_tutoring_requests():
    suffix = uuid.uuid4().hex[:10]
    student, student_headers = register_student(f"reporter-{suffix}@example.com")
    other_student, _ = register_student(f"request-owner-{suffix}@example.com")
    tutor, _ = register_tutor(f"reported-tutor-{suffix}@example.com")
    with SessionLocal() as db:
        other_profile = db.query(Student).filter_by(account_id=other_student["account"]["id"]).one()
        tutor_profile = db.query(Tutor).filter_by(account_id=tutor["account"]["id"]).one()
        offer = LearningPost(
            post_type="tutor", author_name="Report Tutor", subject="Physics", level="HSC", fee=500,
            description="Tutor offer", author_profile_id=tutor_profile.id, author_profile_type="tutor",
            created_at=timestamp(),
        )
        request = LearningPost(
            post_type="student", author_name="Request owner", subject="Mathematics", level="University", fee=500,
            description="Student request", author_profile_id=other_profile.id, author_profile_type="student",
            created_at=timestamp(),
        )
        db.add_all([offer, request])
        db.commit()
        offer_id, request_id, tutor_profile_id = offer.id, request.id, tutor_profile.id

    profile_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "profile", "target_id": tutor_profile_id, "reason": "impersonation",
        "description": "Profile identity concern",
    })
    post_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "tutoring_post", "target_id": offer_id, "reason": "misleading",
        "description": "Offer details appear inaccurate",
    })
    request_report = client.post("/api/reports", headers=student_headers, json={
        "target_type": "tutoring_request", "target_id": request_id, "reason": "spam",
        "description": "Repeated solicitation",
    })
    assert profile_report.status_code == post_report.status_code == request_report.status_code == 201
    duplicate = client.post("/api/reports", headers=student_headers, json={
        "target_type": "profile", "target_id": tutor_profile_id, "reason": "other", "description": "",
    })
    assert duplicate.status_code == 409

    admin = admin_headers()
    listed = client.get("/api/admin/reports?status=pending&limit=20", headers=admin)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 3
    report_id = profile_report.json()["id"]
    reviewed = client.patch(f"/api/admin/reports/{report_id}", headers=admin, json={
        "status": "resolved", "review_note": "Reviewed the profile and recorded the outcome.",
    })
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "resolved"
    assert client.get("/api/admin/reports", headers=student_headers).status_code == 403


def test_admin_subject_catalogue_duplicate_protection_and_reference_safeguards():
    admin = admin_headers()
    suffix = uuid.uuid4().hex[:8]
    name = f"Catalogue {suffix}"
    created = client.post("/api/admin/subjects", headers=admin, json={"name": name})
    assert created.status_code == 201, created.text
    subject = created.json()
    duplicate = client.post("/api/admin/subjects", headers=admin, json={"name": name.upper()})
    assert duplicate.status_code == 409

    with SessionLocal() as db:
        student = Student(
            full_name="Catalogue Test Student", email=f"catalogue-{suffix}@example.com",
            education_level="University", preferred_subjects=name, subjects_json='["' + name + '"]',
        )
        db.add(student)
        db.commit()
    blocked_delete = client.delete(f"/api/admin/subjects/{subject['id']}", headers=admin)
    assert blocked_delete.status_code == 409
    blocked_rename = client.patch(f"/api/admin/subjects/{subject['id']}", headers=admin, json={"name": name + " Updated"})
    assert blocked_rename.status_code == 409

    deactivated = client.patch(f"/api/admin/subjects/{subject['id']}", headers=admin, json={"active": False})
    assert deactivated.status_code == 200
    active = client.get("/api/subjects")
    assert active.status_code == 200
    assert name not in active.json()

    unused = client.post("/api/admin/subjects", headers=admin, json={"name": f"Unused {suffix}"})
    assert unused.status_code == 201
    deleted = client.delete(f"/api/admin/subjects/{unused.json()['id']}", headers=admin)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
