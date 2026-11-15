import json

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

try:
    from backend.database import Base
except ModuleNotFoundError:
    from database import Base


def split_legacy_subjects(value: str | None) -> list[str]:
    return normalize_subjects([part.strip() for part in (value or "").replace(";", ",").split(",")])


def normalize_subjects(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = str(raw).strip()
        key = value.casefold()
        if value and key not in seen:
            result.append(value[:80])
            seen.add(key)
    return result[:20]


def read_subjects(raw: str | None, legacy: str | None = None) -> list[str]:
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return normalize_subjects(parsed)
        except (TypeError, ValueError):
            pass
    return split_legacy_subjects(legacy)


class UserAccount(Base):
    """Credential and authorization record shared by all TutorInn roles."""

    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)


class RefreshSession(Base):
    """Server-side refresh-token session; raw refresh tokens are never persisted."""

    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    last_used_at: Mapped[str] = mapped_column(String(40), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    revoked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class SecurityEvent(Base):
    """Minimal security audit record; never store passwords or raw tokens."""

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    attempted_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    education_level: Mapped[str] = mapped_column(String(80), nullable=False)
    preferred_subjects: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subjects_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def subjects(self) -> list[str]:
        return read_subjects(self.subjects_json, self.preferred_subjects)


class Tutor(Base):
    __tablename__ = "tutors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    teaching_level: Mapped[str] = mapped_column(String(80), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hourly_rate: Mapped[float] = mapped_column(nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    availability: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subjects_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def subjects(self) -> list[str]:
        return read_subjects(self.subjects_json, self.subject)


class LearningPost(Base):
    __tablename__ = "learning_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_type: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(80), nullable=False)
    experience: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    availability: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    fee: Mapped[float] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)
    student_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    tutor_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    student_response: Mapped[str] = mapped_column(String(20), default="No response", nullable=False)
    tutor_response: Mapped[str] = mapped_column(String(20), default="No response", nullable=False)
    author_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    author_profile_type: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    subjects_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def subjects(self) -> list[str]:
        return read_subjects(self.subjects_json, self.subject)


class InterestResponse(Base):
    __tablename__ = "interest_responses"
    __table_args__ = (UniqueConstraint("post_id", "profile_type", "profile_id", name="uq_interest_post_profile"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    profile_type: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    response: Mapped[str] = mapped_column(String(20), nullable=False, default="Interested")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Not required")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)
