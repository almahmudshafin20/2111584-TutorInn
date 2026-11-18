import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import verify_password
from app.database import Base
from app.models import UserAccount
from scripts.create_first_admin import create_first_admin


@pytest.fixture
def isolated_session_factory(monkeypatch):
    monkeypatch.setenv(
        "PASSWORD_PEPPER",
        "test-only-password-pepper-with-at-least-32-characters",
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


def test_cli_creates_a_peppered_first_admin_with_normalized_email(isolated_session_factory):
    password = "a-secure-admin-password-123"
    account_id = create_first_admin(
        "  FIRST.ADMIN@EXAMPLE.COM ",
        password,
        session_factory=isolated_session_factory,
    )

    with isolated_session_factory() as db:
        account = db.get(UserAccount, account_id)
        assert account is not None
        assert account.email == "first.admin@example.com"
        assert account.role == "admin"
        assert account.is_first_admin is True
        assert account.status == "active"
        assert account.created_at
        assert account.updated_at
        assert account.password_hash != password
        assert verify_password(password, account.password_hash)


def test_cli_refuses_when_any_admin_already_exists(isolated_session_factory):
    with isolated_session_factory() as db:
        db.add(UserAccount(
            email="existing.admin@example.com",
            password_hash="not-a-real-hash",
            role="admin",
            is_first_admin=True,
            status="active",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        ))
        db.commit()

    with pytest.raises(RuntimeError, match="Admin account already exists"):
        create_first_admin(
            "new.admin@example.com",
            "a-secure-admin-password-123",
            session_factory=isolated_session_factory,
        )


def test_cli_refuses_an_email_already_used_by_an_account(isolated_session_factory):
    with isolated_session_factory() as db:
        db.add(UserAccount(
            email="existing.user@example.com",
            password_hash="not-a-real-hash",
            role="student",
            is_first_admin=False,
            status="active",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        ))
        db.commit()

    with pytest.raises(RuntimeError, match="email address is already in use"):
        create_first_admin(
            "existing.user@example.com",
            "a-secure-admin-password-123",
            session_factory=isolated_session_factory,
        )


@pytest.mark.parametrize("password", ["short-password", "x" * 129])
def test_cli_applies_registration_password_length_rules(
    isolated_session_factory, password
):
    with pytest.raises(ValueError, match="12 and 128 characters"):
        create_first_admin(
            "new.admin@example.com",
            password,
            session_factory=isolated_session_factory,
        )
