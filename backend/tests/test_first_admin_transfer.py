"""First Admin ownership transfer: explicit acceptance, atomic switch, safeguards and exactly one First Admin."""
import os, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('first-admin-transfer-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import hash_password, timestamp, utc_now
from app.database import SessionLocal, initialize_database
from app.models import FirstAdminTransfer, RefreshSession, SecurityEvent, UserAccount

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.query(FirstAdminTransfer).delete(synchronize_session=False)
        db.commit()
    yield


@pytest.fixture
def transfer_accounts():
    """Make one isolated First Admin and one eligible Admin; restore the shared First Admin flags afterwards."""
    with SessionLocal() as db:
        original_first_admin_ids = [row.id for row in db.query(UserAccount).filter_by(is_first_admin=True).all()]
        db.query(UserAccount).update({"is_first_admin": False}, synchronize_session=False)
        suffix = uuid.uuid4().hex[:8]
        first = UserAccount(email=f"transfer-first-{suffix}@example.com", password_hash=hash_password(PASSWORD),
                            role="admin", is_first_admin=True, status="active",
                            created_at=timestamp(), updated_at=timestamp())
        recipient = UserAccount(email=f"transfer-admin-{suffix}@example.com", password_hash=hash_password(PASSWORD),
                                role="admin", is_first_admin=False, status="active",
                                created_at=timestamp(), updated_at=timestamp())
        other_admin = UserAccount(email=f"transfer-other-{suffix}@example.com", password_hash=hash_password(PASSWORD),
                                  role="admin", is_first_admin=False, status="active",
                                  created_at=timestamp(), updated_at=timestamp())
        student = UserAccount(email=f"transfer-student-{suffix}@example.com", password_hash=hash_password(PASSWORD),
                              role="student", is_first_admin=False, status="active",
                              created_at=timestamp(), updated_at=timestamp())
        db.add_all([first, recipient, other_admin, student])
        db.commit()
        emails = {"first": first.email, "recipient": recipient.email, "other": other_admin.email, "student": student.email}
        ids = {"first": first.id, "recipient": recipient.id, "other": other_admin.id, "student": student.id}
    yield {"emails": emails, "ids": ids}
    with SessionLocal() as db:
        db.query(UserAccount).update({"is_first_admin": False}, synchronize_session=False)
        for account_id in original_first_admin_ids:
            account = db.get(UserAccount, account_id)
            if account is not None:
                account.is_first_admin = True
        db.commit()


def login(email: str) -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def start(headers: dict, recipient_email: str, password: str = PASSWORD, confirm: str | None = None):
    return client.post("/api/admin/first-admin-transfer", headers=headers, json={
        "recipient_email": recipient_email, "confirm_recipient_email": confirm or recipient_email, "password": password,
    })


def test_only_the_current_first_admin_can_start_and_must_re_enter_password_and_recipient_email(transfer_accounts):
    emails = transfer_accounts["emails"]
    other = login(emails["other"])
    assert start(other, emails["recipient"]).status_code == 403
    first = login(emails["first"])
    assert start(first, emails["recipient"], password="wrong-password-value-123").status_code == 403
    assert start(first, emails["recipient"], confirm=emails["other"]).status_code == 422


def test_recipient_must_be_an_active_eligible_admin(transfer_accounts):
    emails = transfer_accounts["emails"]
    first = login(emails["first"])
    assert start(first, emails["student"]).status_code == 422
    assert start(first, emails["first"]).status_code == 422
    assert start(first, f"missing-{uuid.uuid4().hex[:6]}@example.com").status_code == 422
    with SessionLocal() as db:
        db.get(UserAccount, transfer_accounts["ids"]["other"]).status = "suspended"
        db.commit()
    assert start(first, emails["other"]).status_code == 422


def test_only_one_transfer_can_be_pending_and_visibility_is_limited(transfer_accounts):
    emails = transfer_accounts["emails"]
    first = login(emails["first"])
    created = start(first, emails["recipient"])
    assert created.status_code == 201, created.text
    assert start(first, emails["other"]).status_code == 409
    recipient = login(emails["recipient"])
    other = login(emails["other"])
    assert client.get("/api/admin/first-admin-transfer", headers=recipient).json()["pending"]["status"] == "pending"
    assert client.get("/api/admin/first-admin-transfer", headers=first).json()["pending"]["status"] == "pending"
    assert client.get("/api/admin/first-admin-transfer", headers=other).json()["pending"] is None


def test_recipient_can_decline_and_a_new_transfer_can_then_start(transfer_accounts):
    emails = transfer_accounts["emails"]
    first = login(emails["first"])
    start(first, emails["recipient"])
    recipient = login(emails["recipient"])
    assert client.post("/api/admin/first-admin-transfer/decline", headers=login(emails["other"])).status_code == 403
    assert client.post("/api/admin/first-admin-transfer/decline", headers=recipient).json()["status"] == "declined"
    assert start(first, emails["other"]).status_code == 201


def test_initiator_can_cancel_but_others_cannot(transfer_accounts):
    emails = transfer_accounts["emails"]
    first = login(emails["first"])
    start(first, emails["recipient"])
    assert client.request("DELETE", "/api/admin/first-admin-transfer", headers=login(emails["other"])).status_code == 403
    assert client.request("DELETE", "/api/admin/first-admin-transfer", headers=first).json()["status"] == "cancelled"


def test_acceptance_switches_first_admin_atomically_and_revokes_sessions(transfer_accounts):
    emails, ids = transfer_accounts["emails"], transfer_accounts["ids"]
    first = login(emails["first"])
    recipient = login(emails["recipient"])
    start(first, emails["recipient"])
    assert client.post("/api/admin/first-admin-transfer/accept", headers=login(emails["other"])).status_code == 403

    accepted = client.post("/api/admin/first-admin-transfer/accept", headers=recipient)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["former_first_admin_role"] == "admin"

    with SessionLocal() as db:
        first_admins = db.query(UserAccount).filter_by(is_first_admin=True).all()
        assert [row.id for row in first_admins] == [ids["recipient"]]
        former = db.get(UserAccount, ids["first"])
        assert former.role == "admin" and former.is_first_admin is False
        assert db.query(RefreshSession).filter(
            RefreshSession.account_id.in_([ids["first"], ids["recipient"]]), RefreshSession.revoked_at.is_(None),
        ).count() == 0
        event = db.query(SecurityEvent).filter_by(event_type="first_admin_transfer_accepted").order_by(SecurityEvent.id.desc()).first()
        assert event is not None and f"new_first_admin_account_id={ids['recipient']}" in event.details
        assert "password" not in event.details.lower() and "token" not in event.details.lower()

    # The former First Admin keeps Admin access but loses First-Admin-only powers.
    old_first = login(emails["first"])
    assert client.request("DELETE", "/api/admin/activity/purge", headers=old_first, json={
        "before": "2000-01-01T00:00:00Z", "reason": "Former First Admin check.", "confirm": True,
    }).status_code == 403


def test_expired_transfer_cannot_be_accepted_and_is_marked_expired(transfer_accounts):
    emails = transfer_accounts["emails"]
    first = login(emails["first"])
    start(first, emails["recipient"])
    with SessionLocal() as db:
        row = db.query(FirstAdminTransfer).filter_by(status="pending").one()
        row.expires_at = (utc_now() - timedelta(minutes=1)).isoformat()
        db.commit()
    recipient = login(emails["recipient"])
    assert client.post("/api/admin/first-admin-transfer/accept", headers=recipient).status_code == 409
    with SessionLocal() as db:
        assert db.query(FirstAdminTransfer).one().status == "expired"
        assert db.query(UserAccount).filter_by(is_first_admin=True).one().id == transfer_accounts["ids"]["first"]


def test_transfer_is_refused_if_the_recipient_became_ineligible_before_acceptance(transfer_accounts):
    emails, ids = transfer_accounts["emails"], transfer_accounts["ids"]
    first = login(emails["first"])
    recipient = login(emails["recipient"])
    start(first, emails["recipient"])
    with SessionLocal() as db:
        db.get(UserAccount, ids["recipient"]).status = "suspended"
        db.commit()
    assert client.post("/api/admin/first-admin-transfer/accept", headers=recipient).status_code in (401, 403, 409)
    with SessionLocal() as db:
        assert db.query(UserAccount).filter_by(is_first_admin=True).one().id == ids["first"]
