from datetime import date
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from .models import normalize_subjects, split_legacy_subjects


class StudentInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    phone_number: str = Field(default="", max_length=32)
    education_level: str = Field(min_length=2, max_length=80)
    subjects: list[str] = Field(default_factory=list, max_length=20)
    preferred_subjects: str = Field(default="", max_length=255)

    @field_validator("full_name", "education_level")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone_number(cls, value: str) -> str:
        value = value.strip()
        if value and not all(char.isdigit() or char in "+-() " for char in value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_subjects(cls, value: list[str]) -> list[str]:
        return normalize_subjects(value)


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    education_level: str
    subjects: list[str]


class TutorInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    phone_number: str = Field(default="", max_length=32)
    subjects: list[str] = Field(default_factory=list, max_length=20)
    subject: str = Field(default="", max_length=120)
    teaching_level: str = Field(min_length=2, max_length=80)
    experience_years: int = Field(ge=0, le=60)
    hourly_rate: float = Field(gt=0, le=100000)
    bio: str = Field(default="", max_length=2000)
    availability: str = Field(default="", max_length=255)

    @field_validator("full_name", "teaching_level")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone_number(cls, value: str) -> str:
        value = value.strip()
        if value and not all(char.isdigit() or char in "+-() " for char in value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_subjects(cls, value: list[str]) -> list[str]:
        return normalize_subjects(value)

    def resolved_subjects(self) -> list[str]:
        return normalize_subjects(self.subjects or split_legacy_subjects(self.subject))


class TutorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    subjects: list[str]
    teaching_level: str
    experience_years: int
    hourly_rate: float
    bio: str
    availability: str = ""


class LearningPostInput(BaseModel):
    post_type: str = Field(pattern="^(tutor|student)$")
    author_name: str = Field(default="Selected profile", max_length=120)
    subjects: list[str] = Field(default_factory=list, max_length=20)
    subject: str = Field(default="", max_length=120)
    level: str = Field(min_length=1, max_length=80)
    experience: str = Field(default="", max_length=500)
    availability: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=255)
    fee: float = Field(ge=0, le=1000000)
    description: str = Field(default="", max_length=4000)

    @field_validator("author_name")
    @classmethod
    def clean_author_name(cls, value: str) -> str:
        return value.strip() or "Selected profile"

    @field_validator("level")
    @classmethod
    def clean_level(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_subjects(cls, value: list[str]) -> list[str]:
        return normalize_subjects(value)

    def resolved_subjects(self) -> list[str]:
        return normalize_subjects(self.subjects or split_legacy_subjects(self.subject))


class LearningPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_type: str
    author_name: str
    subjects: list[str]
    subject: str
    level: str
    experience: str
    availability: str
    location: str
    fee: float
    description: str
    status: str
    author_profile_id: int | None = None
    author_profile_type: str | None = None
    student_confirmed: bool = False
    tutor_confirmed: bool = False
    student_response: str = "No response"
    tutor_response: str = "No response"


class ResponseInput(BaseModel):
    response: str = Field(pattern="^(Interested|Not Interested)$")


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_id: int
    profile_id: int
    profile_type: str
    response: str
    review_status: str
    created_at: str
    updated_at: str


class StudentRegistrationInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    phone_number: str = Field(default="", max_length=32)
    education_level: str = Field(min_length=2, max_length=80)
    subjects: list[str] = Field(default_factory=list, min_length=1, max_length=20)

    @field_validator("full_name", "education_level")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_registration_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_registration_phone(cls, value: str) -> str:
        value = value.strip()
        if value and not all(char.isdigit() or char in "+-() " for char in value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_registration_subjects(cls, value: list[str]) -> list[str]:
        result = normalize_subjects(value)
        if not result:
            raise ValueError("Select at least one subject.")
        return result


class TutorRegistrationInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    phone_number: str = Field(default="", max_length=32)
    subjects: list[str] = Field(min_length=1, max_length=20)
    teaching_level: str = Field(min_length=2, max_length=80)
    experience_years: int = Field(ge=0, le=60)
    hourly_rate: float = Field(gt=0, le=100000)
    bio: str = Field(default="", max_length=2000)
    availability: str = Field(default="Flexible", max_length=255)

    @field_validator("full_name", "teaching_level")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_registration_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_registration_phone(cls, value: str) -> str:
        value = value.strip()
        if value and not all(char.isdigit() or char in "+-() " for char in value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_registration_subjects(cls, value: list[str]) -> list[str]:
        result = normalize_subjects(value)
        if not result:
            raise ValueError("Select at least one subject.")
        return result


class LoginInput(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value


class AdminBootstrapInput(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_admin_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    status: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    csrf_token: str
    account: AccountRead


class SessionRead(BaseModel):
    id: int
    created_at: str
    last_used_at: str
    expires_at: str
    user_agent: str
    ip_address: str
    current: bool = False


class StudentPrivateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    phone_number: str
    education_level: str
    subjects: list[str]


class TutorPrivateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    phone_number: str
    subjects: list[str]
    teaching_level: str
    experience_years: int
    hourly_rate: float
    bio: str
    availability: str


class StudentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(default="", max_length=32)
    education_level: str = Field(min_length=2, max_length=80)
    subjects: list[str] = Field(min_length=1, max_length=20)

    @field_validator("full_name", "education_level")
    @classmethod
    def clean_student_profile_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_student_profile_phone(cls, value: str) -> str:
        value = value.strip()
        if value and not all(char.isdigit() or char in "+-() " for char in value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_student_profile_subjects(cls, value: list[str]) -> list[str]:
        result = normalize_subjects(value)
        if not result:
            raise ValueError("Select at least one subject.")
        return result


class TutorProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(default="", max_length=32)
    subjects: list[str] = Field(min_length=1, max_length=20)
    teaching_level: str = Field(min_length=2, max_length=80)
    experience_years: int = Field(ge=0, le=60)
    hourly_rate: float = Field(gt=0, le=100000)
    bio: str = Field(default="", max_length=2000)
    availability: str = Field(default="Flexible", max_length=255)

    @field_validator("full_name", "teaching_level")
    @classmethod
    def clean_tutor_profile_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_tutor_profile_phone(cls, value: str) -> str:
        value = value.strip()
        if value and not all(char.isdigit() or char in "+-() " for char in value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("subjects")
    @classmethod
    def clean_tutor_profile_subjects(cls, value: list[str]) -> list[str]:
        result = normalize_subjects(value)
        if not result:
            raise ValueError("Select at least one subject.")
        return result


class PasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class PersonalTaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    category: str | None = Field(default=None, max_length=60)
    due_date: date | None = None
    completed: bool = False

    @field_validator("title")
    @classmethod
    def clean_task_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def clean_task_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("category")
    @classmethod
    def clean_task_category(cls, value: str | None) -> str | None:
        value = value.strip() if value else ""
        return value or None


class PersonalTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: str | None
    due_date: date | None
    completed: bool
    created_at: str
    updated_at: str

    @computed_field
    @property
    def status(self) -> str:
        if self.completed:
            return "completed"
        if self.due_date is not None and self.due_date < date.today():
            return "overdue"
        return "open"


class PersonalTaskSummaryRead(BaseModel):
    total_count: int
    open_count: int
    completed_count: int
    overdue_count: int
    uncategorized_count: int
    categories: list[str]


class LearningGroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=1000)

    @field_validator("name")
    @classmethod
    def clean_group_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def clean_group_description(cls, value: str) -> str:
        return value.strip()


class LearningGroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=1000)

    @field_validator("name")
    @classmethod
    def clean_updated_group_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def clean_updated_group_description(cls, value: str) -> str:
        return value.strip()


class GroupMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_email: str = Field(min_length=5, max_length=255)

    @field_validator("student_email")
    @classmethod
    def normalize_student_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Enter a valid Student email.")
        return value


class GroupMemberPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    can_create_tasks: bool = False
    can_edit_tasks: bool = False
    can_assign_tasks: bool = False


class GroupTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    video_url: str | None = Field(default=None, max_length=2048)
    due_date: date | None = None

    @field_validator("video_url")
    @classmethod
    def validate_drive_video_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        candidate = value.strip()
        parsed = urlsplit(candidate)
        if parsed.scheme != "https" or parsed.hostname != "drive.google.com":
            raise ValueError("Use a secure Google Drive video share link.")
        parts = parsed.path.strip("/").split("/")
        file_id = parts[2] if len(parts) >= 3 and parts[0] == "file" and parts[1] == "d" else None
        if parts[0] == "open":
            file_id = parse_qs(parsed.query).get("id", [None])[0]
        if not file_id or not all(char.isalnum() or char in "_-" for char in file_id):
            raise ValueError("Enter a valid Google Drive file link.")
        return candidate

    @field_validator("title")
    @classmethod
    def clean_group_task_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def clean_group_task_description(cls, value: str) -> str:
        return value.strip()


class GroupTaskAssignmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    all_members: bool = False
    student_account_ids: list[int] = Field(default_factory=list, max_length=100)

    @field_validator("student_account_ids")
    @classmethod
    def unique_student_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("A Student can only be selected once.")
        return value


class GroupTaskCompletionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: bool


class GroupMemberRead(BaseModel):
    account_id: int
    full_name: str
    email: str
    can_create_tasks: bool
    can_edit_tasks: bool
    can_assign_tasks: bool
    joined_at: str


class GroupTaskAssignmentRead(BaseModel):
    id: int
    student_account_id: int
    student_name: str
    completed: bool
    assigned_at: str
    completed_at: str | None


class GroupTaskRead(BaseModel):
    id: int
    group_id: int
    created_by_account_id: int
    title: str
    description: str
    video_url: str | None = None
    due_date: date | None
    created_at: str
    updated_at: str
    assignments: list[GroupTaskAssignmentRead] = Field(default_factory=list)


class LearningGroupRead(BaseModel):
    id: int
    owner_account_id: int
    name: str
    description: str
    created_at: str
    updated_at: str
    member_count: int = 0
    task_count: int = 0
    is_owner: bool = False
    my_permissions: GroupMemberPermissions = Field(default_factory=GroupMemberPermissions)
    members: list[GroupMemberRead] = Field(default_factory=list)
    tasks: list[GroupTaskRead] = Field(default_factory=list)


class DeletionContentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content_type: str = Field(pattern="^(learning_post|personal_task|learning_group|group_task|group_assignment)$")
    content_id: int = Field(gt=0)


class AccountDeletionRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    reason: str = Field(default="", max_length=500)
    # Legacy field remains optional for existing clients during the migration window.
    deletion_option: str | None = Field(default=None, pattern="^(anonymize|complete)$")
    content_action: str | None = Field(default=None, pattern="^(account_only|delete_selected|delete_all|retain_all)$")
    selected_content: list[DeletionContentSelection] = Field(default_factory=list, max_length=200)
    visibility: str = Field(default="visible", pattern="^(visible|hidden)$")
    anonymize_content: bool = True


class AccountDeletionReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(approved|rejected)$")
    # Admin's final choices are independent of the user's preferences.
    deletion_option: str | None = Field(default=None, pattern="^(anonymize|complete)$")
    content_action: str | None = Field(default=None, pattern="^(account_only|delete_selected|delete_all|retain_all)$")
    selected_content: list[DeletionContentSelection] | None = Field(default=None, max_length=200)
    visibility: str | None = Field(default=None, pattern="^(visible|hidden)$")
    anonymize_content: bool | None = None
    review_note: str = Field(default="", max_length=1000)
