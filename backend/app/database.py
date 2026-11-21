import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

_UNSUPPORTED_QUERY_KEYS = {"supa", "pgbouncer"}


def database_url() -> str:
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_PRISMA_URL")
        or os.getenv("POSTGRES_URL_NON_POOLING")
    )
    if not url:
        if os.getenv("VERCEL"):
            # SQLite files inside a Vercel function are ephemeral, so deployed data would be lost.
            raise RuntimeError("Set DATABASE_URL (or a POSTGRES_*_URL) on Vercel; SQLite is not persistent there.")
        return f"sqlite:///{Path(__file__).resolve().parent.parent / 'tutorinn.db'}"

    # Keep non-PostgreSQL URLs (especially explicit SQLite URLs) intact.
    # urlunsplit() can collapse sqlite:/// paths because SQLite has no netloc.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    elif not url.startswith("postgresql+psycopg://"):
        return url

    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key not in _UNSUPPORTED_QUERY_KEYS]
    return urlunsplit(parts._replace(query=urlencode(query)))


DATABASE_URL = database_url()
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, connect_args={"prepare_threshold": None}, poolclass=NullPool, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _validate_postgres_schema() -> None:
    """Fail closed when a PostgreSQL schema has not been migrated.

    PostgreSQL schema changes are managed by reviewed Alembic/Supabase
    migrations. Runtime startup must never create tables or add columns,
    because doing so can bypass the RLS and privilege hardening in those
    migrations.
    """
    from . import models  # noqa: F401 - register mapped tables on Base.metadata

    existing = set(inspect(engine).get_table_names(schema="public"))
    missing = sorted(set(Base.metadata.tables) - existing)
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            "The PostgreSQL database is missing required TutorInn tables: "
            f"{names}. Apply the reviewed Alembic and Supabase SQL migrations "
            "before starting the API."
        )


def initialize_database() -> None:
    # Import the app package from the backend service root so all runtime
    # entry points (FastAPI, tests, and Alembic) register the same metadata.
    from . import models  # noqa: F401

    if engine.dialect.name == "postgresql":
        _validate_postgres_schema()
        return

    # SQLite is the local-development/test database. Keep its lightweight
    # metadata initialization and legacy-column compatibility behavior.
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        migrations = {
            "students": {
                "subjects_json": "TEXT",
                "phone_number": "VARCHAR(32) NOT NULL DEFAULT ''",
                "account_id": "INTEGER REFERENCES user_accounts(id)",
            },
            "tutors": {
                "subjects_json": "TEXT",
                "phone_number": "VARCHAR(32) NOT NULL DEFAULT ''",
                "account_id": "INTEGER REFERENCES user_accounts(id)",
                "availability": "VARCHAR(255) NOT NULL DEFAULT ''",
            },
            "learning_posts": {
                "author_profile_id": "INTEGER",
                "author_profile_type": "VARCHAR(12)",
                "subjects_json": "TEXT",
                "student_response": "VARCHAR(20) NOT NULL DEFAULT 'No response'",
                "tutor_response": "VARCHAR(20) NOT NULL DEFAULT 'No response'",
            },
        }
        for table_name, columns in migrations.items():
            existing = {column["name"] for column in inspect(engine).get_columns(table_name)}
            for column_name, sql_type in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")
                    )
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_students_account_id "
            "ON students(account_id) WHERE account_id IS NOT NULL"
        ))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_tutors_account_id "
            "ON tutors(account_id) WHERE account_id IS NOT NULL"
        ))
