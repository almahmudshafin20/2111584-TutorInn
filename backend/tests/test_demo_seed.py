"""Demo seed safety: refuses production, requires a supplied password, never creates a First Admin."""
import os
import sys
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('demo-seed-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from sqlalchemy import select
from scripts import seed_demo_accounts as seed_module
from scripts.seed_demo_accounts import SeedRefused, assert_not_production, demo_password, seed
from app.database import SessionLocal
from app.models import LearningGroup, LearningGroupMember, UserAccount

GOOD_PASSWORD = "demo-only-password-123"


def test_refuses_when_vercel_environment_is_production():
    with pytest.raises(SeedRefused):
        assert_not_production("sqlite:///x.db", {"VERCEL_ENV": "production"})


def test_refuses_when_database_points_at_the_production_supabase_project():
    url = "postgresql+psycopg://user:pw@aws-0-ap-south-1.pooler.supabase.com/postgres?project=agioyjludjokntvlyjqz"
    with pytest.raises(SeedRefused):
        assert_not_production(url, {})


def test_allows_preview_and_local_databases():
    assert_not_production("sqlite:///demo.db", {"VERCEL_ENV": "preview"})


def test_requires_a_demo_password_of_at_least_twelve_characters():
    with pytest.raises(SeedRefused):
        demo_password({})
    with pytest.raises(SeedRefused):
        demo_password({"DEMO_PASSWORD": "short"})
    assert demo_password({"DEMO_PASSWORD": GOOD_PASSWORD}) == GOOD_PASSWORD


def test_seed_creates_demo_accounts_group_and_is_idempotent_without_first_admin():
    seed(environ={"DEMO_PASSWORD": GOOD_PASSWORD})
    again = seed(environ={"DEMO_PASSWORD": GOOD_PASSWORD})
    assert again == {"admin": 0, "student": 0, "tutor": 0, "group": 0, "members": 0}

    with SessionLocal() as db:
        admins = db.scalars(select(UserAccount).where(UserAccount.email.like("demo-admin-%@example.com"))).all()
        assert len(admins) == 2
        assert all(row.role == "admin" and row.is_first_admin is False for row in admins)
        first_admins = db.scalars(select(UserAccount).where(UserAccount.is_first_admin.is_(True))).all()
        assert not any(row.email.startswith("demo-") for row in first_admins)
        group = db.scalar(select(LearningGroup).where(LearningGroup.name == "Demo Shared Group"))
        assert group is not None
        members = db.scalars(select(LearningGroupMember).where(LearningGroupMember.group_id == group.id)).all()
        assert len(members) == 2
        assert sorted((m.can_create_tasks, m.can_edit_tasks) for m in members) == [(False, False), (True, False)]
