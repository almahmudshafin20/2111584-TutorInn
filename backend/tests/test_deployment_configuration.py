"""Deployment configuration: hosted deployments must use a persistent database, and the API docs are served."""
import os, sys
from pathlib import Path
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('deployment-config-test.db')}")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-only-password-pepper-with-at-least-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from app.database import database_url

DATABASE_VARIABLES = ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING")


def clear_database_variables(monkeypatch):
    for name in DATABASE_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def test_vercel_deployment_refuses_the_ephemeral_sqlite_fallback(monkeypatch):
    clear_database_variables(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(RuntimeError, match="persistent"):
        database_url()


def test_vercel_deployment_uses_a_configured_postgres_url(monkeypatch):
    clear_database_variables(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@db.example.test:5432/tutorinn")
    assert database_url().startswith("postgresql")


def test_local_runs_keep_the_sqlite_fallback(monkeypatch):
    clear_database_variables(monkeypatch)
    monkeypatch.delenv("VERCEL", raising=False)
    assert database_url().startswith("sqlite:///")
