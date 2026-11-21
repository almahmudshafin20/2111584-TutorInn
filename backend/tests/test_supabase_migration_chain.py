"""Replay the Supabase migration chain on a clean PostgreSQL database and verify the resulting schema.

Runs only in the dedicated migration-chain CI job (TEST_MIGRATION_POSTGRES_URL). The database must be
a throwaway database whose name contains "migration_chain"; the test refuses any other name.
"""
import os
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
MIGRATIONS = BACKEND.parent / "supabase" / "migrations"
URL = os.getenv("TEST_MIGRATION_POSTGRES_URL")
SUPABASE_ROLES = ("anon", "authenticated", "service_role", "postgres")

pytestmark = pytest.mark.skipif(
    not URL, reason="TEST_MIGRATION_POSTGRES_URL is only configured in the migration-chain CI job",
)


def _psycopg_url() -> str:
    return URL.replace("postgresql+psycopg://", "postgresql://", 1)


def _connect():
    import psycopg
    return psycopg.connect(_psycopg_url(), autocommit=True)


def test_supabase_migration_chain_replays_on_a_clean_database():
    database_name = URL.rsplit("/", 1)[-1]
    assert "migration_chain" in database_name, "refusing to run against a database not dedicated to the migration chain"
    files = sorted(MIGRATIONS.glob("*.sql"))
    assert files, "no Supabase migrations found"

    # Supabase provides these roles; a plain PostgreSQL service does not.
    with _connect() as conn:
        for role in SUPABASE_ROLES:
            conn.execute(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') "
                f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$;"
            )

    # The chain is self-contained: the profile tables and the untracked MVP tables are created by
    # the first migrations (see 20261019164750 and 20261019164800), not by SQLAlchemy create_all.
    for path in files:
        with _connect() as conn:
            try:
                conn.execute(path.read_text(encoding="utf-8"))
            except Exception as error:  # report the failing file by name
                pytest.fail(f"migration {path.name} failed on a clean replay: {error}")

    with _connect() as conn:
        def scalar(sql: str):
            return conn.execute(sql).fetchone()[0]

        assert scalar(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'user_accounts' AND column_name = 'is_first_admin'"
        ) == 1
        assert scalar(
            "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' "
            "AND indexname = 'uq_first_admin_transfers_one_pending'"
        ) == 1
        assert scalar(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity"
        ) == 0, "a public table has row level security disabled"
        assert scalar(
            "SELECT count(*) FROM information_schema.role_table_grants "
            "WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')"
        ) == 0, "anon or authenticated still has direct table privileges"
