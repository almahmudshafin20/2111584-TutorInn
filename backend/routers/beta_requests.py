from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from backend import crud
    from backend.auth import get_current_account, require_roles
    from backend.database import get_db
    from backend.models import InterestResponse, LearningPost, Student, Tutor, UserAccount
    from backend.schemas import (
        LearningPostInput, LearningPostRead, ResponseInput, ResponseRead,
        StudentRead, TutorRead,
    )
except ModuleNotFoundError:
    import crud
    from auth import get_current_account, require_roles
    from database import get_db
    from models import InterestResponse, LearningPost, Student, Tutor, UserAccount
    from schemas import LearningPostInput, LearningPostRead, ResponseInput, ResponseRead, StudentRead, TutorRead

router = APIRouter(tags=["Authenticated dashboards and requests"])


def _owned_profile(account: UserAccount, db: Session) -> Student | Tutor:
    if account.role == "student":
        profile = db.scalar(select(Student).where(Student.account_id == account.id))
    elif account.role == "tutor":
        profile = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    else:
        raise HTTPException(status_code=403, detail="This account role does not have a Student or Tutor profile.")
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active profile.")
    return profile


def _post_read(posts: list[LearningPost]) -> list[dict]:
    return [LearningPostRead.model_validate(post).model_dump() for post in posts]


def _response_read(responses: list[InterestResponse]) -> list[dict]:
    return [ResponseRead.model_validate(item).model_dump() for item in responses]


