from pydantic import BaseModel, ConfigDict, Field, field_validator
try:
    from backend.models import normalize_subjects, split_legacy_subjects
except ModuleNotFoundError:
    from models import normalize_subjects, split_legacy_subjects

class StudentInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
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
    email: str
    education_level: str
    subjects: list[str]

class TutorInput(BaseModel):
    full_name:¶»§q«^