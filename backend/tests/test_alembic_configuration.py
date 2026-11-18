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

    assert scripts.get_heads() == ["20261118_0009"]
    baseline = scripts.get_revision("20261116_0001")
    personal_tasks = scripts.get_revision("20261116_0002")
    group_learning = scripts.get_revision("20261116_0003")
    tutor_verification = scripts.get_revision("20261116_0004")
    request_timestamps = scripts.get_revision("20261116_0005")
    moderation_subjects = scripts.get_revision("20261116_0006")
    former_user_recovery = scripts.get_revision("20261118_0007")
    account_deletion_rls = scripts.get_revision("20261118_0008")
    first_admin_identity = scripts.get_revision("20261118_0009")
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
    assert former_user_recovery is not None
    assert former_user_recovery.down_revision == "20261116_0006"
    assert account_deletion_rls is not None
    assert first_admin_identity is not None
    assert first_admin_identity.down_revision == "20261118_0008"
    assert account_deletion_rls.down_revision == "20261118_0007"


def test_database_url_defaults_to_local_sqlite_when_no_postgres_url_is_set(monkeypatch) -> None:
    from app.database import database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PRISMA_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL_NON_POOLING", raising=False)

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


def test_database_url_accepts_vercel_postgres_prisma_url_fallback(monkeypatch) -> None:
    from app.database import database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL_NON_POOLING", raising=False)
    monkeypatch.setenv(
        "POSTGRES_PRISMA_URL",
        "postgres://tutorinn:local-test-password@db.example.test:6543/postgres"
        "?sslmode=require&pgbouncer=true&supa=project-ref",
    )

    resolved = database_url()
    assert resolved.startswith(
        "postgresql+psycopg://tutorinn:local-test-password@db.example.test:6543/postgres"
    )
    assert "sslmode=require" in resolved
    assert "pgbouncer" not in resolved
    assert "supa=" not in resolved


def test_database_url_accepts_vercel_non_pooling_url_as_last_fallback(monkeypatch) -> None:
    from app.database import database_url

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PRISMA_URL", raising=False)
    monkeypatch.setenv(
        "POSTGRES_URL_NON_POOLING",
        "postgresql://tutorinn:local-test-password@db.example.test:5432/postgres?sslmode=require",
    )

    resolved = database_url()
    assert resolved.startswith("postgresql+psycopg://")
    assert "db.example.test:5432/postgres" in resolved


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
        assert "CREATE TABLE account_deletion_requests" in generated_sql
        assert "CREATE TABLE retained_content" in generated_sql
        assert "CREATE TABLE former_user_content_tokens" in generated_sql
        assert "CREATE TABLE former_user_content_removal_requests" in generated_sql



