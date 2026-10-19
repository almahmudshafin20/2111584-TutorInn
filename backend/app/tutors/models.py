from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.requests.models import TutoringRequest


class Tutor(SQLModel, table=True):
    __tablename__ = "tutors"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=1, max_length=100)
    teaching_level: str = Field(min_length=1, max_length=100)
    experience: int = Field(ge=0)
    bio: str | None = Field(default=None, max_length=1000)
    availability: str | None = Field(default=None, max_length=500)

    requests: list["TutoringRequest"] = Relationship(back_populates="tutor")
