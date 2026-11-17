import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_account, hash_password, record_activity_event, record_security_event, require_roles, timestamp, verify_password
from ..database import get_db
from ..models import (AccountDeletionRequest, ContentReport, GroupLearningTask, GroupTaskAssignment, InterestResponse, LearningGroup, LearningGroupMember, LearningPost, PersonalLearningTask, RefreshSession, SecurityEvent, Student, Tutor, TutorVerification, UserAccount)
from ..schemas import (
    PasswordChangeInput, StudentPrivateRead, StudentProfileUpdate,
    TutorPrivateRead, TutorProfileUpdate, AccountDeletionRequestInput,
)

router = APIRouter(tags=["Account profiles and security"])


@router.get("/api/me/profile", response_model=StudentPrivateRead | TutorPrivateRead)
def read_my_profile(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> Student | Tutor:
    if account.role == "student":
        profile = db.scalar(select(Student).where(Student.account_id == account.id))
    else:
        profile = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active profile.")
    return profile


@router.put("/api/me/profile/student", response_model=StudentPrivateRead)
def update_my_student_profile(
    payload: StudentProfileUpdate,
    request: Request,
    account: UserAccount = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> Student:
    profile = db.scalar(select(Student).where(Student.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active Student profile.")
    profile.full_name = payload.full_name
    profile.phone_number = payload.phone_number
    profile.education_level = payload.education_level
    profile.preferred_subjects = ", ".join(payload.subjects)
    profile.subjects_json = json.dumps(payload.subjects, ensure_ascii=False)
    db.commit()
    db.refresh(profile)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="profile_updated", target_type="student_profile", target_id=profile.id)
    return profile


@router.put("/api/me/profile/tutor", response_model=TutorPrivateRead)
def update_my_tutor_profile(
    payload: TutorProfileUpdate,
    request: Request,
    account: UserAccount = Depends(require_roles("tutor")),
    db: Session = Depends(get_db),
) -> Tutor:
    profile = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    if profile is None:
        raise HTTPException(status_code=409, detail="Your account is not linked to an active Tutor profile.")
    profile.full_name = payload.full_name
    profile.phone_number = payload.phone_number
    profile.subject = payload.subjects[0]
    profile.subjects_json = json.dumps(payload.subjects, ensure_ascii=False)
    profile.teaching_level = payload.teaching_level
    profile.experience_years = payload.experience_years
    profile.hourly_rate = payload.hourly_rate
    profile.bio = payload.bio
    profile.availability = payload.availability
    db.commit()
    db.refresh(profile)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="profile_updated", target_type="tutor_profile", target_id=profile.id)
    return profile


@router.post("/api/me/password")
def change_my_password(
    payload: PasswordChangeInput,
    request: Request,
    account: UserAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if verify_password(payload.new_password, account.password_hash):
        raise HTTPException(status_code=422, detail="Choose a new password different from your current password.")

    account.password_hash = hash_password(payload.new_password)
    account.updated_at = timestamp()
    now = timestamp()
    active_sessions = list(db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == account.id,
        RefreshSession.revoked_at.is_(None),
    )).all())
    for session in active_sessions:
        session.revoked_at = now
    db.commit()
    record_security_event(db, "password_changed", request, account_id=account.id)
    record_activity_event(db, request, actor_account_id=account.id, actor_role=account.role, action="password_changed", target_type="account", target_id=account.id)
    return {"message": "Password updated. All active sessions were revoked; sign in again."}


@router.get("/api/me/deletion-request")
def read_my_deletion_request(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> dict | None:
    item = db.scalar(select(AccountDeletionRequest).where(
        AccountDeletionRequest.account_id == account.id,
        AccountDeletionRequest.status == "pending",
    ).order_by(AccountDeletionRequest.id.desc()))
    if item is None:
        return None
    return {
        "id": item.id, "status": item.status, "reason": item.reason,
        "requested_at": item.requested_at, "requested_option": item.requested_option,
        "final_option": item.final_option,
        "requested_account_action": item.requested_account_action,
        "requested_content_action": item.requested_content_action,
        "requested_content_ids": json.loads(item.requested_content_ids or "[]"),
        "requested_visibility": item.requested_visibility,
        "requested_anonymize_content": item.requested_anonymize_content,
        "final_account_action": item.final_account_action,
        "final_content_action": item.final_content_action,
        "final_content_ids": json.loads(item.final_content_ids or "[]") if item.final_content_ids else None,
        "final_visibility": item.final_visibility,
        "final_anonymize_content": item.final_anonymize_content,
    }


@router.get("/api/me/deletion-content")
def list_my_deletion_content(
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> dict:
    """List only content this account may select for deletion."""
    student = db.scalar(select(Student).where(Student.account_id == account.id))
    tutor = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    profile_id = student.id if student else (tutor.id if tutor else None)
    profile_type = "student" if student else ("tutor" if tutor else None)
    items: list[dict] = []

    if profile_id is not None:
        posts = db.scalars(select(LearningPost).where(
            LearningPost.author_profile_id == profile_id,
            LearningPost.author_profile_type == profile_type,
        ).order_by(LearningPost.id.desc())).all()
        items.extend({
            "content_type": "learning_post", "content_id": row.id,
            "label": f"Learning post: {row.subject}",
            "description": row.description[:160],
        } for row in posts)

    personal_tasks = db.scalars(select(PersonalLearningTask).where(
        PersonalLearningTask.owner_account_id == account.id,
    ).order_by(PersonalLearningTask.id.desc())).all()
    items.extend({
        "content_type": "personal_task", "content_id": row.id,
        "label": f"Personal task: {row.title}", "description": row.description[:160],
    } for row in personal_tasks)

    groups = db.scalars(select(LearningGroup).where(
        LearningGroup.owner_account_id == account.id,
    ).order_by(LearningGroup.id.desc())).all()
    group_ids = {row.id for row in groups}
    items.extend({
        "content_type": "learning_group", "content_id": row.id,
        "label": f"Learning group: {row.name}", "description": row.description[:160],
    } for row in groups)

    task_statement = select(GroupLearningTask).where(or_(
        GroupLearningTask.created_by_account_id == account.id,
        GroupLearningTask.group_id.in_(group_ids) if group_ids else False,
    )).order_by(GroupLearningTask.id.desc())
    group_tasks = db.scalars(task_statement).all()
    items.extend({
        "content_type": "group_task", "content_id": row.id,
        "label": f"Group task: {row.title}", "description": row.description[:160],
    } for row in group_tasks)

    assignments = db.execute(select(GroupTaskAssignment, GroupLearningTask).join(
        GroupLearningTask, GroupTaskAssignment.task_id == GroupLearningTask.id,
    ).where(
        GroupTaskAssignment.student_account_id == account.id,
    ).order_by(GroupTaskAssignment.id.desc())).all()
    items.extend({
        "content_type": "group_assignment", "content_id": assignment.id,
        "label": f"Group assignment: {task.title}",
        "description": "Your assignment progress in a shared learning group.",
    } for assignment, task in assignments)

    return {"items": items}


@router.post("/api/me/deletion-request", status_code=201)
def request_account_deletion(
    payload: AccountDeletionRequestInput,
    request: Request,
    account: UserAccount = Depends(require_roles("student", "tutor")),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    existing = db.scalar(select(AccountDeletionRequest).where(
        AccountDeletionRequest.account_id == account.id,
        AccountDeletionRequest.status == "pending",
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account deletion request is already awaiting Admin review.")
    now = timestamp()
    legacy_option = payload.deletion_option or "complete"
    content_action = payload.content_action or ("retain_all" if legacy_option == "anonymize" else "delete_all")
    selected_content = [item.model_dump() for item in payload.selected_content]
    if content_action == "delete_selected" and not selected_content:
        raise HTTPException(status_code=422, detail="Select at least one content item to delete.")
    if content_action != "delete_selected" and selected_content:
        raise HTTPException(status_code=422, detail="Selected content is only valid with the selected-content option.")
    selection_keys = [(item["content_type"], item["content_id"]) for item in selected_content]
    if len(selection_keys) != len(set(selection_keys)):
        raise HTTPException(status_code=422, detail="A content item can only be selected once.")
    if selected_content:
        student = db.scalar(select(Student).where(Student.account_id == account.id))
        tutor = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
        profile_id = student.id if student else (tutor.id if tutor else None)
        profile_type = "student" if student else ("tutor" if tutor else None)
        owned_group_ids = set(db.scalars(select(LearningGroup.id).where(
            LearningGroup.owner_account_id == account.id,
        )).all())
        for selected in selected_content:
            kind, content_id = selected["content_type"], selected["content_id"]
            if kind == "learning_post":
                owned = profile_id is not None and db.scalar(select(LearningPost.id).where(
                    LearningPost.id == content_id,
                    LearningPost.author_profile_id == profile_id,
                    LearningPost.author_profile_type == profile_type,
                )) is not None
            elif kind == "personal_task":
                owned = db.scalar(select(PersonalLearningTask.id).where(
                    PersonalLearningTask.id == content_id,
                    PersonalLearningTask.owner_account_id == account.id,
                )) is not None
            elif kind == "learning_group":
                owned = content_id in owned_group_ids
            elif kind == "group_task":
                owned = db.scalar(select(GroupLearningTask.id).where(
                    GroupLearningTask.id == content_id,
                    (GroupLearningTask.created_by_account_id == account.id) |
                    (GroupLearningTask.group_id.in_(owned_group_ids) if owned_group_ids else False),
                )) is not None
            else:
                owned = db.scalar(select(GroupTaskAssignment.id).where(
                    GroupTaskAssignment.id == content_id,
                    GroupTaskAssignment.student_account_id == account.id,
                )) is not None
            if not owned:
                raise HTTPException(status_code=422, detail="One or more selected content items do not belong to your account.")
    item = AccountDeletionRequest(
        account_id=account.id, account_email=account.email, account_role=account.role,
        reason=payload.reason.strip(), requested_option=legacy_option, status="pending", requested_at=now,
        requested_account_action="delete_account", requested_content_action=content_action,
        requested_content_ids=json.dumps(selected_content, separators=(",", ":")),
        requested_visibility=payload.visibility,
        requested_anonymize_content=payload.anonymize_content,
    )
    db.add(item)
    account.status = "deletion_pending"
    account.updated_at = now
    db.query(RefreshSession).filter(
        RefreshSession.account_id == account.id, RefreshSession.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account deletion request is already awaiting Admin review.") from exc
    db.refresh(item)
    record_security_event(
        db, "account_deletion_requested", request, account_id=account.id,
        attempted_email=account.email, details=f"deletion_request_id={item.id}; role={account.role}",
    )
    return {"id": item.id, "status": item.status, "requested_at": item.requested_at,
            "requested_option": item.requested_option, "message": "Your account is now inactive while an Admin reviews your deletion request."}
