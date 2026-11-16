import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import crud
from ..auth import record_security_event, require_roles, timestamp
from ..database import get_db
from ..models import (
    GroupLearningTask, GroupTaskAssignment, InterestResponse, LearningGroup,
    LearningGroupMember, LearningPost, PersonalLearningTask, RefreshSession,
    SecurityEvent, Student, Tutor, TutorVerification, UserAccount,
)
from ..schemas import ResponseRead

router = APIRouter(tags=["Admin"])


def _admin(account: UserAccount = Depends(require_roles("admin"))) -> UserAccount:
    return account


def _audit(db: Session, request: Request, actor: UserAccount, action: str, target: str, reason: str = "") -> None:
    record_security_event(
        db, "admin_" + action, request, account_id=actor.id,
        attempted_email=target[:255],
        details=(f"target={target}; reason={reason.strip()}" if reason else f"target={target}")[:2000],
    )


def _account_payload(account: UserAccount, db: Session) -> dict:
    student = db.scalar(select(Student).where(Student.account_id == account.id))
    tutor = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    profile = None
    if student:
        profile = {"id": student.id, "full_name": student.full_name, "education_level": student.education_level, "subjects": student.subjects}
    elif tutor:
        verification = db.scalar(select(TutorVerification).where(TutorVerification.tutor_id == tutor.id))
        profile = {
            "id": tutor.id, "full_name": tutor.full_name, "subjects": tutor.subjects,
            "teaching_level": tutor.teaching_level, "experience_years": tutor.experience_years,
            "verification_status": verification.status if verification else "pending",
        }
    return {"id": account.id, "email": account.email, "role": account.role, "status": account.status,
            "created_at": account.created_at, "updated_at": account.updated_at, "profile": profile}


def _csv_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


@router.get("/api/admin/overview")
def admin_overview(db: Session = Depends(get_db), _: UserAccount = Depends(_admin)) -> dict:
    count = lambda model: int(db.scalar(select(func.count()).select_from(model)) or 0)
    return {
        "students": count(Student), "tutors": count(Tutor), "tutoring_requests": count(LearningPost),
        "total_accounts": count(UserAccount),
        "active_accounts": int(db.scalar(select(func.count()).select_from(UserAccount).where(UserAccount.status == "active")) or 0),
        "banned_accounts": int(db.scalar(select(func.count()).select_from(UserAccount).where(UserAccount.status == "banned")) or 0),
        "suspended_accounts": int(db.scalar(select(func.count()).select_from(UserAccount).where(UserAccount.status == "suspended")) or 0),
        "pending_tutor_reviews": int(db.scalar(select(func.count()).select_from(Tutor).outerjoin(TutorVerification).where(
            or_(TutorVerification.id.is_(None), TutorVerification.status == "pending")
        )) or 0),
    }


