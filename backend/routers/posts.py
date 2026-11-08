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

router = APIRouter(tags=['Posts and Responses'])

@router.post('/api/posts', response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: LearningPostInput, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return crud.create_post(payload=payload, db=db, profile=profile)

@router.get('/api/posts', response_model=list[LearningPostRead])
def list_posts(post_type: str | None = Query(default=None, pattern="^(tutor|student)$"),
               subject: str ¶»§q«^