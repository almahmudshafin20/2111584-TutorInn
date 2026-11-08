from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    education_level: str = Field(min_length=2, max_length=80)
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


class StudentRead(StudentInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TutorInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    subject: str = Field(min_length=2, max_length=120)
    teaching_level: str = Field(min_length=2, max_length=80)
    experience_years: int = Field(ge=0, le=60)
    hourly_rate: float = Field(gt=0, le=100000)
    bio: str = Field(default="", max_length=2000)

    @field_validator("full_name", "subject", "teaching_level")
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


class TutorRead(TutorInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class LearningPostInput(BaseModel):
    post_type: str = Field(pattern="^(tutor|student)$")
    author_name: str = Field(min_length=2, max_length=120)
    subject: str = Field(min_length=2, max_length=120)
    level: str = Field(min_length=1, max_length=80)
    experience: str = Field(default="", max_length=500)
    availability: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=255)
    fee: float = Field(ge=0, le=1000000)
    description: str = Field(default="", max_length=4000)

    @field_validator("author_name", "subject", "level")
    @classmethod
    def clean_post_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class LearningPostRead(LearningPostInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    student_confirmed: bool
    tutor_confirmed: bool
    student_response: str
    tutor_response: str


class ConfirmationInput(BaseModel):
    actor: str = Field(pattern="^(student|tutor)$")
