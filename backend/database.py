import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

_UNSUPPORTED_QUERY_KEYS = {"supa", "pgbouncer"}


def database_url() -> str:
    """Use PostgreSQL/Supabase in deployment and SQLite for local development."""
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        parts = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parts.query) if key not in _UNSUPPORTED_QUERY_KEYS]
        return urlunsplit(parts._replace(query=urlencode(query)))
    local_db = Path(__file__).resolve().parent / "tutorinn.db"
    return f"sqlite:///{local_db}"


DATABASE_URL = database_url()
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"prepare_threshold": None},
        poolclass=NullPool,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    """Create mapped tables and safely add response columns to older databases."""
    # Import models so all mapped tables are registered on Base.metadata.
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        existing_columns = {column["name"] for column in inspect(engine).get_columns("learning_posts")}
        if "student_response" not in existing_columns:
            connection.execute(text(
                "ALTER TABLE learning_posts ADD COLUMN student_response VARCHAR(20) NOT NULL DEFAULT 'No response'"
            ))
        if "tutor_response" not in existing_columns:
            connection.execute(text(
                "ALTER TABLE learning_posts ADD COLUMN tutor_response VARCHAR(20) NOT NULL DEFAULT 'No response'"
            ))