@router.get("/api/admin/users")
def admin_users(
    role: str | None = Query(default=None, pattern="^(student|tutor|admin)$"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|banned|suspended)$"),
    q: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(_admin),
) -> dict:
    statement = select(UserAccount)
    if role:
        statement = statement.where(UserAccount.role == role)
    if status_filter:
        statement = statement.where(UserAccount.status == status_filter)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(UserAccount.email.ilike(needle))
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(UserAccount.created_at.desc(), UserAccount.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [_account_payload(row, db) for row in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/users/{account_id}")
def admin_user_detail(account_id: int, request: Request, db: Session = Depends(get_db),
                      actor: UserAccount = Depends(_admin)) -> dict:
    target = db.get(UserAccount, account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    _audit(db, request, actor, "user_inspected", str(target.id))
    activity = db.scalars(select(SecurityEvent).where(
        or_(SecurityEvent.account_id == target.id, SecurityEvent.attempted_email == target.email)
    ).order_by(SecurityEvent.created_at.desc()).limit(20)).all()
    return {**_account_payload(target, db), "recent_activity": [
        {"event_type": item.event_type, "created_at": item.created_at, "details": item.details}
        for item in activity
    ]}


@router.patch("/api/admin/users/{account_id}/status")
def update_user_status(
    account_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    actor: UserAccount = Depends(_admin),
) -> dict:
    status_value = payload.get("status")
    reason = str(payload.get("reason", "")).strip()
    if status_value not in {"active", "banned", "suspended"}:
        raise HTTPException(status_code=422, detail="Status must be active, banned or suspended.")
    if len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Provide a moderation reason between 5 and 500 characters.")
    target = db.get(UserAccount, account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    if target.id == actor.id or target.role == "admin":
        raise HTTPException(status_code=409, detail="Admin accounts and your own account cannot be moderated here.")
    previous = target.status
    target.status = status_value
    target.updated_at = timestamp()
    if status_value != "active":
        sessions = db.scalars(select(RefreshSession).where(
            RefreshSession.account_id == target.id, RefreshSession.revoked_at.is_(None)
        )).all()
        now = timestamp()
        for session in sessions:
            session.revoked_at = now
    db.commit()
    _audit(db, request, actor, "account_status_changed", f"{target.id}:{target.email}",
           f"{previous} -> {status_value}; {reason}")
    return _account_payload(target, db)


@router.post("/api/admin/users/bulk-status")
def bulk_user_status(payload: dict, request: Request, db: Session = Depends(get_db),
                     actor: UserAccount = Depends(_admin)) -> dict:
    ids = payload.get("account_ids")
    status_value = payload.get("status")
    reason = str(payload.get("reason", "")).strip()
    if not isinstance(ids, list) or not ids or len(ids) > 50 or any(type(i) is not int for i in ids) or len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Select between 1 and 50 unique account IDs.")
    if status_value not in {"active", "banned", "suspended"} or len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Choose a valid status and provide a moderation reason.")
    results = []
    for account_id in ids:
        target = db.get(UserAccount, account_id)
        if target is None:
            results.append({"account_id": account_id, "success": False, "error": "Account not found."})
            continue
        if target.id == actor.id or target.role == "admin":
            results.append({"account_id": account_id, "success": False, "error": "Admin accounts cannot be bulk moderated."})
            continue
        target.status = status_value
        target.updated_at = timestamp()
        if status_value != "active":
            for session in db.scalars(select(RefreshSession).where(
                RefreshSession.account_id == target.id, RefreshSession.revoked_at.is_(None)
            )).all():
                session.revoked_at = timestamp()
        results.append({"account_id": account_id, "success": True})
    db.commit()
    for result in results:
        if result["success"]:
            _audit(db, request, actor, "bulk_account_status_changed", str(result["account_id"]),
                   f"{status_value}; {reason}")
    return {"results": results, "succeeded": sum(item["success"] for item in results),
            "failed": sum(not item["success"] for item in results)}


@router.get("/api/admin/tutors")
def admin_tutors(
    verification_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    q: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(_admin),
) -> dict:
    statement = select(Tutor, TutorVerification).outerjoin(TutorVerification, TutorVerification.tutor_id == Tutor.id)
    if verification_status == "pending":
        statement = statement.where(or_(TutorVerification.id.is_(None), TutorVerification.status == "pending"))
    elif verification_status:
        statement = statement.where(TutorVerification.status == verification_status)
    if q.strip():
        needle = "%" + q.strip() + "%"
        statement = statement.where(or_(Tutor.full_name.ilike(needle), Tutor.email.ilike(needle)))
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.execute(statement.order_by(Tutor.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": tutor.id, "full_name": tutor.full_name, "email": tutor.email, "phone_number": tutor.phone_number,
        "subjects": tutor.subjects, "teaching_level": tutor.teaching_level, "experience_years": tutor.experience_years,
        "hourly_rate": tutor.hourly_rate, "bio": tutor.bio,
        "verification_status": verification.status if verification else "pending",
        "reviewed_at": verification.reviewed_at if verification else None,
        "review_note": verification.review_note if verification else "",
    } for tutor, verification in rows], "total": total, "offset": offset, "limit": limit}


@router.patch("/api/admin/tutors/{tutor_id}/verification")
def review_tutor(tutor_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                 actor: UserAccount = Depends(_admin)) -> dict:
    status_value = payload.get("status")
    note = str(payload.get("note", "")).strip()
    if status_value not in {"approved", "rejected", "pending"} or len(note) > 1000:
        raise HTTPException(status_code=422, detail="Choose pending, approved or rejected and a note up to 1000 characters.")
    tutor = db.get(Tutor, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor profile not found.")
    verification = db.scalar(select(TutorVerification).where(TutorVerification.tutor_id == tutor_id))
    if verification is None:
        verification = TutorVerification(tutor_id=tutor_id, status=status_value)
        db.add(verification)
    verification.status = status_value
    verification.reviewer_account_id = actor.id
    verification.reviewed_at = timestamp()
    verification.review_note = note
    db.commit()
    _audit(db, request, actor, "tutor_verification_changed", str(tutor_id), f"{status_value}; {note}")
    return {"tutor_id": tutor_id, "status": verification.status, "reviewed_at": verification.reviewed_at,
            "reviewer_account_id": actor.id, "note": verification.review_note}


@router.get("/api/admin/requests")
def admin_requests(
    status_filter: str | None = Query(default=None, alias="status", max_length=20),
    q: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(_admin),
) -> dict:
    statement = select(LearningPost)
    if status_filter:
        statement = statement.where(LearningPost.status == status_filter)
    if q.strip():
        needle = "%" + q.strip() + "%"
        statement = statement.where(or_(LearningPost.author_name.ilike(needle), LearningPost.subject.ilike(needle)))
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(LearningPost.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": row.id, "type": row.post_type, "author": row.author_name, "subjects": row.subjects,
        "level": row.level, "status": row.status, "created_at": None,
    } for row in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/activity")
def admin_activity(
    event_type: str | None = Query(default=None, max_length=64),
    q: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(_admin),
) -> dict:
    statement = select(SecurityEvent)
    if event_type:
        statement = statement.where(SecurityEvent.event_type == event_type)
    if q.strip():
        needle = "%" + q.strip() + "%"
        statement = statement.where(or_(SecurityEvent.event_type.ilike(needle),
            SecurityEvent.attempted_email.ilike(needle), SecurityEvent.details.ilike(needle)))
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": row.id, "event_type": row.event_type, "account_id": row.account_id,
        "target": row.attempted_email, "ip_address": row.ip_address,
        "created_at": row.created_at, "details": row.details,
    } for row in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/security")
def admin_security(db: Session = Depends(get_db), _: UserAccount = Depends(_admin)) -> dict:
    events = db.scalars(select(SecurityEvent).where(
        SecurityEvent.event_type.in_(["login_failed", "login_locked", "refresh_token_reuse", "access_denied",
                                      "blocked_inactive_account", "admin_bootstrap_denied"])
    ).order_by(SecurityEvent.created_at.desc()).limit(100)).all()
    return {"incident_count": len(events), "events": [{
        "id": item.id, "event_type": item.event_type, "account_id": item.account_id,
        "ip_address": item.ip_address, "created_at": item.created_at,
    } for item in events]}


@router.delete("/api/admin/tasks/bulk")
def bulk_delete_personal_tasks(payload: dict, request: Request, db: Session = Depends(get_db),
                               actor: UserAccount = Depends(_admin)) -> dict:
    ids = payload.get("task_ids")
    reason = str(payload.get("reason", "")).strip()
    if not isinstance(ids, list) or not ids or len(ids) > 50 or any(type(i) is not int for i in ids) or len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Select between 1 and 50 unique task IDs.")
    if len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Provide a deletion reason between 5 and 500 characters.")
    results = []
    for task_id in ids:
        task = db.get(PersonalLearningTask, task_id)
        if task is None:
            results.append({"task_id": task_id, "success": False, "error": "Task not found."})
        else:
            db.delete(task)
            results.append({"task_id": task_id, "success": True})
    db.commit()
    for result in results:
        if result["success"]:
            _audit(db, request, actor, "personal_task_deleted", str(result["task_id"]), reason)
    return {"results": results, "succeeded": sum(item["success"] for item in results),
            "failed": sum(not item["success"] for item in results)}


@router.delete("/api/admin/groups/{group_id}")
def admin_delete_group(group_id: int, request: Request, db: Session = Depends(get_db),
                       actor: UserAccount = Depends(_admin)) -> dict:
    group = db.get(LearningGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Learning group not found.")
    task_ids = list(db.scalars(select(GroupLearningTask.id).where(GroupLearningTask.group_id == group_id)).all())
    member_count = int(db.scalar(select(func.count()).select_from(LearningGroupMember).where(LearningGroupMember.group_id == group_id)) or 0)
    assignment_count = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).join(
        GroupLearningTask, GroupTaskAssignment.task_id == GroupLearningTask.id
    ).where(GroupLearningTask.group_id == group_id)) or 0)
    for task_id in task_ids:
        db.query(GroupTaskAssignment).filter(GroupTaskAssignment.task_id == task_id).delete(synchronize_session=False)
    db.query(GroupLearningTask).filter(GroupLearningTask.group_id == group_id).delete(synchronize_session=False)
    db.query(LearningGroupMember).filter(LearningGroupMember.group_id == group_id).delete(synchronize_session=False)
    db.delete(group)
    db.commit()
    _audit(db, request, actor, "learning_group_deleted", str(group_id),
           f"name={group.name}; members={member_count}; tasks={len(task_ids)}; assignments={assignment_count}")
    return {"deleted": True, "group_id": group_id, "members_removed": member_count,
            "tasks_removed": len(task_ids), "assignments_removed": assignment_count}


@router.get("/api/admin/export/{kind}")
def export_admin_data(kind: str, db: Session = Depends(get_db), _: UserAccount = Depends(_admin)) -> StreamingResponse:
    if kind not in {"users", "tasks", "activity"}:
        raise HTTPException(status_code=404, detail="Supported exports are users, tasks and activity.")
    output = io.StringIO()
    writer = csv.writer(output)
    if kind == "users":
        writer.writerow(["account_id", "email", "role", "status", "created_at"])
        rows = db.scalars(select(UserAccount).order_by(UserAccount.id.desc()).limit(5000)).all()
        for row in rows:
            writer.writerow([row.id, _csv_cell(row.email), row.role, row.status, row.created_at])
    elif kind == "tasks":
        writer.writerow(["task_id", "owner_account_id", "title", "category", "due_date", "completed", "created_at"])
        rows = db.scalars(select(PersonalLearningTask).order_by(PersonalLearningTask.id.desc()).limit(5000)).all()
        for row in rows:
            writer.writerow([row.id, row.owner_account_id, _csv_cell(row.title), _csv_cell(row.category),
                             row.due_date.isoformat() if row.due_date else "", row.completed, row.created_at])
    else:
        writer.writerow(["event_id", "event_type", "account_id", "target", "ip_address", "created_at", "details"])
        rows = db.scalars(select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(5000)).all()
        for row in rows:
            writer.writerow([row.id, row.event_type, row.account_id, _csv_cell(row.attempted_email),
                             row.ip_address, row.created_at, _csv_cell(row.details)])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="tutorinn-{kind}.csv"',
                 "Cache-Control": "no-store"})


# Retained legacy match-review routes now require the authenticated Admin role.
@router.get("/api/admin/matches")
def list_admin_matches(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected)$"),
                       db: Session = Depends(get_db), _: UserAccount = Depends(_admin)) -> list[dict]:
    return crud.list_admin_matches(review_status=review_status, db=db)


@router.get("/api/admin/responses", response_model=list[ResponseRead])
def list_admin_responses(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
                         db: Session = Depends(get_db), _: UserAccount = Depends(_admin)) -> list[InterestResponse]:
    return crud.list_admin_responses(review_status=review_status, db=db, _=_)


@router.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(response_id: int, db: Session = Depends(get_db),
                     _: UserAccount = Depends(_admin)) -> InterestResponse:
    return crud.approve_interest(response_id=response_id, db=db, _=_)


@router.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(response_id: int, db: Session = Depends(get_db),
                    _: UserAccount = Depends(_admin)) -> InterestResponse:
    return crud.reject_interest(response_id=response_id, db=db, _=_)
