"""Database operations and business rules for TutorInn resources."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import LearningPost, Student, Tutor
from backend.schemas import ConfirmationInput, LearningPostInput, StudentInput, TutorInput


# Student operations

def create_student(db: Session, payload: StudentInput, actor: str) -> Student:
    if actor != "student":
        raise HTTPException(status_code=403, detail="Only the Student role can create student profiles.")
    if db.scalar(select(Student).where(Student.email == payload.email)):
        raise HTTPException(status_code=409, detail="A student with this email already exists.")
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def list_students(db: Session, q: str | None = None) -> list[Student]:
    statement = select(Student).order_by(Student.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where((Student.full_name.ilike(pattern)) | (Student.preferred_subjects.ilike(pattern)))
    return list(db.scalars(statement).all())


def get_student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


def update_student(db: Session, student_id: int, payload: StudentInput, actor: str) -> Student:
    if actor != "student":
        raise HTTPException(status_code=403, detail="Only the Student role can update student profiles.")
    student = get_student(db, student_id)
    duplicate = db.scalar(select(Student).where(Student.email == payload.email, Student.id != student_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another student already uses this email.")
    for key, value in payload.model_dump().items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: int, actor: str) -> None:
    if actor != "student":
        raise HTTPException(status_code=403, detail="Only the Student role can delete student profiles.")
    student = get_student(db, student_id)
    db.delete(student)
    db.commit()


# Tutor operations

def create_tutor(db: Session, payload: TutorInput, actor: str) -> Tutor:
    if actor != "tutor":
        raise HTTPException(status_code=403, detail="Only the Tutor role can create tutor profiles.")
    if db.scalar(select(Tutor).where(Tutor.email == payload.email)):
        raise HTTPException(status_code=409, detail="A tutor with this email already exists.")
    tutor = Tutor(**payload.model_dump())
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor


def list_tutors(db: Session, q: str | None = None, subject: str | None = None, level: str | None = None) -> list[Tutor]:
    statement = select(Tutor).order_by(Tutor.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where((Tutor.full_name.ilike(pattern)) | (Tutor.subject.ilike(pattern)) | (Tutor.bio.ilike(pattern)))
    if subject and subject.strip():
        statement = statement.where(Tutor.subject.ilike(f"%{subject.strip()}%"))
    if level and level.strip():
        statement = statement.where(Tutor.teaching_level.ilike(f"%{level.strip()}%"))
    return list(db.scalars(statement).all())


def get_tutor(db: Session, tutor_id: int) -> Tutor:
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    return tutor


def update_tutor(db: Session, tutor_id: int, payload: TutorInput, actor: str) -> Tutor:
    if actor != "tutor":
        raise HTTPException(status_code=403, detail="Only the Tutor role can update tutor profiles.")
    tutor = get_tutor(db, tutor_id)
    duplicate = db.scalar(select(Tutor).where(Tutor.email == payload.email, Tutor.id != tutor_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another tutor already uses this email.")
    for key, value in payload.model_dump().items():
        setattr(tutor, key, value)
    db.commit()
    db.refresh(tutor)
    return tutor


def delete_tutor(db: Session, tutor_id: int, actor: str) -> None:
    if actor != "tutor":
        raise HTTPException(status_code=403, detail="Only the Tutor role can delete tutor profiles.")
    tutor = get_tutor(db, tutor_id)
    db.delete(tutor)
    db.commit()


# Tutoring post operations

def create_post(db: Session, payload: LearningPostInput, actor: str) -> LearningPost:
    if payload.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only create {actor} listings.")
    post = LearningPost(**payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def list_posts(db: Session, post_type: str | None = None, offset: int = 0, limit: int = 20) -> list[LearningPost]:
    statement = select(LearningPost).order_by(LearningPost.id.desc())
    if post_type:
        statement = statement.where(LearningPost.post_type == post_type)
    return list(db.scalars(statement.offset(offset).limit(limit)).all())


def get_post(db: Session, post_id: int) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    return post


def update_post(db: Session, post_id: int, payload: LearningPostInput, actor: str) -> LearningPost:
    post = get_post(db, post_id)
    if post.post_type != actor or payload.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only edit its own listing type.")
    if post.status in {"Accepted", "Completed"}:
        raise HTTPException(status_code=409, detail="Accepted tasks cannot be edited.")
    for key, value in payload.model_dump().items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post_id: int, actor: str) -> None:
    post = get_post(db, post_id)
    if post.post_type != actor:
        raise HTTPException(status_code=403, detail=f"{actor.title()} role can only delete its own listing type.")
    db.delete(post)
    db.commit()


def confirm_post(db: Session, post_id: int, payload: ConfirmationInput, actor: str) -> LearningPost:
    if payload.actor != actor:
        raise HTTPException(status_code=403, detail="The selected role does not match the request actor.")
    post = get_post(db, post_id)
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


def mark_not_interested(db: Session, post_id: int, payload: ConfirmationInput, actor: str) -> LearningPost:
    if payload.actor != actor:
        raise HTTPException(status_code=403, detail="The selected role does not match the request actor.")
    post = get_post(db, post_id)
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


def approve_post(db: Session, post_id: int) -> LearningPost:
    post = get_post(db, post_id)
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending listings can be approved.")
    if not (post.student_confirmed or post.tutor_confirmed):
        raise HTTPException(status_code=409, detail="A listing must have an interested Student or Tutor before approval.")
    post.status = "Accepted"
    db.commit()
    db.refresh(post)
    return post


def reject_post(db: Session, post_id: int) -> LearningPost:
    post = get_post(db, post_id)
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending listings can be rejected.")
    if not (post.student_confirmed or post.tutor_confirmed):
        raise HTTPException(status_code=409, detail="A listing must have an interested Student or Tutor before rejection.")
    post.status = "Rejected"
    db.commit()
    db.refresh(post)
    return post
