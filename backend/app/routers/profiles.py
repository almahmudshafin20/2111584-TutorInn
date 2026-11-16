from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

try:
    from backend.app import crud
    from backend.app.database import get_db
    from backend.app.dependencies import require_demo_profile
except ModuleNotFoundError:
    from app import crud
    from app.database import get_db
    from app.dependencies import require_demo_profile

router = APIRouter(tags=["Profiles"])


@router.get("/api/profiles/approved-matches")
def list_approved_matches(
    db: Session = Depends(get_db),
    profile: tuple[str, int] = Depends(require_demo_profile),
) -> list[dict]:
    return crud.list_approved_matches(db=db, profile=profile)
