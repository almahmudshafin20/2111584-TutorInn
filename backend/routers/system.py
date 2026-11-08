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

router = APIRouter(tags=["System"])

@router.get("/api/health")
def health() -> dict[str, str]:
    return crud.health()

@router.get("/api/subjects")
def list_subjects(db: Session = Depends(get_db)) -> list[str]:
    return crud.list_subjects(db=db)

@router.get("/api/hello")
def hello(name: str = "World") -> dict[str, str]:
    return crud.hello(name=name)
