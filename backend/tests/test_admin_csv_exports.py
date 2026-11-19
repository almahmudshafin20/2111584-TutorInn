"""Admin CSV exports: active filters are respected, empty results are safe, and formulas are neutralized."""
import os, secrets, sys, uuid
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('admin-csv-export-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import pytest
from app import main
from app.auth import create_access_token, hash_password, timestamp, token_hash, utc_now
from app.database import SessionLocal, initialize_database
from app.models import RefreshSession, SecurityEvent, UserAccount
from app.routers.admin import _csv_cell

initialize_database()
client = TestClient(main.app)
PASSWORD = "correct-horse-battery-staple-42"


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_events():
    with SessionLocal() as db:
        db.query(SecurityEvent).filter(SecurityEvent.event_type.like("auth_attempt_%")).delete(synchronize_session=False)
        db.commit()
    yield


def admin_headers() -> dict:
    email = f"csv-admin-{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        account = UserAccount(email=email, password_hash=hash_password(PASSWORD), role="admin",
                              is_first_admin=False, status="active", created_at=timestamp(), updated_at=timestamp())
        db.add(account)
        db.flush()
        now = timestamp()
        session = RefreshSession(
            account_id=account.id, token_hash=token_hash(secrets.token_urlsafe(48)),
            family_id=str(uuid.uuid4()), csrf_token_hash=token_hash(secrets.token_urlsafe(32)),
            created_at=now, last_used_at=now, expires_at=(utc_now() + timedelta(days=1)).isoformat(),
            revoked_at=None, replaced_by=None, user_agent="csv-test", ip_address="127.0.0.1",
        )
        db.add(session)
        db.flush()
        access, _ = create_access_token(account, session.id)
        db.commit()
    return {"Authorization": f"Bearer {access}"}


def register_student(email: str) -> None:
    response = client.post("/api/auth/register/student", json={
        "full_name": "Export Student", "email": email, "password": PASSWORD,
        "education_level": "University", "subjects": ["Mathematics"],
    })
    assert response.status_code == 201, response.text


def test_user_export_contains_only_rows_matching_the_active_search_filter():
    token = uuid.uuid4().hex[:10]
    match = f"exportmatch{token}@example.com"
    other = f"exportother{token}@example.com"
    register_student(match)
    register_student(other)
    admin = admin_headers()
    exported = client.get(f"/api/admin/export/users?q=exportmatch{token}", headers=admin)
    assert exported.status_code == 200, exported.text
    assert match in exported.text
    assert other not in exported.text


def test_user_export_with_no_matches_returns_only_the_header_row():
    admin = admin_headers()
    exported = client.get(f"/api/admin/export/users?q=no-such-account-{uuid.uuid4().hex}", headers=admin)
    assert exported.status_code == 200, exported.text
    data_lines = [line for line in exported.text.splitlines() if line.strip()]
    assert len(data_lines) <= 1


def test_spreadsheet_formulas_are_neutralized_in_exported_cells():
    assert _csv_cell("=HYPERLINK(\"http://evil\")") == "'=HYPERLINK(\"http://evil\")"
    assert _csv_cell("+1+1") == "'+1+1"
    assert _csv_cell("-2") == "'-2"
    assert _csv_cell("@SUM(A1)") == "'@SUM(A1)"
    assert _csv_cell("plain text") == "plain text"


def test_export_rejects_unknown_kinds():
    response = client.get("/api/admin/export/not-a-real-kind", headers=admin_headers())
    assert response.status_code in (404, 422)