def test_fresh_postgresql_database_applies_all_incremental_alembic_migrations() -> None:
    import pytest
    from sqlalchemy import create_engine, inspect, text

    test_url = os.getenv("TEST_POSTGRES_URL")
    if not test_url:
        pytest.skip("TEST_POSTGRES_URL is only configured in the PostgreSQL CI job")

    engine = create_engine(test_url)
    try:
        # Revision 0001 marks the existing MVP schema; seed the three legacy
        # tables that subsequent revisions extend or reference.
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE user_accounts (id SERIAL PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE tutors (id SERIAL PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE learning_posts (id SERIAL PRIMARY KEY)"))

        environment = os.environ.copy()
        environment["DATABASE_URL"] = test_url
        for key in ("POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING"):
            environment.pop(key, None)

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

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
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
            "account_deletion_requests",
            "retained_content",
            "former_user_content_tokens",
            "former_user_content_removal_requests",
        }.issubset(tables)
        assert "created_at" in {
            column["name"] for column in inspector.get_columns("learning_posts")
        }
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "20261118_0008"
        with engine.connect() as connection:
            protected_tables = connection.execute(text("""
                SELECT relname FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                  AND c.relrowsecurity
                  AND c.relname IN (
                    'account_deletion_requests', 'retained_content',
                    'former_user_content_tokens', 'former_user_content_removal_requests'
                  )
            """)).scalars().all()
            assert set(protected_tables) == {
                "account_deletion_requests", "retained_content",
                "former_user_content_tokens", "former_user_content_removal_requests",
            }
        deletion_columns = {column["name"] for column in inspector.get_columns("account_deletion_requests")}
        assert {"former_user_link_status", "requested_content_action", "final_content_action", "former_user_email"}.issubset(deletion_columns)
        assert "uq_account_deletion_pending" in {index["name"] for index in inspector.get_indexes("account_deletion_requests")}
        assert "uq_former_user_removal_pending" in {index["name"] for index in inspector.get_indexes("former_user_content_removal_requests")}
        for table, column in (
            ("personal_learning_tasks", "owner_account_id"),
            ("learning_groups", "owner_account_id"),
            ("learning_group_members", "student_account_id"),
            ("group_learning_tasks", "created_by_account_id"),
            ("group_task_assignments", "student_account_id"),
        ):
            assert next(item for item in inspector.get_columns(table) if item["name"] == column)["nullable"] is True
            foreign_key = next(item for item in inspector.get_foreign_keys(table) if item["constrained_columns"] == [column])
            assert (foreign_key.get("options") or {}).get("ondelete", "").upper() == "SET NULL"
    finally:
        engine.dispose()


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
    migration_command = [
        sys.executable, "-m", "alembic", "-c",
        str(BACKEND_DIR / "alembic.ini"), "upgrade",
    ]
    subprocess.run(
        migration_command + ["20261116_0006"],
        cwd=BACKEND_DIR.parent, env=environment, check=True,
        capture_output=True, text=True,
    )

    # Seed related learning records before the retention migration rebuilds
    # nullable ownership columns; all rows must survive the SQLite rebuild.
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO user_accounts (id) VALUES (1)")
        connection.execute("INSERT INTO personal_learning_tasks (id, owner_account_id, title, description, completed, created_at, updated_at) VALUES (1, 1, 'Retained task', '', 0, 'now', 'now')")
        connection.execute("INSERT INTO learning_groups (id, owner_account_id, name, description, created_at, updated_at) VALUES (1, 1, 'Retained group', '', 'now', 'now')")
        connection.execute("INSERT INTO learning_group_members (id, group_id, student_account_id, joined_at) VALUES (1, 1, 1, 'now')")
        connection.execute("INSERT INTO group_learning_tasks (id, group_id, created_by_account_id, title, description, created_at, updated_at) VALUES (1, 1, 1, 'Retained group task', '', 'now', 'now')")
        connection.execute("INSERT INTO group_task_assignments (id, task_id, student_account_id, completed, assigned_at) VALUES (1, 1, 1, 0, 'now')")
        connection.commit()

    subprocess.run(
        migration_command + ["head"],
        cwd=BACKEND_DIR.parent, env=environment, check=True,
        capture_output=True, text=True,
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
            "account_deletion_requests",
            "retained_content",
            "former_user_content_tokens",
            "former_user_content_removal_requests",
        }.issubset(tables)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(learning_posts)")
        }
        assert "created_at" in columns
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        assert revision == ("20261118_0008",)
        deletion_columns = {row[1] for row in connection.execute("PRAGMA table_info(account_deletion_requests)")}
        assert {"former_user_link_status", "requested_content_action", "final_content_action", "former_user_email"}.issubset(deletion_columns)
        assert "uq_account_deletion_pending" in {row[1] for row in connection.execute("PRAGMA index_list(account_deletion_requests)")}
        assert "uq_former_user_removal_pending" in {row[1] for row in connection.execute("PRAGMA index_list(former_user_content_removal_requests)")}
        for table, column in (
            ("personal_learning_tasks", "owner_account_id"),
            ("learning_groups", "owner_account_id"),
            ("learning_group_members", "student_account_id"),
            ("group_learning_tasks", "created_by_account_id"),
            ("group_task_assignments", "student_account_id"),
        ):
            table_columns = {row[1]: row for row in connection.execute(f"PRAGMA table_info({table})")}
            assert table_columns[column][3] == 0, f"{table}.{column} must allow retained content ownership to be detached"
            foreign_key = next(row for row in connection.execute(f"PRAGMA foreign_key_list({table})") if row[3] == column)
            assert foreign_key[6].upper() == "SET NULL"
        assert connection.execute("SELECT COUNT(*) FROM personal_learning_tasks").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM learning_groups").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM learning_group_members").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM group_learning_tasks").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM group_task_assignments").fetchone()[0] == 1