@router.get("/api/dashboard")
def read_dashboard(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> dict:
    profile = _owned_profile(account, db)
    if account.role == "student":
        own_requests = list(db.scalars(
            select(LearningPost).where(
                LearningPost.post_type == "student",
                LearningPost.author_profile_type == "student",
                LearningPost.author_profile_id == profile.id,
            ).order_by(LearningPost.id.desc())
        ).all())
        incoming = list(db.scalars(
            select(InterestResponse)
            .join(LearningPost, LearningPost.id == InterestResponse.post_id)
            .where(
                LearningPost.author_profile_type == "student",
                LearningPost.author_profile_id == profile.id,
            )
            .order_by(InterestResponse.updated_at.desc())
        ).all())
        return {
            "role": "student",
            "profile": StudentRead.model_validate(profile).model_dump(),
            "requests": _post_read(own_requests),
            "incoming_responses": _response_read(incoming),
        }

    available_requests = list(db.scalars(
        select(LearningPost).where(LearningPost.post_type == "student", LearningPost.status == "Pending")
        .order_by(LearningPost.id.desc()).limit(50)
    ).all())
    own_responses = list(db.scalars(
        select(InterestResponse).where(
            InterestResponse.profile_type == "tutor",
            InterestResponse.profile_id == profile.id,
        ).order_by(InterestResponse.updated_at.desc())
    ).all())
    return {
        "role": "tutor",
        "profile": TutorRead.model_validate(profile).model_dump(),
        "requests": _post_read(available_requests),
        "responses": _response_read(own_responses),
    }


@router.get("/api/requests", response_model=list[LearningPostRead])
def list_authenticated_requests(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> list[LearningPost]:
    statement = select(LearningPost).where(LearningPost.post_type == "student", LearningPost.status == "Pending")
    if account.role == "student":
        profile = _owned_profile(account, db)
        statement = statement.where(
            LearningPost.author_profile_type == "student",
            LearningPost.author_profile_id == profile.id,
        )
    return list(db.scalars(statement.order_by(LearningPost.id.desc()).limit(100)).all())


@router.post("/api/requests", response_model=LearningPostRead, status_code=status.HTTP_201_CREATED)
def create_authenticated_request(
    payload: LearningPostInput,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> LearningPost:
    profile = _owned_profile(account, db)
    if payload.post_type != "student":
        raise HTTPException(status_code=403, detail="Student accounts can create only Student tutoring requests.")
    return crud.create_post(payload=payload, db=db, profile=("student", profile.id))


@router.get("/api/requests/{request_id}", response_model=LearningPostRead)
def get_authenticated_request(
    request_id: int,
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> LearningPost:
    post = db.get(LearningPost, request_id)
    if post is None or post.post_type != "student":
        raise HTTPException(status_code=404, detail="Tutoring request not found.")
    if account.role == "student":
        profile = _owned_profile(account, db)
        if (post.author_profile_type, post.author_profile_id) != ("student", profile.id):
            raise HTTPException(status_code=404, detail="Tutoring request not found.")
    return post


@router.put("/api/requests/{request_id}", response_model=LearningPostRead)
def update_authenticated_request(
    request_id: int,
    payload: LearningPostInput,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> LearningPost:
    profile = _owned_profile(account, db)
    post = db.get(LearningPost, request_id)
    if post is None or (post.author_profile_type, post.author_profile_id) != ("student", profile.id):
        raise HTTPException(status_code=404, detail="Tutoring request not found.")
    if payload.post_type != "student":
        raise HTTPException(status_code=403, detail="A Student request cannot change its role or listing type.")
    return crud.update_post(post_id=request_id, payload=payload, db=db, profile=("student", profile.id))


@router.delete("/api/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_authenticated_request(
    request_id: int,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> None:
    profile = _owned_profile(account, db)
    post = db.get(LearningPost, request_id)
    if post is None or (post.author_profile_type, post.author_profile_id) != ("student", profile.id):
        raise HTTPException(status_code=404, detail="Tutoring request not found.")
    crud.delete_post(post_id=request_id, db=db, profile=("student", profile.id))


@router.post("/api/requests/{request_id}/responses", response_model=ResponseRead)
def respond_to_authenticated_request(
    request_id: int,
    payload: ResponseInput,
    account: UserAccount = Depends(require_roles("tutor")),
    db: Session = Depends(get_db),
) -> InterestResponse:
    profile = _owned_profile(account, db)
    post = db.get(LearningPost, request_id)
    if post is None or post.post_type != "student":
        raise HTTPException(status_code=404, detail="Tutoring request not found.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="This tutoring request is no longer open for responses.")
    return crud.set_interest_response(post_id=request_id, payload=payload, db=db, profile=("tutor", profile.id))


@router.get("/api/requests/{request_id}/responses", response_model=list[ResponseRead])
def list_request_responses(
    request_id: int,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> list[InterestResponse]:
    profile = _owned_profile(account, db)
    post = db.get(LearningPost, request_id)
    if post is None or (post.author_profile_type, post.author_profile_id) != ("student", profile.id):
        raise HTTPException(status_code=404, detail="Tutoring request not found.")
    return list(db.scalars(
        select(InterestResponse).where(InterestResponse.post_id == request_id)
        .order_by(InterestResponse.updated_at.desc())
    ).all())


@router.get("/api/me/responses", response_model=list[ResponseRead])
def list_own_authenticated_responses(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> list[InterestResponse]:
    profile = _owned_profile(account, db)
    return crud.list_my_responses(db=db, profile=(account.role, profile.id))


@router.post("/api/requests/{request_id}/responses/{response_id}/accept", response_model=ResponseRead)
def accept_tutor_response(
    request_id: int,
    response_id: int,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> InterestResponse:
    """Let only the owning Student accept one interested Tutor for their request."""
    profile = _owned_profile(account, db)
    post = db.scalar(
        select(LearningPost)
        .where(LearningPost.id == request_id)
        .with_for_update()
    )
    if post is None or (post.author_profile_type, post.author_profile_id) != ("student", profile.id):
        raise HTTPException(status_code=404, detail="Tutoring request not found.")
    if post.status != "Pending":
        raise HTTPException(status_code=409, detail="This tutoring request has already been resolved.")

    selected = db.scalar(select(InterestResponse).where(
        InterestResponse.id == response_id,
        InterestResponse.post_id == request_id,
        InterestResponse.profile_type == "tutor",
    ))
    if selected is None:
        raise HTTPException(status_code=404, detail="Tutor response not found.")
    if selected.response != "Interested" or selected.review_status != "Pending":
        raise HTTPException(status_code=409, detail="Only a pending Interested response can be accepted.")

    other_responses = list(db.scalars(select(InterestResponse).where(
        InterestResponse.post_id == request_id,
        InterestResponse.profile_type == "tutor",
        InterestResponse.id != response_id,
        InterestResponse.review_status == "Pending",
    )).all())
    for item in other_responses:
        if item.response == "Interested":
            item.review_status = "Rejected"

    selected.review_status = "Approved"
    post.status = "Accepted"
    post.student_confirmed = True
    post.tutor_confirmed = False
    db.commit()
    db.refresh(selected)
    return selected
