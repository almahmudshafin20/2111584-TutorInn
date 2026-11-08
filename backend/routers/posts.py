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

router = APIRouter(tags=["Posts and Responses"])

@router.post("/api/posts", response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: LearningPostInput, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return crud.create_post(payload=payload, db=db, profile=profile)

@router.get("/api/posts", response_model=list[LearningPostRead])
def list_posts(post_type: str | None = Query(default=None, pattern="^(tutor|student)$"),
               subject: str | None = Query(default=None, max_length=80), offset: int = Query(default=0, ge=0, le=180),
               limit: int = Query(default=20, ge=1, le=20), db: Session = Depends(get_db)) -> list[LearningPost]:
    return crud.list_posts(post_type=post_type, subject=subject, offset=offset, limit=limit, db=db)

@router.get("/api/posts/{post_id}", response_model=LearningPostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> LearningPost:
    return crud.get_post(post_id=post_id, db=db)

@router.put("/api/posts/{post_id}", response_model=LearningPostRead)
def update_post(post_id: int, payload: LearningPostInput, db: Session = Depends(get_db),
                profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return crud.update_post(post_id=post_id, payload=payload, db=db, profile=profile)

@router.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> None:
    return crud.delete_post(post_id=post_id, db=db, profile=profile)

@router.post("/api/posts/{post_id}/response", response_model=ResponseRead)
def set_interest_response(post_id: int, payload: ResponseInput, db: Session = Depends(get_db),
                          profile: tuple[str, int] = Depends(require_demo_profile)) -> InterestResponse:
    return crud.set_interest_response(post_id=post_id, payload=payload, db=db, profile=profile)

@router.get("/api/responses", response_model=list[ResponseRead])
def list_my_responses(db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> list[InterestResponse]:
    return crud.list_my_responses(db=db, profile=profile)

@router.get("/api/admin/responses", response_model=list[ResponseRead])
def list_admin_responses(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
                         db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> list[InterestResponse]:
    return crud.list_admin_responses(review_status=review_status, db=db, _=_)

@router.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(response_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> InterestResponse:
    return crud.approve_interest(response_id=response_id, db=db, _=_)

@router.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(response_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> InterestResponse:
    return crud.reject_interest(response_id=response_id, db=db, _=_)

@router.post("/api/posts/{post_id}/confirm", response_model=LearningPostRead)
def legacy_confirm(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return crud.legacy_confirm(post_id=post_id, db=db, profile=profile)

@router.post("/api/posts/{post_id}/not-interested", response_model=LearningPostRead)
def legacy_not_interested(post_id: int, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    return crud.legacy_not_interested(post_id=post_id, db=db, profile=profile)

