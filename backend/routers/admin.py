from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.database import get_db
    from backend.dependencies import require_admin_key
    from backend.models import InterestResponse
    from backend.schemas import ResponseRead
except ModuleNotFoundError:
    import crud
    from database import get_db
    from dependencies import require_admin_key
    from models import InterestResponse
    from schemas import ResponseRead

router = APIRouter(tags=["Admin"])


@router.get("/api/admin/matches")
def list_admin_matches(
    review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected)$"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> list[dict]:
    return crud.list_admin_matches(review_status=review_status, db=db)


@router.get("/api/admin/responses", response_model=list[ResponseRead])
def list_admin_responses(
    review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> list[InterestResponse]:
    return crud.list_admin_responses(review_status=review_status, db=db, _=_)


@router.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(
    response_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> InterestResponse:
    return crud.approve_interest(response_id=response_id, db=db, _=_)


@router.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(
    response_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> InterestResponse:
    return crud.reject_interest(response_id=response_id, db=db, _=_)
