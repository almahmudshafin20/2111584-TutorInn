import json
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
try:
    from backend.database import get_db
    from backend.dependencies import require_admin_key, require_demo_profile
    from backend.models import InterestResponse, LearningPost, Student, Tutor, normalize_subjects, split_legacy_subjects
    from backend.schemas import LearningPostInput, LearningPostRead, ResponseInput, ResponseRead, StudentInput, StudentRead, TutorInput, TutorRead
except ModuleNotFoundError:
    from database import get_db
    from dependencies import require_admin_key, require_demo_profile
    from models import InterestResponse, LearningPost, Student, Tutor, normalize_subjects, split_legacy_subjects
    from schemas import LearningPostInput, LearningPostRead, ResponseInput, ResponseRead, StudentInput, StudentRead, TutorInput, TutorRead


def health() -> dict[str, str]:
    return {"status": "ok", "database": "configured"}

def list_subjects(db: Session = Depends(get_db)) -> list[str]:
    found: dict[str, str] = {}
    for profile in list(db.scalars(select(Tutor)).all()) + list(db.scalars(select(Student)).all()):
        for subject in profile.subjects:
            found.setdefault(subject.casefold(), subject)
    for post in db.scalars(select(LearningPost)).all():
        for subject in post.subjects:
            found.setdefault(subject.casefold(), subject)
    return sorted(found.values(), key=str.casefold)

def create_student(payload: StudentInput, db: Session = Depends(get_db)) -> Student:
    if db.scalar(select(Student).where(Student.email == payload.email)):
        raise HTTPException(status_code=409, detail="A student with this email already exists.")
    subjects = normalize_subjects(payload.subjects or split_legacy_subjects(payload.preferred_subjects))
    student = Student(full_name=payload.full_name, email=payload.email, phone_number=payload.phone_number, education_level=payload.education_level,
                      preferred_subjects=", ".join(subjects), subjects_json=json.dumps(subjects, ensure_ascii=False))
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

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

