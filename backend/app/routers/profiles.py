from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..dependencies import require_demo_profile

router = APIRouter(tags=["Profiles"])


@router.get("/api/profiles/approved-matches")
def list_approved_matches(
    db: Session = Depends(get_db),
    profile: tuple[str, int] = Depends(require_demo_profile),
) -> list[dict]:
    return crud.list_approved_matches(db=db, profile=profile)
