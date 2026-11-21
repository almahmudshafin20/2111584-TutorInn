from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..auth import record_activity_event
from ..dependencies import require_demo_profile
from ..models import InterestResponse, LearningPost, Student, Tutor
from ..schemas import LearningPostInput, LearningPostRead, ResponseInput, ResponseRead

router = APIRouter(tags=["Posts and Responses"])


def _record_profile_activity(db: Session, request: Request, profile: tuple[str, int], action: str, target_type: str, target_id: int) -> None:
    role, profile_id = profile
    model = Student if role == "student" else Tutor
    account_id = db.scalar(select(model.account_id).where(model.id == profile_id))
    record_activity_event(db, request, actor_account_id=account_id, actor_role=role, action=action,
                          target_type=target_type, target_id=target_id,
                          details=f"actor_profile_id={profile_id}")


@router.post("/api/posts", response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: LearningPostInput, request: Request, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    post = crud.create_post(payload=payload, db=db, profile=profile)
    _record_profile_activity(db, request, profile, "tutoring_post_created", "tutoring_post", post.id)
    return post


@router.get("/api/posts", response_model=list[LearningPostRead])
def list_posts(post_type: str | None = Query(default=None, pattern="^(tutor|student)$"),
               subject: str | None = Query(default=None, max_length=80), offset: int = Query(default=0, ge=0, le=180),
               limit: int = Query(default=20, ge=1, le=20), db: Session = Depends(get_db)) -> list[LearningPost]:
    return crud.list_posts(post_type=post_type, subject=subject, offset=offset, limit=limit, db=db)


@router.get("/api/posts/{post_id}", response_model=LearningPostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> LearningPost:
    return crud.get_post(post_id=post_id, db=db)


@router.put("/api/posts/{post_id}", response_model=LearningPostRead)
def update_post(post_id: int, payload: LearningPostInput, request: Request, db: Session = Depends(get_db),
                profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    post = crud.update_post(post_id=post_id, payload=payload, db=db, profile=profile)
    _record_profile_activity(db, request, profile, "tutoring_post_updated", "tutoring_post", post_id)
    return post


@router.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, request: Request, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> None:
    result = crud.delete_post(post_id=post_id, db=db, profile=profile)
    _record_profile_activity(db, request, profile, "tutoring_post_deleted", "tutoring_post", post_id)
    return result


@router.post("/api/posts/{post_id}/response", response_model=ResponseRead)
def set_interest_response(post_id: int, payload: ResponseInput, request: Request, db: Session = Depends(get_db),
                          profile: tuple[str, int] = Depends(require_demo_profile)) -> InterestResponse:
    response = crud.set_interest_response(post_id=post_id, payload=payload, db=db, profile=profile)
    _record_profile_activity(db, request, profile, "tutoring_request_response_updated", "tutoring_post", post_id)
    return response


@router.get("/api/responses", response_model=list[ResponseRead])
def list_my_responses(db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> list[InterestResponse]:
    return crud.list_my_responses(db=db, profile=profile)


@router.post("/api/posts/{post_id}/confirm", response_model=LearningPostRead)
def legacy_confirm(post_id: int, request: Request, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    post = crud.legacy_confirm(post_id=post_id, db=db, profile=profile)
    _record_profile_activity(db, request, profile, "tutoring_request_confirmed", "tutoring_post", post_id)
    return post


@router.post("/api/posts/{post_id}/not-interested", response_model=LearningPostRead)
def legacy_not_interested(post_id: int, request: Request, db: Session = Depends(get_db), profile: tuple[str, int] = Depends(require_demo_profile)) -> LearningPost:
    post = crud.legacy_not_interested(post_id=post_id, db=db, profile=profile)
    _record_profile_activity(db, request, profile, "tutoring_request_declined", "tutoring_post", post_id)
    return post
