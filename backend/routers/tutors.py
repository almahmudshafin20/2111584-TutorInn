from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
try:
    from backend import crud
    from backend.database import get_db
    from backend.dependencies import require_admin_key, require_demo_profile
    from backend.models import InterestResponse, LearningPost, Student, Tutor, normalize_subjects, split_legacy_subjects
    from backend.schemas import LearningPostInput, LearningPostRead, ResponseInput, ResponseRead, StudentInput, StudentRead, TutorInput, TutorRead
except ModuleNotFoundError:
    import crud
    from database import get_db
    from dependencies import require_admin_key, require_demo_profile
    from models import InterestResponse, LearningPost, Student, Tutor, normalize_subjects, split_legacy_subjects
    from schemas import LearningPostInput, LearningPostRead, ResponseInput, ResponseRead, StudentInput, StudentRead, TutorInput, TutorRead

router = APIRouter(tags=['Tutors'])

@router.post('/api/tutors', response_model=TutorRead, status_code=status.HTTP_201_CREATED)
def create_tutor(payload: TutorInput, db: Session = Depends(get_db)) -> Tutor:
    return crud.create_tutor(payload=payload, db=db)

@router.get('/api/tutors', response_model=list[TutorRead])
def list_tutors(q: str | None = Query(default=None, max_length=120), subject: str | None = Query(default=None, max_length=80),
                level: str | None = Query(default=None, max_length=80), db: Session = Depends(get_db))¶»§q«^