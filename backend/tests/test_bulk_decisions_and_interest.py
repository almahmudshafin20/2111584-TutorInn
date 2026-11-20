"""Bulk tutor verification, tutor-interest review and the Decisions log, with audit and lock rules."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('bulk-decisions-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import InterestResponse, LearningPost, RefreshSession, SecurityEvent, Tutor, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"


def staff_headers(role: str) -> dict:
    email = f"decisions-{role}-{uuid.uuid4().hex[:10]}@example.com"
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
            revoked_at=None, replaced_by=None, user_agent="decisions-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def make_tutor() -> int:
    email = f"decisions-tutor-{uuid.uuid4().hex[:10]}@example.com"
    created = client.post("/api/auth/register/tutor", json={
        "full_name": "Decision Tutor", "email": email, "password": PASSWORD,
        "subjects": ["Physics"], "teaching_level": "HSC", "experience_years": 3, "hourly_rate": 500,
    })
    assert created.status_code == 201, created.text
    with SessionLocal() as db:
        return db.query(Tutor).filter_by(account_id=created.json()["account"]["id"]).one().id


def make_open_interest(tutor_id: int) -> tuple[int, int]:
    with SessionLocal() as db:
        post = LearningPost(post_type="student", author_name="Request owner", subject="Physics", level="HSC",
                            fee=500, description="Decision test request", status="Pending",
                            author_profile_id=1, author_profile_type="student", created_at=timestamp())
        db.add(post)
        db.flush()
        response = InterestResponse(post_id=post.id, profile_id=tutor_id, profile_type="tutor",
                                    response="Interested", review_status="Pending",
                                    created_at=timestamp(), updated_at=timestamp())
        db.add(response)
        db.commit()
        return post.id, response.id


def test_bulk_tutor_verification_sets_each_tutor_and_reports_partial_failures():
    headers = staff_headers("admin")
    first, second = make_tutor(), make_tutor()
    result = client.post("/api/admin/tutors/bulk-verification", headers=headers,
                         json={"tutor_ids": [first, second, 99999999], "status": "approved", "note": "Checked"})
    assert result.status_code == 200, result.text
    assert result.json()["succeeded"] == 2 and result.json()["failed"] == 1
    approved = client.get("/api/admin/tutors?verification_status=approved", headers=headers)
    assert {item["id"] for item in approved.json()["items"]} >= {first, second}


def test_bulk_tutor_verification_validates_status_ids_and_limit():
    headers = staff_headers("admin")
    tutor = make_tutor()
    bad_status = client.post("/api/admin/tutors/bulk-verification", headers=headers,
                             json={"tutor_ids": [tutor], "status": "suspended", "note": ""})
    assert bad_status.status_code == 422
    empty = client.post("/api/admin/tutors/bulk-verification", headers=headers,
                        json={"tutor_ids": [], "status": "pending", "note": ""})
    assert empty.status_code == 422
    boolean_id = client.post("/api/admin/tutors/bulk-verification", headers=headers,
                             json={"tutor_ids": [True], "status": "pending", "note": ""})
    assert boolean_id.status_code == 422
    too_many = client.post("/api/admin/tutors/bulk-verification", headers=headers,
                           json={"tutor_ids": list(range(1, 202)), "status": "pending", "note": ""})
    assert too_many.status_code == 422


def test_tutor_interest_can_change_while_open_and_locks_after_acceptance():
    headers = staff_headers("admin")
    tutor_id = make_tutor()
    post_id, response_id = make_open_interest(tutor_id)

    listed = client.get("/api/admin/interest-responses?review_status=Pending", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == response_id for item in listed.json())

    approved = client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                           json={"status": "Approved", "reason": "Good fit"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["review_status"] == "Approved"
    assert client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                       json={"status": "Approved", "reason": ""}).status_code == 409

    rejected = client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                           json={"status": "Rejected", "reason": "Changed mind"})
    assert rejected.status_code == 200 and rejected.json()["review_status"] == "Rejected"
    reset = client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                        json={"status": "Pending", "reason": ""})
    assert reset.status_code == 200 and reset.json()["review_status"] == "Pending"
    assert client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                       json={"status": "Maybe", "reason": ""}).status_code == 422

    with SessionLocal() as db:
        db.get(LearningPost, post_id).status = "Accepted"
        db.commit()
    locked = client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                         json={"status": "Rejected", "reason": "Too late"})
    assert locked.status_code == 409

    with SessionLocal() as db:
        events = db.query(SecurityEvent).filter_by(event_type="admin_interest_review_changed",
                                                   attempted_email=str(response_id)).all()
        assert len(events) == 3
        assert all(event.account_id is not None for event in events)


def test_decisions_log_names_the_admin_for_tutor_and_interest_changes():
    headers = staff_headers("admin")
    tutor_id = make_tutor()
    _, response_id = make_open_interest(tutor_id)
    assert client.post(f"/api/admin/interest-responses/{response_id}/review", headers=headers,
                       json={"status": "Rejected", "reason": "Log check"}).status_code == 200
    assert client.post("/api/admin/tutors/bulk-verification", headers=headers,
                       json={"tutor_ids": [tutor_id], "status": "rejected", "note": "Log check"}).status_code == 200

    decisions = client.get("/api/admin/decisions", headers=headers)
    assert decisions.status_code == 200, decisions.text
    body = decisions.json()
    tutor_row = next(item for item in body["tutors"] if item["tutor_id"] == tutor_id)
    assert tutor_row["status"] == "rejected"
    assert tutor_row["actor"]["label"] and tutor_row["actor"]["email"]
    interest_row = next(item for item in body["interest_decisions"] if item["target"] == str(response_id))
    assert interest_row["status"] == "rejected"
    assert interest_row["actor"]["label"] and interest_row["actor"]["email"]
