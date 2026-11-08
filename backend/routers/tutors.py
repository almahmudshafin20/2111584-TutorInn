from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.database import get_db
    from backend.dependencies import require_demo_role
    from backend.models import Tutor
    from backend.schemas import TutorInput, TutorRead
except ModuleNotFoundError:
    import crud
    from database import get_db
    from dependencies import require_demo_role
    from models import Tutor
    from schemas import TutorInput, TutorRead

router = APIRouter(prefix="/api/tutors", tags=["Tutors"])


@router.post("", response_model=TutorRead, status_code=status.HTTP_201_CREATED)
def create_tutor(payload: TutorInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Tutor:
    return crud.create_tutor(db, payload, actor)


@router.get("", response_model=list[TutorRead])
def list_tutors(
    q: str | None = Query(default=None, max_length=120),
    subject: str | None = Query(default=None, max_length=120),
    level: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> list[Tutor]:
    return crud.list_tutors(db, q, subject, level)


@router.get("/{tutor_id}", response_model=TutorRead)
def get_tutor(tutor_id: int, db: Session = Depends(get_db)) -> Tutor:
    return crud.get_tutor(db, tutor_id)


@router.put("/{tutor_id}", response_model=TutorRead)
def update_tutor(tutor_id: int, payload: TutorInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Tutor:
    return crud.update_tutor(db, tutor_id, payload, actor)


@router.delete("/{tutor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tutor(tutor_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> None:
    crud.delete_tutor(db, tutor_id, actor)
