"""Create the one-time First Admin account directly in the configured database.

Run from the backend directory with DATABASE_URL and PASSWORD_PEPPER set.
The password is prompted interactively and is never accepted as an argument.
"""
from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass
from typing import Callable

from pydantic import ValidationError
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.auth import hash_password, timestamp
from app.database import DATABASE_URL, SessionLocal
from app.models import Student, Tutor, UserAccount
from app.schemas import StudentRegistrationInput


def _validated_credentials(email: str, password: str) -> tuple[str, str]:
    """Reuse the Student registration schema's email and password validation."""
    try:
        registration = StudentRegistrationInput.model_validate({
            "full_name": "First Admin",
            "email": email.strip().lower(),
            "password": password,
            "education_level": "Administration",
            "subjects": ["Administration"],
        })
    except ValidationError as exc:
        password_error = any(
            error.get("loc") == ("password",) for error in exc.errors()
        )
        if password_error:
            raise ValueError(
                "Password must be between 12 and 128 characters, matching registration."
            ) from None
        raise ValueError("Enter a valid email address.") from None
    return registration.email, registration.password


def create_first_admin(
    email: str,
    password: str,
    session_factory: Callable[[], Session] = SessionLocal,
) -> int:
    """Create the First Admin once; return its account ID."""
    normalized_email, validated_password = _validated_credentials(email, password)

    with session_factory() as db:
        bind = db.get_bind()
        if not inspect(bind).has_table("user_accounts"):
            raise RuntimeError(
                "The user_accounts table is missing. Apply the required database migrations first."
            )
        columns = {column["name"] for column in inspect(bind).get_columns("user_accounts")}
        if "is_first_admin" not in columns:
            raise RuntimeError(
                "The is_first_admin migration is not applied. Apply migration 0009 before creating the First Admin."
            )

        with db.begin():
            # Serialize simultaneous invocations on PostgreSQL so only one can
            # pass the first-admin check at a time.
            if bind.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(741902611)"))

            existing_admin = db.scalar(
                select(UserAccount.id).where(UserAccount.role == "admin").limit(1)
            )
            if existing_admin is not None:
                raise RuntimeError(
                    "An Admin account already exists. First Admin creation is disabled."
                )

            email_in_use = (
                db.scalar(select(UserAccount.id).where(UserAccount.email == normalized_email).limit(1))
                or db.scalar(select(Student.id).where(Student.email == normalized_email).limit(1))
                or db.scalar(select(Tutor.id).where(Tutor.email == normalized_email).limit(1))
            )
            if email_in_use is not None:
                raise RuntimeError(
                    "That email address is already in use. Choose an unused email address."
                )

            account = UserAccount(
                email=normalized_email,
                password_hash=hash_password(validated_password),
                role="admin",
                is_first_admin=True,
                status="active",
                created_at=timestamp(),
                updated_at=timestamp(),
            )
            db.add(account)
            db.flush()
            account_id = account.id

    return account_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create TutorInn's one-time First Admin directly in PostgreSQL."
    )
    parser.add_argument("email", help="Email address for the First Admin account")
    args = parser.parse_args(argv)

    if not os.getenv("DATABASE_URL"):
        parser.error("Set DATABASE_URL to the Supabase PostgreSQL connection string first.")
    if not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
        parser.error("Refusing to run against a non-PostgreSQL database.")
    if not os.getenv("PASSWORD_PEPPER"):
        parser.error("Set PASSWORD_PEPPER to the exact value used by Vercel Production.")

    password = getpass("New First Admin password: ")
    confirmation = getpass("Confirm First Admin password: ")
    if password != confirmation:
        print("Passwords do not match. No account was created.", file=sys.stderr)
        return 1

    try:
        account_id = create_first_admin(args.email, password)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # Do not print exception details that might contain connection strings.
        print(
            f"First Admin creation failed ({type(exc).__name__}). "
            "Check the database connection and migration status.",
            file=sys.stderr,
        )
        return 1

    print(f"First Admin account created successfully (account ID: {account_id}).")
    print("Keep PASSWORD_PEPPER unchanged; it is required for future password verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