def get_student(student_id: int, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student

def update_student(student_id: int, payload: StudentInput, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    duplicate = db.scalar(select(Student).where(Student.email == payload.email, Student.id != student_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another student already uses this email.")
    subjects = normalize_subjects(payload.subjects or split_legacy_subjects(payload.preferred_subjects))
    student.full_name, student.email, student.phone_number, student.education_level = payload.full_name, payload.email, payload.phone_number, payload.education_level
    student.preferred_subjects = ", ".join(subjects)
    student.subjects_json = json.dumps(subjects, ensure_ascii=False)
    db.commit()
    db.refresh(student)
    return student

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

def create_tutor(payload: TutorInput, db: Session = Depends(get_db)) -> Tutor:
    if db.scalar(select(Tutor).where(Tutor.email == payload.email)):
        raise HTTPException(status_code=409, detail="A tutor with this email already exists.")
    subjects = payload.resolved_subjects()
    if not subjects:
        raise HTTPException(status_code=422, detail="Select at least one subject you teach.")
    tutor = Tutor(full_name=payload.full_name, email=payload.email, phone_number=payload.phone_number, subject=subjects[0], teaching_level=payload.teaching_level,
                  experience_years=payload.experience_years, hourly_rate=payload.hourly_rate, bio=payload.bio,
                  availability=payload.availability, subjects_json=json.dumps(subjects, ensure_ascii=False))
    db.add(tutor)
    db.commit()
    db.refresh(tutor)
    return tutor

def list_tutors(q: str | None = Query(default=None, max_length=120), subject: str | None = Query(default=None, max_length=80),
                level: str | None = Query(default=None, max_length=80),
                min_experience: int | None = Query(default=None, ge=0, le=60),
                availability: str | None = Query(default=None, max_length=255),
                db: Session = Depends(get_db)) -> list[Tutor]:
    statement = select(Tutor).order_by(Tutor.full_name)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where((Tutor.full_name.ilike(pattern)) | (Tutor.bio.ilike(pattern)) | (Tutor.subject.ilike(pattern)))
    if level and level.strip():
        statement = statement.where(Tutor.teaching_level.ilike(f"%{level.strip()}%"))
    if min_experience is not None:
        statement = statement.where(Tutor.experience_years >= min_experience)
    if availability and availability.strip():
        statement = statement.where(Tutor.availability.ilike(f"%{availability.strip()}%"))
    tutors = list(db.scalars(statement).all())
    if q and q.strip():
        needle = q.strip().casefold()
        tutors = [item for item in tutors if needle in item.full_name.casefold() or needle in item.bio.casefold() or any(needle in value.casefold() for value in item.subjects)]
    if subject and subject.strip():
        needle = subject.strip().casefold()
        tutors = [item for item in tutors if any(value.casefold() == needle for value in item.subjects)]
    return tutors

def get_tutor(tutor_id: int, db: Session = Depends(get_db)) -> Tutor:
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found.")
    return tutor

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
    tutor.full_name, tutor.email, tutor.phone_number, tutor.teaching_level = payload.full_name, payload.email, payload.phone_number, payload.teaching_level
    tutor.experience_years, tutor.hourly_rate, tutor.bio = payload.experience_years, payload.hourly_rate, payload.bio
    tutor.availability = payload.availability
    tutor.subject, tutor.subjects_json = subjects[0], json.dumps(subjects, ensure_ascii=False)
    db.commit()
    db.refresh(tutor)
    return tutor

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

def get_post(post_id: int, db: Session = Depends(get_db)) -> LearningPost:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    return post

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

def delete_post(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> None:
    post = db.get(LearningPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Tutoring post not found.")
    if (post.author_profile_type, post.author_profile_id) != profile:
        raise HTTPException(status_code=403, detail="Only the selected author profile can delete this post.")
    db.query(InterestResponse).filter_by(post_id=post_id).delete(synchronize_session=False)
    db.delete(post)
    db.commit()

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

def list_my_responses(db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> list[InterestResponse]:
    return list(db.scalars(select(InterestResponse).where(InterestResponse.profile_type == profile[0],
        InterestResponse.profile_id == profile[1]).order_by(InterestResponse.updated_at.desc())).all())

def list_admin_responses(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
                         db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> list[InterestResponse]:
    return list(db.scalars(select(InterestResponse).where(InterestResponse.response == "Interested",
        InterestResponse.review_status == review_status).order_by(InterestResponse.updated_at.desc())).all())

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

def legacy_confirm(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return _legacy_response(post_id, "Interested", db, profile)

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

def list_approved_matches(db: Session, profile: tuple[str, int]) -> list[dict]:
    """Return only approved matches involving the selected demo profile."""
    profile_type, profile_id = profile
    responses = list(db.scalars(select(InterestResponse).where(
        InterestResponse.response == "Interested",
        InterestResponse.review_status == "Approved",
    ).order_by(InterestResponse.updated_at.desc())).all())
    matches: list[dict] = []
    for response in responses:
        post = db.get(LearningPost, response.post_id)
        if post is None or post.author_profile_id is None or post.author_profile_type not in {"student", "tutor"}:
            continue
        if (response.profile_type, response.profile_id) == profile:
            other_type, other_id = post.author_profile_type, post.author_profile_id
        elif (post.author_profile_type, post.author_profile_id) == profile:
            other_type, other_id = response.profile_type, response.profile_id
        else:
            continue
        other = db.get(Tutor if other_type == "tutor" else Student, other_id)
        if other is None:
            continue
        matches.append({
            "response": {"id": response.id, "review_status": response.review_status},
            "post": {"id": post.id, "subjects": post.subjects, "level": post.level, "location": post.location,
                     "availability": post.availability, "fee": post.fee, "description": post.description},
            "counterpart": {
                "id": other.id, "type": other_type, "full_name": other.full_name,
                "email": other.email, "phone_number": other.phone_number, "subjects": other.subjects,
                "education_level": getattr(other, "education_level", None),
                "teaching_level": getattr(other, "teaching_level", None),
                "experience_years": getattr(other, "experience_years", None),
                "hourly_rate": getattr(other, "hourly_rate", None), "bio": getattr(other, "bio", None),
            },
        })
    return matches


def hello(name: str = "World") -> dict[str, str]:
    return {"message": f"Hello, {name}!"}


def list_admin_matches(review_status: str, db: Session) -> list[dict]:
    """Return complete candidate details; the router requires the admin API key."""
    responses = list(db.scalars(select(InterestResponse).where(
        InterestResponse.response == "Interested",
        InterestResponse.review_status == review_status,
    ).order_by(InterestResponse.updated_at.desc())).all())
    result: list[dict] = []
    for response in responses:
        post = db.get(LearningPost, response.post_id)
        if post is None:
            continue
        if response.profile_type == "tutor":
            tutor = db.get(Tutor, response.profile_id)
            student = db.get(Student, post.author_profile_id) if post.author_profile_type == "student" and post.author_profile_id else None
        else:
            student = db.get(Student, response.profile_id)
            tutor = db.get(Tutor, post.author_profile_id) if post.author_profile_type == "tutor" and post.author_profile_id else None
        result.append({
            "response": {"id": response.id, "post_id": response.post_id, "profile_id": response.profile_id,
                "profile_type": response.profile_type, "response": response.response,
                "review_status": response.review_status, "created_at": response.created_at, "updated_at": response.updated_at},
            "post": {"id": post.id, "post_type": post.post_type, "author_name": post.author_name,
                "subjects": post.subjects, "level": post.level, "experience": post.experience,
                "availability": post.availability, "location": post.location, "fee": post.fee,
                "description": post.description, "status": post.status},
            "tutor": ({"id": tutor.id, "full_name": tutor.full_name, "email": tutor.email, "phone_number": tutor.phone_number,
                "subjects": tutor.subjects, "teaching_level": tutor.teaching_level,
                "experience_years": tutor.experience_years, "hourly_rate": tutor.hourly_rate, "bio": tutor.bio} if tutor else None),
            "student": ({"id": student.id, "full_name": student.full_name, "email": student.email, "phone_number": student.phone_number,
                "education_level": student.education_level, "subjects": student.subjects} if student else None),
        })
    return result
