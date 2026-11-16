from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

try:
    from backend.app from app import crud
    from backend.app.database import get_db
    from backend.app.dependencies import require_demo_mode
    from backend.app.models import Student
    from backend.app.schemas import StudentInput, StudentRead
except ModuleNotFoundError:
    from app import crud
    from app.database import get_db
    from app.dependencies import require_demo_mode
    from app.models import Student
    from app.schemas import StudentInput, StudentRead

router = APIRouter(tags=["Students"])


@router.post("/api/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentInput,
    db: Session = Depends(get_db),
    _: None = Depends(require_demo_mode),
) -> Student:
    return crud.create_student(payload=payload, db=db)


@router.get("/api/students", response_model=list[StudentRead])
def list_students(
    q: str | None = Query(default=None, max_length=120),
    subject: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> list[Student]:
    return crud.list_students(q=q, subject=subject, db=db)


@router.get("/api/students/{student_id}", response_model=StudentRead)
def get_student(student_id: int, db: Session = Depends(get_db)) -> Student:
    return crud.get_student(student_id=student_id, db=db)


@router.put("/api/students/{student_id}", response_model=StudentRead)
def update_student(
    student_id: int,
    payload: StudentInput,
    db: Session = Depends(get_db),
    _: None = Depends(require_demo_mode),
) -> Student:
    return crud.update_student(student_id=student_id, payload=payload, db=db)


@router.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_demo_mode),
) -> None:
    return crud.delete_student(student_id=student_id, db=db)
