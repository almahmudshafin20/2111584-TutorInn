from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import crud
from backend.database import get_db
from backend.dependencies import require_admin_key, require_demo_role
from backend.models import LearningPost
from backend.schemas import ConfirmationInput, LearningPostInput, LearningPostRead

router = APIRouter(prefix="/api/posts", tags=["Posts"])


@router.post("", response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: LearningPostInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    return crud.create_post(db, payload, actor)


@router.get("", response_model=list[LearningPostRead])
def list_posts(
    post_type: str | None = Query(default=None, pattern="^(tutor|student)$"),
    offset: int = Query(default=0, ge=0, le=180),
    limit: int = Query(default=20, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[LearningPost]:
    return crud.list_posts(db, post_type, offset, limit)


@router.get("/{post_id}", response_model=LearningPostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> LearningPost:
    return crud.get_post(db, post_id)


@router.put("/{post_id}", response_model=LearningPostRead)
def update_post(post_id: int, payload: LearningPostInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    return crud.update_post(db, post_id, payload, actor)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> None:
    crud.delete_post(db, post_id, actor)


@router.post("/{post_id}/confirm", response_model=LearningPostRead)
def confirm_post(post_id: int, payload: ConfirmationInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    return crud.confirm_post(db, post_id, payload, actor)


@router.post("/{post_id}/not-interested", response_model=LearningPostRead)
def mark_not_interested(post_id: int, payload: ConfirmationInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> LearningPost:
    return crud.mark_not_interested(db, post_id, payload, actor)


@router.post("/{post_id}/approve", response_model=LearningPostRead)
def approve_post(post_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> LearningPost:
    return crud.approve_post(db, post_id)


@router.post("/{post_id}/reject", response_model=LearningPostRead)
def reject_post(post_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin_key)) -> LearningPost:
    return crud.reject_post(db, post_id)
