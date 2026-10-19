import os
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool

app = FastAPI(title="TutorInn API", version="1.0.0")


def database_url() -> str:
    """Use a configured PostgreSQL/Supabase URL in deployment; SQLite is for local development."""
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        # Some providers still supply the legacy postgres:// scheme.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url
    local_db = Path(__file__).resolve().parent / "tutorinn.db"
    return f"sqlite:///{local_db}"


DATABASE_URL = database_url()
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # Supabase Transaction Pooler is designed for serverless workloads.
    # NullPool avoids keeping application-side connections across invocations,
    # and psycopg prepared statements are disabled because transaction pooling
    # does not support them.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"prepare_threshold": None},
        poolclass=NullPool,
        pool_pre_ping=True,
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    education_level: Mapped[str] = mapped_column(String(80), nullable=False)
    preferred_subjects: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class Tutor(Base):
    __tablename__ = "tutors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    teaching_level: Mapped[str] = mapped_column(String(80), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hourly_rate: Mapped[float] = mapped_column(nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)


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


Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": "configured"}


@app.get("/api/hello")
def hello(name: str = "World") -> dict[str, str]:
    return {"message": f"Hello, {name}!"}


# Student CRUD
@app.post("/api/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentInput, db: Session = Depends(get_db)) -> Student:
    if db.scalar(select(Student).where(Student.email == payload.email)):
        raise HTTPException(status_code=409, detail="A student with this email already exists.")
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.get("/api/students", response_model=list[StudentRead])
def list_students(
    q: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
) -> list[Student]:
    statement = select(Student).order_by(Student.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            (Student.full_name.ilike(pattern)) | (Student.preferred_subjects.ilike(pattern))
        )
    return list(db.scalars(statement).all())


@app.get("/api/students/{student_id}", response_model=StudentRead)
def get_student(student_id: int, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


@app.put("/api/students/{student_id}", response_model=StudentRead)
def update_student(student_id: int, payload: StudentInput, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    duplicate = db.scalar(select(Student).where(Student.email == payload.email, Student.id != student_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another student already uses this email.")
    for key, value in payload.model_dump().items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


@app.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)) -> None:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    db.delete(student)
    db.commit()


# Tutor CRUD
@app.post("/api/tutors", response_model=TutorRead, status_code=status.HTTP_201_CREATED)
def create_tutor(payload: TutorInput, db: Session = Depends(get_db)) -> Tutor:
    if db.scalar(select(Tutor).where(Tutor.email == payload.email)):
        raise HTTPException(status_code=409, detail="A tutor with this email already exists.")
    tutor = Tutor(**payload.model_dump())
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor


@app.get("/api/tutors", response_model=list[TutorRead])
def list_tutors(
    q: str | None = Query(default=None, max_length=120),
    subject: str | None = Query(default=None, max_length=120),
    level: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> list[Tutor]:
    statement = select(Tutor).order_by(Tutor.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            (Tutor.full_name.ilike(pattern))
            | (Tutor.subject.ilike(pattern))
            | (Tutor.bio.ilike(pattern))
        )
    if subject and subject.strip():
        statement = statement.where(Tutor.subject.ilike(f"%{subject.strip()}%"))
    if level and level.strip():
        statement = statement.where(Tutor.teaching_level.ilike(f"%{level.strip()}%"))
    return list(db.scalars(statement).all())


@app.get("/api/tutors/{tutor_id}", response_model=TutorRead)
def get_tutor(tutor_id: int, db: Session = Depends(get_db)) -> Tutor:
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    return tutor


@app.put("/api/tutors/{tutor_id}", response_model=TutorRead)
def update_tutor(tutor_id: int, payload: TutorInput, db: Session = Depends(get_db)) -> Tutor:
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    duplicate = db.scalar(select(Tutor).where(Tutor.email == payload.email, Tutor.id != tutor_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another tutor already uses this email.")
    for key, value in payload.model_dump().items():
        setattr(tutor, key, value)
    db.commit()
    db.refresh(tutor)
    return tutor


@app.delete("/api/tutors/{tutor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tutor(tutor_id: int, db: Session = Depends(get_db)) -> None:
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    db.delete(tutor)
    db.commit()


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
