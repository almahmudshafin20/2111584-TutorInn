import os
from pathlib import Path
from typing import Generator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool

app = FastAPI(title="TutorInn API", version="1.0.0")


_UNSUPPORTED_QUERY_KEYS = {"supa", "pgbouncer"}


def database_url() -> str:
    """Use a configured PostgreSQL/Supabase URL in deployment; SQLite is for local development."""
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        # Some providers still supply the legacy postgres:// scheme.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        # Supabase/Vercel may add parameters intended for other clients (for example
        # pgbouncer). Psycopg rejects those parameters, so keep only supported ones.
        parts = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parts.query) if key not in _UNSUPPORTED_QUERY_KEYS]
        return urlunsplit(parts._replace(query=urlencode(query)))
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


class TutorRead(TutorInput):
    model_config = ConfigDict(from_attributes=True)
    id: int



class LearningPost(Base):
    __tablename__ = "learning_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_type: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(80), nullable=False)
    experience: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    availability: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    fee: Mapped[float] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)
    student_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    tutor_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    student_response: Mapped[str] = mapped_column(String(20), default="No response", nullable=False)
    tutor_response: Mapped[str] = mapped_column(String(20), default="No response", nullable=False)


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


def require_demo_role(x_tutorinn_role: str | None = Header(default=None, alias="X-TutorInn-Role")) -> str:
    if x_tutorinn_role not in {"student", "tutor"}:
        raise HTTPException(status_code=403, detail="Select Student or Tutor before performing this action.")
    return x_tutorinn_role


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    configured_key = os.getenv("ADMIN_API_KEY")
    if not configured_key:
        raise HTTPException(status_code=503, detail="Admin actions are disabled until ADMIN_API_KEY is configured on the backend.")
    if not x_admin_key or x_admin_key != configured_key:
        raise HTTPException(status_code=403, detail="Valid Admin API key required.")


Base.metadata.create_all(bind=engine)

# Add response-status columns to existing databases without losing current records.
from sqlalchemy import inspect, text

with engine.begin() as connection:
    existing_columns = {column["name"] for column in inspect(engine).get_columns("learning_posts")}
    if "student_response" not in existing_columns:
        connection.execute(text("ALTER TABLE learning_posts ADD COLUMN student_response VARCHAR(20) NOT NULL DEFAULT 'No response'"))
    if "tutor_response" not in existing_columns:
        connection.execute(text("ALTER TABLE learning_posts ADD COLUMN tutor_response VARCHAR(20) NOT NULL DEFAULT 'No response'"))


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
def create_student(payload: StudentInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Student:
    if actor != "student":
        raise HTTPException(status_code=403, detail="Only the Student role can create student profiles.")
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
def update_student(student_id: int, payload: StudentInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Student:
    if actor != "student":
        raise HTTPException(status_code=403, detail="Only the Student role can update student profiles.")
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
def delete_student(student_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> None:
    if actor != "student":
        raise HTTPException(status_code=403, detail="Only the Student role can delete student profiles.")
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    db.delete(student)
    db.commit()


# Tutor CRUD
@app.post("/api/tutors", response_model=TutorRead, status_code=status.HTTP_201_CREATED)
def create_tutor(payload: TutorInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Tutor:
    if actor != "tutor":
        raise HTTPException(status_code=403, detail="Only the Tutor role can create tutor profiles.")
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
def update_tutor(tutor_id: int, payload: TutorInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Tutor:
    if actor != "tutor":
        raise HTTPException(status_code=403, detail="Only the Tutor role can update tutor profiles.")
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
def delete_tutor(tutor_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> None:
    if actor != "tutor":
        raise HTTPException(status_code=403, detail="Only the Tutor role can delete tutor profiles.")
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    db.delete(tutor)
    db.commit()



# Tutor offers and student learning requests
@app.post("/api/posts", response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: LearningPostInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    if payload.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only create {actor} listings.")
    post = LearningPost(**payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/api/posts", response_model=list[LearningPostRead])
def list_posts(
    post_type: str | None = Query(default=None, pattern="^(tutor|student)$"),
    offset: int = Query(default=0, ge=0, le=180),
    limit: int = Query(default=20, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[LearningPost]:
    statement = select(LearningPost).order_by(LearningPost.id.desc())
    if post_type:
        statement = statement.where(LearningPost.post_type == post_type)
    statement = statement.offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@app.get("/api/posts/{post_id}", response_model=LearningPostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    return post


@app.put("/api/posts/{post_id}", response_model=LearningPostRead)
def update_post(post_id: int, payload: LearningPostInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.post_type != actor or payload.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only edit its own listing type.")
    if post.status in {"Accepted", "Completed"}:
        raise HTTPException(status_code=409, detail="Accepted tasks cannot be edited.")
    for key, value in payload.model_dump().items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> None:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only delete its own listing type.")
    db.delete(post)
    db.commit()


@app.post("/api/posts/{post_id}/confirm", response_model=LearningPostRead)
def confirm_post(post_id: int, payload: ConfirmationInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    """Record interest only; this must never approve a listing."""
    if payload.actor != actor:
        raise HTTPException(status_code=403, detail="The selected role does not match the request actor.")
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending listings can receive interest.")
    expected_actor = "student" if post.post_type == "tutor" else "tutor"
    if payload.actor != expected_actor:
        listing_label = "tutor offer" if post.post_type == "tutor" else "student request"
        raise HTTPException(status_code=409, detail=f"This {listing_label} can only receive interest from the opposite role ({expected_actor.title()}).")
    if expected_actor == "student":
        post.student_confirmed = True
        post.student_response = "Interested"
    else:
        post.tutor_confirmed = True
        post.tutor_response = "Interested"
    db.commit()
    db.refresh(post)
    return post


@app.post("/api/posts/{post_id}/not-interested", response_model=LearningPostRead)
def mark_not_interested(post_id: int, payload: ConfirmationInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    if payload.actor != actor:
        raise HTTPException(status_code=403, detail="The selected role does not match the request actor.")
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending listings can change interest.")
    expected_actor = "student" if post.post_type == "tutor" else "tutor"
    if payload.actor != expected_actor:
        raise HTTPException(status_code=409, detail=f"Only the opposite role ({expected_actor.title()}) can change interest for this listing.")
    if expected_actor == "student":
        post.student_confirmed = False
        post.student_response = "Not Interested"
    else:
        post.tutor_confirmed = False
        post.tutor_response = "Not Interested"
    db.commit()
    db.refresh(post)
    return post


@app.post("/api/posts/{post_id}/approve", response_model=LearningPostRead)
def approve_post(post_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending listings can be approved.")
    if not (post.student_confirmed or post.tutor_confirmed):
        raise HTTPException(status_code=409, detail="A listing must have an interested Student or Tutor before approval.")
    post.status = "Accepted"
    db.commit()
    db.refresh(post)
    return post


@app.post("/api/posts/{post_id}/reject", response_model=LearningPostRead)
def reject_post(post_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending listings can be rejected.")
    if not (post.student_confirmed or post.tutor_confirmed):
        raise HTTPException(status_code=409, detail="A listing must have an interested Student or Tutor before rejection.")
    post.status = "Rejected"
    db.commit()
    db.refresh(post)
    return post


@app.post("/api/posts/{post_id}/withdraw", response_model=LearningPostRead)
def withdraw_post(post_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if post.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only withdraw its own listing type.")
    if post.status in {"Accepted", "Completed"}:
        raise HTTPException(status_code=409, detail="Accepted tasks cannot be withdrawn.")
    post.status = "Withdrawn"
    db.commit()
    db.refresh(post)
    return post


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
