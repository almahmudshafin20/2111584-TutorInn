"""Create the demo accounts and sample group for course demonstrations.

Creates two ordinary Admin accounts (never the First Admin), one verified Tutor who owns a sample
group, and two verified Students with different group permissions. Running it again changes nothing
that already exists. Usage (from the backend directory, with DATABASE_URL and PASSWORD_PEPPER set):

    DEMO_PASSWORD='<demo-only password, 12-128 characters>' python scripts/seed_demo_accounts.py --confirm

The password is read from the environment, never from arguments. The script prints the database host
and name before writing, and it writes nothing unless --confirm is given.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth import hash_password, timestamp  # noqa: E402
from app.models import LearningGroup, LearningGroupMember, Student, Tutor, TutorVerification, UserAccount  # noqa: E402

DEMO_ADMINS = [
    ("demo-admin1@example.com", "Demo Admin One"),
    ("demo-admin2@example.com", "Demo Admin Two"),
]
DEMO_TUTOR = ("demo-tutor@example.com", "Demo Tutor")
DEMO_STUDENTS = [
    ("demo-student1@example.com", "Demo Student One"),
    ("demo-student2@example.com", "Demo Student Two"),
]
DEMO_GROUP = "Demo Study Group"


def _account(db: Session, email: str, role: str, password_hash: str, now: str) -> UserAccount | None:
    """Return None when the account already exists, so re-running the seed is harmless."""
    if db.scalar(select(UserAccount.id).where(UserAccount.email == email)) is not None:
        return None
    account = UserAccount(email=email, password_hash=password_hash, role=role, is_first_admin=False,
                          status="active", email_verified_at=now, created_at=now, updated_at=now)
    db.add(account)
    db.flush()
    return account


def seed_demo_data(db: Session, password: str) -> dict:
    """Write the demo data in one transaction and report what was created."""
    now = timestamp()
    password_hash = hash_password(password)
    created: dict[str, int] = {"accounts": 0, "profiles": 0, "groups": 0, "members": 0}

    for email, _name in DEMO_ADMINS:
        if _account(db, email, "admin", password_hash, now) is not None:
            created["accounts"] += 1
    first_reviewer = db.scalar(select(UserAccount).where(UserAccount.email == DEMO_ADMINS[0][0]))

    tutor_email, tutor_name = DEMO_TUTOR
    tutor_account = _account(db, tutor_email, "tutor", password_hash, now)
    if tutor_account is not None:
        created["accounts"] += 1
        tutor = Tutor(account_id=tutor_account.id, full_name=tutor_name, email=tutor_email, phone_number="",
                      subject="Mathematics", teaching_level="University", experience_years=3, hourly_rate=15.0,
                      bio="Demo tutor account for course demonstrations.", availability="Weekday evenings",
                      subjects_json=json.dumps(["Mathematics"]))
        db.add(tutor)
        db.flush()
        db.add(TutorVerification(tutor_id=tutor.id, status="approved", reviewer_account_id=first_reviewer.id,
                                 reviewed_at=now, review_note="Demo data."))
        created["profiles"] += 1
    tutor_account = db.scalar(select(UserAccount).where(UserAccount.email == tutor_email))

    students = []
    for email, name in DEMO_STUDENTS:
        account = _account(db, email, "student", password_hash, now)
        if account is not None:
            created["accounts"] += 1
            db.add(Student(account_id=account.id, full_name=name, email=email, phone_number="",
                           education_level="University", preferred_subjects="Mathematics",
                           subjects_json=json.dumps(["Mathematics"])))
            created["profiles"] += 1
        students.append(db.scalar(select(UserAccount).where(UserAccount.email == email)))

    group = db.scalar(select(LearningGroup).where(LearningGroup.name == DEMO_GROUP, LearningGroup.owner_account_id == tutor_account.id))
    if group is None:
        group = LearningGroup(owner_account_id=tutor_account.id, name=DEMO_GROUP,
                              description="Sample group with mixed member permissions.", created_at=now, updated_at=now)
        db.add(group)
        db.flush()
        created["groups"] += 1
        # Student 1 may create, edit and assign tasks; Student 2 is a plain member.
        permissions = [(students[0], True, True, True), (students[1], False, False, False)]
        for account, can_create, can_edit, can_assign in permissions:
            db.add(LearningGroupMember(group_id=group.id, student_account_id=account.id, can_create_tasks=can_create,
                                       can_edit_tasks=can_edit, can_assign_tasks=can_assign, joined_at=now))
            created["members"] += 1
    db.commit()
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Required: acknowledge that demo data will be written.")
    args = parser.parse_args(argv)
    if not args.confirm:
        print("Refusing to write: pass --confirm after checking the target database below.", file=sys.stderr)
        return 2

    password = os.getenv("DEMO_PASSWORD", "")
    if not 12 <= len(password) <= 128:
        print("DEMO_PASSWORD must be set to a demo-only password of 12 to 128 characters.", file=sys.stderr)
        return 2

    from app.database import DATABASE_URL, SessionLocal
    url = make_url(DATABASE_URL)
    print(f"Target database: {url.host or 'local'} / {url.database} (credentials not shown)")
    with SessionLocal() as db:
        summary = seed_demo_data(db, password)
    print(f"Demo seed finished: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
