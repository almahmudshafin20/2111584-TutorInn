from pydantic import BaseModel, ConfigDict, Field, field_validator
try:
    from backend.models import normalize_subjects, split_legacy_subjects
except ModuleNotFoundError:
    from models import normalize_subjects, split_legacy_subjects


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
    account: AccountRead


class SessionRead(BaseModel):
    id: int
    created_at: str
    last_used_at: str
    expires_at: str
    user_agent: str
    ip_address: str
    current: bool = False
