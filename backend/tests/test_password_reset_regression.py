"""Password-reset regressions: rate limits, rejected/expired/superseded tokens, same-password and suspended-account guards."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('password-reset-regression-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import PasswordResetRequest, PasswordResetToken, SecurityEvent, UserAccount
from app.routers import password_resets

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"
NEW_PASSWORD = "a-new-unique-password-2026"
FAKE_TOKEN = "not-a-real-token-value-0000"


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


@pytest.fixture
def delivery(monkeypatch):
    sent = []

    def fake_delivery(to_email, raw_token):
        sent.append({"email": to_email, "token": raw_token})
        return True

    monkeypatch.setattr(password_resets, "send_password_reset_link", fake_delivery)
    return sent


def verified_student(suffix: str | None = None) -> str:
    email = f"reset-reg-{suffix or uuid.uuid4().hex[:10]}@example.com"
    response = client.post("/api/auth/register/student", json={
        "full_name": "Reset Regression", "email": email, "password": PASSWORD,
        "education_level": "University", "subjects": ["Mathematics"],
    })
    assert response.status_code == 201, response.text
    with SessionLocal() as db:
        db.query(UserAccount).filter_by(email=email).one().email_verified_at = timestamp()
        db.commit()
    return email


def reviewer_headers() -> dict:
    email = f"reset-reviewer-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        db.add(UserAccount(email=email, password_hash=hash_password(PASSWORD), role="admin",
                           is_first_admin=False, status="active", created_at=timestamp(), updated_at=timestamp()))
        db.commit()
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def pending_request_id(email: str) -> int:
    with SessionLocal() as db:
        return db.query(PasswordResetRequest).filter_by(account_email=email, status="pending").order_by(
            PasswordResetRequest.id.desc()).first().id


def submit_request(email: str) -> None:
    assert client.post("/api/auth/password-reset/request", json={"email": email}).status_code == 202


def approve(request_id: int, headers: dict):
    return client.patch(f"/api/admin/password-reset-requests/{request_id}", headers=headers,
                        json={"status": "approved", "review_note": "Identity checked."})


def complete(token: str, password: str = NEW_PASSWORD):
    return client.post("/api/auth/password-reset/complete", json={
        "token": token, "new_password": password, "confirm_password": password,
    })


def test_reset_request_endpoint_is_rate_limited_per_ip(monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_REQUEST_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("PASSWORD_RESET_REQUEST_WINDOW_SECONDS", "3600")
    email = verified_student()
    assert client.post("/api/auth/password-reset/request", json={"email": email}).status_code == 202
    assert client.post("/api/auth/password-reset/request", json={"email": email}).status_code == 202
    limited = client.post("/api/auth/password-reset/request", json={"email": email})
    assert limited.status_code == 429


def test_reset_complete_endpoint_is_rate_limited_per_ip(monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_COMPLETE_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("PASSWORD_RESET_COMPLETE_WINDOW_SECONDS", "3600")
    assert complete(FAKE_TOKEN).status_code == 400
    assert complete(FAKE_TOKEN).status_code == 400
    assert complete(FAKE_TOKEN).status_code == 429


def test_unknown_and_garbage_tokens_get_the_same_generic_rejection():
    unknown = complete(secrets.token_urlsafe(48))
    garbage = complete("z" * 25)
    assert unknown.status_code == garbage.status_code == 400
    assert unknown.json() == garbage.json()


def test_rejected_request_never_issues_a_token_and_cannot_be_approved_later(delivery):
    email = verified_student()
    submit_request(email)
    headers = reviewer_headers()
    request_id = pending_request_id(email)
    rejected = client.patch(f"/api/admin/password-reset-requests/{request_id}", headers=headers,
                            json={"status": "rejected", "review_note": "Not the account holder."})
    assert rejected.status_code == 200, rejected.text
    assert delivery == []
    with SessionLocal() as db:
        assert db.query(PasswordResetToken).filter_by(request_id=request_id).count() == 0
    again = approve(request_id, headers)
    assert again.status_code == 409


def test_expired_reset_token_is_rejected_and_password_is_unchanged(delivery):
    email = verified_student()
    submit_request(email)
    approve(pending_request_id(email), reviewer_headers())
    token = delivery[-1]["token"]
    with SessionLocal() as db:
        row = db.query(PasswordResetToken).filter_by(token_hash=token_hash(token)).one()
        row.expires_at = (utc_now() - timedelta(minutes=1)).isoformat()
        db.commit()
    expired = complete(token)
    assert expired.status_code == 400
    assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


def test_reissued_approval_invalidates_the_earlier_token(delivery):
    email = verified_student()
    headers = reviewer_headers()
    submit_request(email)
    approve(pending_request_id(email), headers)
    first_token = delivery[-1]["token"]
    submit_request(email)
    approve(pending_request_id(email), headers)
    second_token = delivery[-1]["token"]
    assert first_token != second_token
    assert complete(first_token).status_code == 400
    assert complete(second_token).status_code == 200


def test_reset_cannot_reuse_the_current_password(delivery):
    email = verified_student()
    submit_request(email)
    approve(pending_request_id(email), reviewer_headers())
    same = complete(delivery[-1]["token"], password=PASSWORD)
    assert same.status_code == 422
    assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    assert complete(delivery[-1]["token"]).status_code == 200


def test_suspended_account_cannot_complete_a_reset_it_already_received(delivery):
    email = verified_student()
    submit_request(email)
    approve(pending_request_id(email), reviewer_headers())
    token = delivery[-1]["token"]
    with SessionLocal() as db:
        db.query(UserAccount).filter_by(email=email).one().status = "suspended"
        db.commit()
    blocked = complete(token)
    assert blocked.status_code == 400
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(email=email).one()
        assert account.password_hash != hash_password(NEW_PASSWORD)
        assert db.query(PasswordResetToken).filter_by(account_id=account.id, invalidated_at=None, used_at=None).count() == 0


def test_failed_email_delivery_saves_no_token_and_leaves_request_pending(monkeypatch):
    def failing_delivery(to_email, raw_token):
        return False

    monkeypatch.setattr(password_resets, "send_password_reset_link", failing_delivery)
    email = verified_student()
    submit_request(email)
    request_id = pending_request_id(email)
    response = approve(request_id, reviewer_headers())
    assert response.status_code == 503
    with SessionLocal() as db:
        assert db.query(PasswordResetToken).filter_by(request_id=request_id).count() == 0
        assert db.get(PasswordResetRequest, request_id).status == "pending"


def test_reset_request_for_unverified_account_is_silently_ignored():
    email = f"reset-reg-unverified-{uuid.uuid4().hex[:8]}@example.com"
    assert client.post("/api/auth/register/student", json={
        "full_name": "Unverified", "email": email, "password": PASSWORD,
        "education_level": "University", "subjects": ["Mathematics"],
    }).status_code == 201
    response = client.post("/api/auth/password-reset/request", json={"email": email})
    assert response.status_code == 202
    with SessionLocal() as db:
        account = db.query(UserAccount).filter_by(email=email).one()
        assert db.query(PasswordResetRequest).filter_by(account_id=account.id).count() == 0
