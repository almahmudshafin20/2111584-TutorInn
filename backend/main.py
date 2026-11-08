import json
import os
from pathlib import Path
from typing import Generator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Integer, String, Text, UniqueConstraint, create_engine, select, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool

app = FastAPI(title="TutorInn API", version="2.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url="/api/redoc")

_UNSUPPORTED_QUERY_KEYS = {"supa", "pgbouncer"}


def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        parts = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parts.query) if key not in _UNSUPPORTED_QUERY_KEYS]
        return urlunsplit(parts._replace(query=urlencode(query)))
    return f"sqlite:///{Path(__file__).resolve().parent / 'tutorinn.db'}"


DATABASE_URL = database_url()
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, connect_args={"prepare_threshold": None}, poolclass=NullPool, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def split_legacy_subjects(value: str | None) -> list[str]:
    return normalize_subjects([part.strip() for part in (value or "").replace(";", ",").split(",")])


def normalize_subjects(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = str(raw).strip()
        key = value.casefold()
        if value and key not in seen:
            result.append(value[:80])
            seen.add(key)
    return result[:20]


def read_subjects(raw: str | None, legacy: str | None = None) -> list[str]:
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return normalize_subjects(parsed)
        except (TypeError, ValueError):
            pass
    return split_legacy_subjects(legacy)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    education_level: Mapped[str] = mapped_column(String(80), nullable=False)
    preferred_subjects: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subjects_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def subjects(self) -> list[str]:
        return read_subjects(self.subjects_json, self.preferred_subjects)


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
    subjects_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def subjects(self) -> list[str]:
        return read_subjects(self.subjects_json, self.subject)


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
    author_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    author_profile_type: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    subjects_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def subjects(self) -> list[str]:
        return read_subjects(self.subjects_json, self.subject)


class InterestResponse(Base):
    __tablename__ = "interest_responses"
    __table_args__ = (UniqueConstraint("post_id", "profile_type", "profile_id", name="uq_interest_post_profile"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    profile_type: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    response: Mapped[str] = mapped_column(String(20), nullable=False, default="Interested")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Not required")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)


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
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
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
    email: str
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


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    configured_key = os.getenv("ADMIN_API_KEY")
    if not configured_key:
        raise HTTPException(status_code=503, detail="Admin actions are disabled until ADMIN_API_KEY is configured on the backend.")
    if not x_admin_key or x_admin_key != configured_key:
        raise HTTPException(status_code=403, detail="Valid Admin API key required.")


def require_demo_profile(
    x_profile_id: int | None = Header(default=None, alias="X-TutorInn-Profile-ID"),
    x_profile_type: str | None = Header(default=None, alias="X-TutorInn-Profile-Type"),
    db: Session = Depends(get_db),
) -> tuple[str, int]:
    if x_profile_type not in {"student", "tutor"} or x_profile_id is None:
        raise HTTPException(status_code=403, detail="Select a Student or Tutor profile before performing this action.")
    model = Student if x_profile_type == "student" else Tutor
    if db.get(model, x_profile_id) is None:
        raise HTTPException(status_code=409, detail="The selected profile no longer exists. Select another profile.")
    return x_profile_type, x_profile_id


Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    migrations = {
        "students": {"subjects_json": "TEXT"},
        "tutors": {"subjects_json": "TEXT"},
        "learning_posts": {
            "author_profile_id": "INTEGER",
            "author_profile_type": "VARCHAR(12)",
            "subjects_json": "TEXT",
            "student_response": "VARCHAR(20) NOT NULL DEFAULT 'No response'",
            "tutor_response": "VARCHAR(20) NOT NULL DEFAULT 'No response'",
        },
    }
    for table_name, columns in migrations.items():
        existing = {column["name"] for column in inspect(engine).get_columns(table_name)}
        for column_name, sql_type in columns.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"))
    # Leave new JSON columns NULL for legacy rows so model properties can read old text fields.
    # Ownership remains NULL for legacy posts; never guess or backfill an author profile.


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": "configured"}


@app.get("/api/subjects")
def list_subjects(db: Session = Depends(get_db)) -> list[str]:
    found: dict[str, str] = {}
    for profile in list(db.scalars(select(Tutor)).all()) + list(db.scalars(select(Student)).all()):
        for subject in profile.subjects:
            found.setdefault(subject.casefold(), subject)
    for post in db.scalars(select(LearningPost)).all():
        for subject in post.subjects:
            found.setdefault(subject.casefold(), subject)
    return sorted(found.values(), key=str.casefold)


@app.post("/api/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentInput, db: Session = Depends(get_db)) -> Student:
    if db.scalar(select(Student).where(Student.email == payload.email)):
        raise HTTPException(status_code=409, detail="A student with this email already exists.")
    subjects = normalize_subjects(payload.subjects or split_legacy_subjects(payload.preferred_subjects))
    student = Student(full_name=payload.full_name, email=payload.email, education_level=payload.education_level,
                      preferred_subjects=", ".join(subjects), subjects_json=json.dumps(subjects, ensure_ascii=False))
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.get("/api/students", response_model=list[StudentRead])
def list_students(q: str | None = Query(default=None, max_length=120), subject: str | None = Query(default=None, max_length=80),
                  db: Session = Depends(get_db)) -> list[Student]:
    statement = select(Student).order_by(Student.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where((Student.full_name.ilike(pattern)) | (Student.preferred_subjects.ilike(pattern)))
    students = list(db.scalars(statement).all())
    if subject and subject.strip():
        needle = subject.strip().casefold()
        students = [item for item in students if any(value.casefold() == needle for value in item.subjects)]
    return students


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
    subjects = normalize_subjects(payload.subjects or split_legacy_subjects(payload.preferred_subjects))
    student.full_name, student.email, student.education_level = payload.full_name, payload.email, payload.education_level
    student.preferred_subjects = ", ".join(subjects)
    student.subjects_json = json.dumps(subjects, ensure_ascii=False)
    db.commit()
    db.refresh(student)
    return student


@app.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)) -> None:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    owned_posts = list(db.scalars(select(LearningPost).where(LearningPost.author_profile_type == "student", LearningPost.author_profile_id == student_id)).all())
    for post in owned_posts:
        db.query(InterestResponse).filter_by(post_id=post.id).delete(synchronize_session=False)
        db.delete(post)
    db.query(InterestResponse).filter_by(profile_type="student", profile_id=student_id).delete(synchronize_session=False)
    db.delete(student)
    db.commit()


@app.post("/api/tutors", response_model=TutorRead, status_code=status.HTTP_201_CREATED)
def create_tutor(payload: TutorInput, db: Session = Depends(get_db)) -> Tutor:
    if db.scalar(select(Tutor).where(Tutor.email == payload.email)):
        raise HTTPException(status_code=409, detail="A tutor with this email already exists.")
    subjects = payload.resolved_subjects()
    if not subjects:
        raise HTTPException(status_code=422, detail="Select at least one subject you teach.")
    tutor = Tutor(full_name=payload.full_name, email=payload.email, subject=subjects[0], teaching_level=payload.teaching_level,
                  experience_years=payload.experience_years, hourly_rate=payload.hourly_rate, bio=payload.bio,
                  subjects_json=json.dumps(subjects, ensure_ascii=False))
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor


@app.get("/api/tutors", response_model=list[TutorRead])
def list_tutors(q: str | None = Query(default=None, max_length=120), subject: str | None = Query(default=None, max_length=80),
                level: str | None = Query(default=None, max_length=80), db: Session = Depends(get_db)) -> list[Tutor]:
    statement = select(Tutor).order_by(Tutor.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where((Tutor.full_name.ilike(pattern)) | (Tutor.subject.ilike(pattern)) | (Tutor.bio.ilike(pattern)))
    if level and level.strip():
        statement = statement.where(Tutor.teaching_level.ilike(f"%{level.strip()}%"))
    tutors = list(db.scalars(statement).all())
    if subject and subject.strip():
        needle = subject.strip().casefold()
        tutors = [item for item in tutors if any(value.casefold() == needle for value in item.subjects)]
    return tutors


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
    subjects = payload.resolved_subjects()
    if not subjects:
        raise HTTPException(status_code=422, detail="Select at least one subject you teach.")
    tutor.full_name, tutor.email, tutor.teaching_level = payload.full_name, payload.email, payload.teaching_level
    tutor.experience_years, tutor.hourly_rate, tutor.bio = payload.experience_years, payload.hourly_rate, payload.bio
    tutor.subject, tutor.subjects_json = subjects[0], json.dumps(subjects, ensure_ascii=False)
    db.commit()
    db.refresh(tutor)
    return tutor


@app.delete("/api/tutors/{tutor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tutor(tutor_id: int, db: Session = Depends(get_db)) -> None:
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    owned_posts = list(db.scalars(select(LearningPost).where(LearningPost.author_profile_type == "tutor", LearningPost.author_profile_id == tutor_id)).all())
    for post in owned_posts:
        db.query(InterestResponse).filter_by(post_id=post.id).delete(synchronize_session=False)
        db.delete(post)
    db.query(InterestResponse).filter_by(profile_type="tutor", profile_id=tutor_id).delete(synchronize_session=False)
    db.delete(tutor)
    db.commit()


@app.post("/api/posts", response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: LearningPostInput, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    profile_type, profile_id = profile
    if payload.post_type != profile_type:
        raise HTTPException(status_code=403, detail="The selected profile type must match the listing type.")
    model = Tutor if profile_type == "tutor" else Student
    author = db.get(model, profile_id)
    subjects = payload.resolved_subjects()
    if not subjects:
        raise HTTPException(status_code=422, detail="Select at least one subject for this listing.")
    post = LearningPost(post_type=profile_type, author_name=author.full_name, subject=subjects[0], level=payload.level,
                        experience=payload.experience, availability=payload.availability, location=payload.location,
                        fee=payload.fee, description=payload.description, author_profile_id=profile_id,
                        author_profile_type=profile_type, subjects_json=json.dumps(subjects, ensure_ascii=False))
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/api/posts", response_model=list[LearningPostRead])
def list_posts(post_type: str | None = Query(default=None, pattern="^(tutor|student)$"),
               subject: str | None = Query(default=None, max_length=80), offset: int = Query(default=0, ge=0, le=180),
               limit: int = Query(default=20, ge=1, le=20), db: Session = Depends(get_db)) -> list[LearningPost]:
    statement = select(LearningPost).order_by(LearningPost.id.desc())
    if post_type:
        statement = statement.where(LearningPost.post_type == post_type)
    posts = list(db.scalars(statement.offset(offset).limit(limit)).all())
    if subject and subject.strip():
        needle = subject.strip().casefold()
        posts = [item for item in posts if any(value.casefold() == needle for value in item.subjects)]
    return posts


@app.get("/api/posts/{post_id}", response_model=LearningPostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    return post


@app.put("/api/posts/{post_id}", response_model=LearningPostRead)
def update_post(post_id: int, payload: LearningPostInput, db: Session = Depends(get_db),
                profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if (post.author_profile_type, post.author_profile_id) != profile:
        raise HTTPException(status_code=403, detail="Only the selected author profile can edit this post. Legacy posts without an owner cannot be edited.")
    if payload.post_type != profile[0]:
        raise HTTPException(status_code=403, detail="The selected profile type cannot change a post's type.")
    if post.status in {"Accepted", "Completed"}:
        raise HTTPException(status_code=409, detail="Accepted tasks cannot be edited.")
    subjects = payload.resolved_subjects()
    if not subjects:
        raise HTTPException(status_code=422, detail="Select at least one subject for this listing.")
    post.author_name = (db.get(Tutor if profile[0] == "tutor" else Student, profile[1])).full_name
    post.subject, post.subjects_json = subjects[0], json.dumps(subjects, ensure_ascii=False)
    for key in ("level", "experience", "availability", "location", "fee", "description"):
        setattr(post, key, getattr(payload, key))
    db.commit()
    db.refresh(post)
    return post


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> None:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if (post.author_profile_type, post.author_profile_id) != profile:
        raise HTTPException(status_code=403, detail="Only the selected author profile can delete this post.")
    db.query(InterestResponse).filter_by(post_id=post_id).delete(synchronize_session=False)
    db.delete(post)
    db.commit()


@app.post("/api/posts/{post_id}/response", response_model=ResponseRead)
def set_interest_response(post_id: int, payload: ResponseInput, db: Session = Depends(get_db),
                          profile: tuple[str, int] = Depends(require_demo_profile)) -> InterestResponse:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    profile_type, profile_id = profile
    expected = "student" if post.post_type == "tutor" else "tutor"
    if profile_type != expected:
        raise HTTPException(status_code=409, detail=f"Only the opposite profile type ({expected}) can respond to this post.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending posts can receive or change responses.")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    response = db.scalar(select(InterestResponse).where(InterestResponse.post_id == post_id,
        InterestResponse.profile_type == profile_type, InterestResponse.profile_id == profile_id))
    if response is None:
        response = InterestResponse(post_id=post_id, profile_id=profile_id, profile_type=profile_type,
            response=payload.response, review_status="Pending" if payload.response == "Interested" else "Not required",
            created_at=now, updated_at=now)
        db.add(response)
    else:
        response.response = payload.response
        response.review_status = "Pending" if payload.response == "Interested" else "Not required"
        response.updated_at = now
    db.commit()
    db.refresh(response)
    return response


@app.get("/api/responses", response_model=list[ResponseRead])
def list_my_responses(db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> list[InterestResponse]:
    return list(db.scalars(select(InterestResponse).where(InterestResponse.profile_type == profile[0],
        InterestResponse.profile_id == profile[1]).order_by(InterestResponse.updated_at.desc())).all())


@app.get("/api/admin/responses", response_model=list[ResponseRead])
def list_admin_responses(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
                         db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> list[InterestResponse]:
    return list(db.scalars(select(InterestResponse).where(InterestResponse.response == "Interested",
        InterestResponse.review_status == review_status).order_by(InterestResponse.updated_at.desc())).all())


@app.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(response_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> InterestResponse:
    response = db.get(InterestResponse, response_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Interest response not found.")
    if response.response != "Interested" or response.review_status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending Interested responses can be approved.")
    response.review_status = "Approved"
    db.commit()
    db.refresh(response)
    return response


@app.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(response_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> InterestResponse:
    response = db.get(InterestResponse, response_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Interest response not found.")
    if response.response != "Interested" or response.review_status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending Interested responses can be rejected.")
    response.review_status = "Rejected"
    db.commit()
    db.refresh(response)
    return response


# Compatibility endpoints retained for old clients. They now require a selected profile
# and write only that profile's response record.
@app.post("/api/posts/{post_id}/confirm", response_model=LearningPostRead)
def legacy_confirm(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return _legacy_response(post_id, "Interested", db, profile)


@app.post("/api/posts/{post_id}/not-interested", response_model=LearningPostRead)
def legacy_not_interested(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return _legacy_response(post_id, "Not Interested", db, profile)


def _legacy_response(post_id: int, value: str, db: Session, profile: tuple[str, int]) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    expected = "student" if post.post_type == "tutor" else "tutor"
    if profile[0] != expected:
        raise HTTPException(status_code=409, detail=f"Only {expected.title()} profiles can respond to this post.")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    item = db.scalar(select(InterestResponse).where(InterestResponse.post_id == post_id,
        InterestResponse.profile_type == profile[0], InterestResponse.profile_id == profile[1]))
    if item is None:
        item = InterestResponse(post_id=post_id, profile_id=profile[1], profile_type=profile[0], response=value,
            review_status="Pending" if value == "Interested" else "Not required", created_at=now, updated_at=now)
        db.add(item)
    else:
        item.response, item.review_status, item.updated_at = value, ("Pending" if value == "Interested" else "Not required"), now
    db.commit()
    db.refresh(post)
    return post


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
