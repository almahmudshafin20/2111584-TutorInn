"""Create demo accounts and one shared group for local or preview testing.

Safety rules:
- Refuses to run against production (VERCEL_ENV/ENVIRONMENT=production or the
  production Supabase project reference in DATABASE_URL).
- Requires DEMO_PASSWORD from the environment (at least 12 characters). No default
  password is ever written into the repository.
- Never creates or modifies a First Admin. Demo Admin accounts use the normal
  admin role only.
- Idempotent: existing demo emails are skipped, not overwritten.

Run from the backend directory:
    DATABASE_URL=sqlite:///./demo.db PASSWORD_PEPPER=... DEMO_PASSWORD=... \
        python -m scripts.seed_demo_accounts
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import select

PRODUCTION_PROJECT_REF = "agioyjludjokntvlyjqz"
DEMO_DOMAIN = "example.com"


class SeedRefused(RuntimeError):
    pass


def assert_not_production(database_url: str, environ: dict[str, str], *, allow_shared_database: bool = False) -> None:
    """Refuse production runtimes always; refuse the production database unless explicitly allowed."""
    if environ.get("VERCEL_ENV", "").lower() == "production" or environ.get("ENVIRONMENT", "").lower() == "production":
        raise SeedRefused("Refusing to seed: this environment is production.")
    if PRODUCTION_PROJECT_REF in database_url and not allow_shared_database:
        raise SeedRefused("Refusing to seed: DATABASE_URL points at the production Supabase project. "
                          "Pass --allow-shared-database only for the approved demo accounts on the shared database.")


def demo_password(environ: dict[str, str]) -> str:
    password = environ.get("DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SeedRefused("Set DEMO_PASSWORD to a demo-only value of at least 12 characters.")
    return password


def seed(environ: dict[str, str] | None = None, *, allow_shared_database: bool = False) -> dict[str, int]:
    environ = dict(os.environ if environ is None else environ)
    from app.database import DATABASE_URL, SessionLocal, initialize_database
    from app.auth import hash_password, timestamp
    from app.models import LearningGroup, LearningGroupMember, Student, Tutor, UserAccount

    assert_not_production(DATABASE_URL, environ, allow_shared_database=allow_shared_database)
    password = demo_password(environ)
    initialize_database()
    hashed = hash_password(password)
    created = {"admin": 0, "student": 0, "tutor": 0, "group": 0, "members": 0}
    now = timestamp()

    with SessionLocal() as db:
        def account(email: str, role: str) -> UserAccount:
            existing = db.scalar(select(UserAccount).where(UserAccount.email == email))
            if existing is not None:
                return existing
            row = UserAccount(email=email, password_hash=hashed, role=role, is_first_admin=False,
                              status="active", created_at=now, updated_at=now)
            db.add(row)
            db.flush()
            created[role] += 1
            return row

        admins = [account(f"demo-admin-{n}@{DEMO_DOMAIN}", "admin") for n in (1, 2)]
        students = [account(f"demo-student-{n}@{DEMO_DOMAIN}", "student") for n in (1, 2)]
        tutor = account(f"demo-tutor-1@{DEMO_DOMAIN}", "tutor")

        for index, row in enumerate(students, start=1):
            if db.scalar(select(Student).where(Student.account_id == row.id)) is None and db.scalar(select(Student).where(Student.email == row.email)) is None:
                db.add(Student(account_id=row.id, full_name=f"Demo Student {index}", email=row.email,
                               education_level="University", preferred_subjects="Mathematics"))
        if db.scalar(select(Tutor).where(Tutor.account_id == tutor.id)) is None and db.scalar(select(Tutor).where(Tutor.email == tutor.email)) is None:
            db.add(Tutor(account_id=tutor.id, full_name="Demo Tutor 1", email=tutor.email, subject="Physics",
                         teaching_level="HSC", experience_years=3, hourly_rate=500.0, bio="Demo tutor account."))

        group = db.scalar(select(LearningGroup).where(LearningGroup.name == "Demo Shared Group", LearningGroup.owner_account_id == tutor.id))
        if group is None:
            group = LearningGroup(owner_account_id=tutor.id, name="Demo Shared Group",
                                  description="Demo group with mixed member permissions.", created_at=now, updated_at=now)
            db.add(group)
            db.flush()
            created["group"] += 1
            permissions = [
                (students[0].id, True, False, False),   # can create tasks only
                (students[1].id, False, False, False),  # plain member
            ]
            for student_id, create, edit, assign in permissions:
                db.add(LearningGroupMember(group_id=group.id, student_account_id=student_id, can_create_tasks=create,
                                           can_edit_tasks=edit, can_assign_tasks=assign, joined_at=now))
                created["members"] += 1
        db.commit()
    return created


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create the demo accounts and shared group.")
    parser.add_argument("--allow-shared-database", action="store_true",
                        help="Permit seeding the Supabase project used by the live site (approved demo accounts only).")
    cli = parser.parse_args()
    try:
        summary = seed(allow_shared_database=cli.allow_shared_database)
    except SeedRefused as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print(f"Demo seed complete: {summary}")
