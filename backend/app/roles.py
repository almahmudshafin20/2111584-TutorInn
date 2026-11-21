"""Canonical account roles and permission groupings for TutorInn."""

from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    TUTOR = "tutor"
    ADMIN = "admin"
    MODERATOR = "moderator"


class Permission(StrEnum):
    VIEW_OWN_PROFILE = "view_own_profile"
    UPDATE_STUDENT_PROFILE = "update_student_profile"
    UPDATE_TUTOR_PROFILE = "update_tutor_profile"
    MANAGE_TUTORING_REQUESTS = "manage_tutoring_requests"
    REVIEW_PASSWORD_RESET_REQUESTS = "review_password_reset_requests"
    INSPECT_ACCOUNT_SESSIONS = "inspect_account_sessions"


# Course-level roles map to TutorInn's domain model: a normal user is either
# a Student or a Tutor; the course Admin role maps to the platform Admin.
COURSE_ROLE_MAPPING: dict[str, frozenset[Role]] = {
    "normal_user": frozenset({Role.STUDENT, Role.TUTOR}),
    "admin": frozenset({Role.ADMIN}),
}

ROLE_LABELS: dict[Role, str] = {
    Role.STUDENT: "Student",
    Role.TUTOR: "Tutor",
    Role.ADMIN: "Admin",
    Role.MODERATOR: "Moderator",
}

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.STUDENT: frozenset({
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_STUDENT_PROFILE,
        Permission.MANAGE_TUTORING_REQUESTS,
    }),
    Role.TUTOR: frozenset({
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_TUTOR_PROFILE,
        Permission.MANAGE_TUTORING_REQUESTS,
    }),
    Role.ADMIN: frozenset({
        Permission.REVIEW_PASSWORD_RESET_REQUESTS,
        Permission.INSPECT_ACCOUNT_SESSIONS,
    }),
    Role.MODERATOR: frozenset({
        Permission.REVIEW_PASSWORD_RESET_REQUESTS,
    }),
}
