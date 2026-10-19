from sqlmodel import Session, SQLModel, create_engine

from app.requests.models import RequestStatus, TutoringRequest
from app.students.models import Student
from app.tutors.models import Tutor


def test_core_tables_and_relationships() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        student = Student(
            name="Test Student",
            email="student@example.com",
            education_level="University",
        )
        tutor = Tutor(
            name="Test Tutor",
            email="tutor@example.com",
            subject="Mathematics",
            teaching_level="University",
            experience=3,
        )
        session.add(student)
        session.add(tutor)
        session.commit()
        session.refresh(student)
        session.refresh(tutor)

        request = TutoringRequest(
            student_id=student.id,
            tutor_id=tutor.id,
            message="I need help with calculus.",
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        assert request.status == RequestStatus.PENDING
        assert request.student_id == student.id
        assert request.tutor_id == tutor.id
        assert request.student.id == student.id
        assert request.tutor.id == tutor.id
        assert request in student.requests
        assert request in tutor.requests


def test_request_status_values() -> None:
    assert {status.value for status in RequestStatus} == {
        "Pending",
        "Accepted",
        "Rejected",
    }
