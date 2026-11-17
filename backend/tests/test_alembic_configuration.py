import os
import subprocess
import sys
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


def test_database_engine_initializes_with_sqlite_when_database_urls_are_unset() -> None:
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)
    environment.pop("POSTGRES_URL", None)

    subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.database import engine; assert engine.dialect.name == 'sqlite'",
        ],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_alembic_migrations_render_for_sqlite_and_postgresql_without_connecting() -> None:
    for database_url in (
        "sqlite:///./migration-smoke-test.db",
        "postgresql+psycopg://migration_user:migration_password@localhost:5432/tutorinn",
    ):
        environment = os.environ.copy()
        environment["DATABASE_URL"] = database_url
        environment.pop("POSTGRES_URL", None)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(BACKEND_DIR / "alembic.ini"),
                "upgrade",
                "head",
                "--sql",
            ],
            cwd=BACKEND_DIR.parent,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Alembic SQL generation failed for {database_url}: {result.stderr}"
        generated_sql = result.stdout
        assert "CREATE TABLE personal_learning_tasks" in generated_sql
        assert "CREATE TABLE group_learning_tasks" in generated_sql
        assert "CREATE TABLE content_reports" in generated_sql
        assert "ALTER TABLE learning_posts ADD COLUMN created_at" in generated_sql


def test_database_url_preserves_explicit_sqlite_urls(monkeypatch) -> None:
    from app.database import database_url

    configured = "sqlite:////tmp/tutorinn-local.db"
    monkeypatch.setenv("DATABASE_URL", configured)
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    assert database_url() == configured



def test_local_env_setup_generates_distinct_secrets_and_preserves_existing_values(tmp_path: Path) -> None:
    import importlib.util

    script_path = BACKEND_DIR / "scripts" / "setup_local_env.py"
    spec = importlib.util.spec_from_file_location("tutorinn_local_env_setup", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    (tmp_path / ".env.example").write_text(
        "JWT_SECRET=CHANGE_ME\nPASSWORD_PEPPER=CHANGE_ME\nCRON_SECRET=CHANGE_ME\nDATABASE_URL=\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "JWT_SECRET=keep-this-local-value\nPASSWORD_PEPPER=CHANGE_ME\nDATABASE_URL=sqlite:///existing.db\n",
        encoding="utf-8",
    )

    env_path = module.setup(tmp_path)
    values = dict(
        line.split("=", 1)
        for line in env_path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert values["JWT_SECRET"] == "keep-this-local-value"
    assert len(values["PASSWORD_PEPPER"]) >= 60
    assert len(values["CRON_SECRET"]) >= 60
    assert values["PASSWORD_PEPPER"] != values["CRON_SECRET"]
    assert values["DATABASE_URL"] == "sqlite:///existing.db"
    if os.name != "nt":
        assert env_path.stat().st_mode & 0o777 == 0o600


def test_fresh_sqlite_database_applies_all_incremental_alembic_migrations(tmp_path: Path) -> None:
    import sqlite3

    database_path = tmp_path / "fresh-local.sqlite3"
    # Revision 0001 is an explicit baseline marker for the pre-existing MVP schema.
    # Seed only the legacy tables that later migrations extend or reference.
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE user_accounts (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE tutors (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE learning_posts (id INTEGER PRIMARY KEY)")

    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    environment.pop("POSTGRES_URL", None)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(BACKEND_DIR / "alembic.ini"),
            "upgrade",
            "head",
        ],
        cwd=BACKEND_DIR.parent,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "alembic_version",
            "personal_learning_tasks",
            "learning_groups",
            "learning_group_members",
            "group_learning_tasks",
            "group_task_assignments",
            "tutor_verifications",
            "managed_subjects",
            "content_reports",
        }.issubset(tables)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(learning_posts)")
        }
        assert "created_at" in columns
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        assert revision == ("20261116_0006",)
