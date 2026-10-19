from enum import Enum

from sqlmodel import Field, SQLModel


class RequestStatus(str, Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


class TutoringRequest(SQLModel, table=True):
    __tablename__ = "tutoring_requests"

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id")
    tutor_id: int = Field(foreign_key="tutors.id")
    message: str
    status: RequestStatus = Field(default=RequestStatus.PENDING)
