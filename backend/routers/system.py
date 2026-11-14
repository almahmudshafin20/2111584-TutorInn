from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.database import get_db
except ModuleNotFoundError:
    import crud
    from database import get_db

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
