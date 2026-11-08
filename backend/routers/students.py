from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.database import get_db
    from backend.dependencies import require_demo_role
    from backend.models import Student
    from backend.schemas import StudentInput, StudentRead
except ModuleNotFoundError:
    import crud
    from database import get_db
    from dependencies import require_demo_role
    from models import Student
    from schemas import StudentInput, StudentRead

router = APIRouter(prefix="/api/students", tags=["Students"])


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Student:
    return crud.create_student(db, payload, actor)


@router.get("", response_model=list[StudentRead])
def list_students(q: str | None = Query(default=None, max_length=120), db: Session = Depends(get_db)) -> list[Student]:
    return crud.list_students(db, q)


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: int, db: Session = Depends(get_db)) -> Student:
    return crud.get_student(db, student_id)


@router.put("/{student_id}", response_model=StudentRead)
def update_student(student_id: int, payload: StudentInput, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> Student:
    return crud.update_student(db, student_id, payload, actor)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db), actor: str = Depends(require_demo_role)) -> None:
    crud.delete_student(db, student_id, actor)
