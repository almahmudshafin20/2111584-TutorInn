import json
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


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
    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
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


class PersonalLearningTask(Base):
    """A private task owned by one authenticated Student or Tutor account."""
    __tablename__ = "personal_learning_tasks"
    __table_args__ = (
        Index("ix_personal_tasks_owner_due_date", "owner_account_id", "due_date"),
        Index("ix_personal_tasks_owner_category", "owner_account_id", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)


class LearningGroup(Base):
    """A tutor-owned learning group."""
    __tablename__ = "learning_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)


class LearningGroupMember(Base):
    """Student membership and owner-configured capabilities for one group."""
    __tablename__ = "learning_group_members"
    __table_args__ = (UniqueConstraint("group_id", "student_account_id", name="uq_group_student_member"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("learning_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    student_account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    can_create_tasks: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_edit_tasks: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_assign_tasks: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[str] = mapped_column(String(40), nullable=False)


class GroupLearningTask(Base):
    """A learning task shared within a group."""
    __tablename__ = "group_learning_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("learning_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)




class TutorVerification(Base):
    """Admin review state kept separate from a Tutor's account role."""
    __tablename__ = "tutor_verifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutors.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    reviewer_account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    review_note: Mapped[str] = mapped_column(String(1000), default="", nullable=False)


class GroupTaskAssignment(Base):
    """Assignment of a group task to one group member."""
    __tablename__ = "group_task_assignments"
    __table_args__ = (UniqueConstraint("task_id", "student_account_id", name="uq_group_task_student_assignment"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("group_learning_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    student_account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_at: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ManagedSubject(Base):
    """Admin-managed catalogue entry used by Student and Tutor profiles."""
    __tablename__ = "managed_subjects"
    __table_args__ = (UniqueConstraint("name", name="uq_managed_subject_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)


class AccountDeletionRequest(Base):
    """Durable review record; account identifiers are cleared after approved deletion."""
    __tablename__ = "account_deletion_requests"
    __table_args__ = (
        Index(
            "uq_account_deletion_pending", "account_id", unique=True,
            postgresql_where=text("status = 'pending' AND account_id IS NOT NULL"),
            sqlite_where=text("status = 'pending' AND account_id IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    account_email: Mapped[str] = mapped_column(String(255), nullable=False)
    account_role: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    requested_option: Mapped[str] = mapped_column(String(16), default="complete", nullable=False)
    final_option: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Expanded preferences are separate: account action, content scope, visibility and anonymization.
    requested_account_action: Mapped[str] = mapped_column(String(24), default="delete_account", nullable=False)
    requested_content_action: Mapped[str] = mapped_column(String(24), default="delete_all", nullable=False)
    requested_content_ids: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    requested_visibility: Mapped[str] = mapped_column(String(12), default="visible", nullable=False)
    requested_anonymize_content: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    final_account_action: Mapped[str | None] = mapped_column(String(24), nullable=True)
    final_content_action: Mapped[str | None] = mapped_column(String(24), nullable=True)
    final_content_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_visibility: Mapped[str | None] = mapped_column(String(12), nullable=True)
    final_anonymize_content: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notification_status: Mapped[str] = mapped_column(String(20), default="not_sent", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    requested_at: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewed_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)


class RetainedContent(Base):
    """Minimal ownership registry for content retained after its creator account is deleted."""
    __tablename__ = "retained_content"
    __table_args__ = (
        UniqueConstraint("deletion_request_id", "content_type", "content_id", name="uq_retained_content_item"),
        Index("ix_retained_content_owner_request", "deletion_request_id", "visibility"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deletion_request_id: Mapped[int] = mapped_column(ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility: Mapped[str] = mapped_column(String(12), default="visible", nullable=False)
    anonymized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class FormerUserContentToken(Base):
    """One-time former-user verification token; only its cryptographic hash is stored."""
    __tablename__ = "former_user_content_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deletion_request_id: Mapped[int] = mapped_column(ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    consumed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class FormerUserContentRemovalRequest(Base):
    """Follow-up request by a verified former user to remove retained content."""
    __tablename__ = "former_user_content_removal_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deletion_request_id: Mapped[int] = mapped_column(ForeignKey("account_deletion_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    selected_content: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    requested_at: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewed_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    review_note: Mapped[str] = mapped_column(String(1000), default="", nullable=False)


class ContentReport(Base):
    """User-submitted moderation report for a profile or tutoring listing."""
    __tablename__ = "content_reports"
    __table_args__ = (
        Index("ix_content_reports_status_created", "status", "created_at"),
        Index("ix_content_reports_target", "target_type", "target_id"),
        Index("ix_content_reports_reporter_created", "reporter_account_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reporter_account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(12), nullable=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    review_note: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    reviewed_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