def test_supabase_private_tables_keep_rls_enabled_and_browser_grants_revoked() -> None:
    migration_dir = BACKEND_DIR.parent / "supabase" / "migrations"
    required_statements = {
        "20261114133407_secure_public_schema_rls_and_api_privileges.sql": [
            "ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.tutors ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.learning_posts ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.interest_responses ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.user_accounts ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.refresh_sessions ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.security_events ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC, anon, authenticated;",
            "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, anon, authenticated;",
            "REVOKE USAGE ON SCHEMA public FROM PUBLIC, anon, authenticated;",
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public",
        ],
        "20261117144551_enable_rls_on_private_learning_tables.sql": [
            "ALTER TABLE public.personal_learning_tasks ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.learning_groups ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.learning_group_members ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.group_learning_tasks ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.group_task_assignments ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON TABLE",
            "REVOKE ALL PRIVILEGES ON SEQUENCE",
        ],
        "20261114134652_legacy_profile_claim_tokens.sql": [
            "ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.tutors ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON public.students, public.tutors FROM PUBLIC, anon, authenticated;",
        ],
        "20261116170000_secure_tutor_verification_admin_table.sql": [
            "ALTER TABLE public.tutor_verifications ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL ON TABLE public.tutor_verifications FROM anon, authenticated, PUBLIC;",
        ],
        "20261116190000_reports_and_subject_catalogue.sql": [
            "ALTER TABLE public.managed_subjects ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.content_reports ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON TABLE public.managed_subjects, public.content_reports",
        ],
        "20261117160000_admin_approved_account_deletion.sql": [
            "ALTER TABLE public.account_deletion_requests ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON TABLE public.account_deletion_requests FROM PUBLIC, anon, authenticated;",
            "GRANT ALL PRIVILEGES ON TABLE public.account_deletion_requests TO service_role;",
        ],
        "20261118064459_secure_account_deletion_tables_rls.sql": [
            "ALTER TABLE public.account_deletion_requests ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.retained_content ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.former_user_content_tokens ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.former_user_content_removal_requests ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON TABLE",
            "FROM PUBLIC;",
        ],
        "20261118010000_expanded_account_deletion_retention.sql": [
            "ALTER TABLE public.retained_content ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.former_user_content_tokens ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.former_user_content_removal_requests ENABLE ROW LEVEL SECURITY;",
            "REVOKE ALL PRIVILEGES ON TABLE public.retained_content, public.former_user_content_tokens, public.former_user_content_removal_requests FROM PUBLIC, anon, authenticated;",
            "GRANT ALL PRIVILEGES ON TABLE public.retained_content, public.former_user_content_tokens, public.former_user_content_removal_requests TO service_role;",
        ],
    }
    for filename, statements in required_statements.items():
        sql = (migration_dir / filename).read_text(encoding="utf-8")
        for statement in statements:
            assert statement in sql, f"{filename} is missing: {statement}"
    for migration in migration_dir.glob("*.sql"):
        sql = migration.read_text(encoding="utf-8")
        assert "CREATE POLICY" not in sql.upper(), (
            f"{migration.name} must not expose private records through browser Data API policies"
        )
