import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

_UNSUPPORTED_QUERY_KEYS = {"supa", "pgbouncer"}

def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        parts = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parts.query) if key not in _UNSUPPORTED_QUERY_KEYS]
        return urlunsplit(parts._replace(query=urlencode(query)))
    return f"sqlite:///{Path(__file__).resolve().parent / 'tutorinn.db'}"

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

def initialize_database() -> None:
    try:
        from backend import models  # noqa: F401
    except ModuleNotFoundError:
        import models  # type: ignore[no-redef] # noqa: F401
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        migrations = {
            "students": {"subjects_json": "TEXT", "phone_number": "VARCHAR(32) NOT NULL DEFAULT ''"},
            "tutors": {"subjects_json": "TEXT", "phone_number": "VARCHAR(32) NOT NULL DEFAULT ''"},
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
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"))
