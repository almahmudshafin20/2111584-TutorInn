from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_alembic_configuration_resolves_paths_from_config_location() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))

    assert Path(config.get_main_option("script_location")).resolve() == (
        BACKEND_DIR / "alembic"
    ).resolve()
    assert Path(config.get_main_option("prepend_sys_path")).resolve() == BACKEND_DIR.resolve()


def test_alembic_has_one_existing_schema_baseline_head() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["20261116_0006"]
    baseline = scripts.get_revision("20261116_0001")
    personal_tasks = scripts.get_revision("20261116_0002")
    group_learning = scripts.get_revision("20261116_0003")
    tutor_verification = scripts.get_revision("20261116_0004")
    request_timestamps = scripts.get_revision("20261116_0005")
    moderation_subjects = scripts.get_revision("20261116_0006")
    assert personal_tasks is not None
    assert personal_tasks.down_revision == "20261116_0001"
    assert baseline is not None
    assert baseline.down_revision is None
    assert group_learning is not None
    assert group_learning.down_revision == "20261116_0002"
    assert tutor_verification is not None
    assert tutor_verification.down_revision == "20261116_0003"
    assert request_timestamps is not None
    assert request_timestamps.down_revision == "20261116_0004"
    assert moderation_subjects is not None
    assert moderation_subjects.down_revision == "20261116_0005"


def test_database_url_defaults_to_local_sqlite_when_no_postgres_url_is_set(monkeypatch) -> None:
    from app.database import database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    resolved = database_url()
    assert resolved.startswith("sqlite:///")
    assert resolved.endswith("/backend/tutorinn.db")


def test_database_url_prefers_explicit_url_and_normalizes_supabase_pooler_parameters(monkeypatch) -> None:
    from app.database import database_url

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://tutorinn:local-test-password@db.example.test:6543/postgres"
        "?sslmode=require&pgbouncer=true&supa=project-ref",
    )
    monkeypatch.setenv(
        "POSTGRES_URL",
        "postgresql://ignored:ignored@other.example.test:5432/ignored",
    )

    resolved = database_url()
    assert resolved.startswith(
        "postgresql+psycopg://tutorinn:local-test-password@db.example.test:6543/postgres"
    )
    assert "sslmode=require" in resolved
    assert "pgbouncer" not in resolved
    assert "supa=" not in resolved
    assert "other.example.test" not in resolved


def test_database_url_accepts_vercel_postgres_url_fallback(monkeypatch) -> None:
    from app.database import database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "POSTGRES_URL",
        "postgresql://tutorinn:local-test-password@db.example.test:6543/postgres?sslmode=require",
    )

    resolved = database_url()
    assert resolved.startswith("postgresql+psycopg://")
    assert "db.example.test:6543/postgres" in resolved
