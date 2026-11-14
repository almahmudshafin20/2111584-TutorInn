from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.database import get_db
    from backend.dependencies import require_demo_mode
    from backend.models import Tutor
    from backend.schemas import TutorInput, TutorRead
except ModuleNotFoundError:
    import crud
    from database import get_db
    from dependencies import require_demo_mode
    from models import Tutor
    from schemas import TutorInput, TutorRead

router = APIRouter(tags=["Tutors"])


@router.post("/api/tutors", response_model=TutorRead, status_code=status.HTTP_201_CREATED)
def create_tutor(
    payload: TutorInput,
    db: Session = Depends(get_db),
    _: None = Depends(require_demo_mode),
) -> Tutor:
    return crud.create_tutor(payload=payload, db=db)


@router.get("/api/tutors", response_model=list[TutorRead])
def list_tutors(
    q: str | None = Query(default=None, max_length=120),
    subject: str | None = Query(default=None, max_length=80),
    level: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> list[Tutor]:
    return crud.list_tutors(q=q, subject=subject, level=level, db=db)


@router.get("/api/tutors/{tutor_id}", response_model=TutorRead)
def get_tutor(tutor_id: int, db: Session = Depends(get_db)) -> Tutor:
    return crud.get_tutor(tutor_id=tutor_id, db=db)


@router.put("/api/tutors/{tutor_id}", response_model=TutorRead)
def update_tutor(
    tutor_id: int,
    payload: TutorInput,
    db: Session = Depends(get_db),
    _: None = Depends(require_demo_mode),
) -> Tutor:
    return crud.update_tutor(tutor_id=tutor_id, payload=payload, db=db)


@router.delete("/api/tutors/{tutor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tutor(
    tutor_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_demo_mode),
) -> None:
    return crud.delete_tutor(tutor_id=tutor_id, db=db)
