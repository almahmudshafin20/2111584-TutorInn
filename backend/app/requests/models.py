from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.students.models import Student
    from app.tutors.models import Tutor


class RequestStatus(str, Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


class TutoringRequest(SQLModel, table=True):
    __tablename__ = "tutoring_requests"

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id", index=True, ge=1)
    tutor_id: int = Field(foreign_key="tutors.id", index=True, ge=1)
    message: str = Field(min_length=1, max_length=2000)
    status: RequestStatus = Field(default=RequestStatus.PENDING)

    student: "Student" = Relationship(back_populates="requests")
    tutor: "Tutor" = Relationship(back_populates="requests")
