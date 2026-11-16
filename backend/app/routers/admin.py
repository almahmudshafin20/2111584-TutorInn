import csv
import io
import os
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import String, cast, func, or_, select
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


ADMIN_PERMISSION_MATRIX: dict[str, frozenset[str]] = {
    "view_dashboard": frozenset({"admin"}),
    "view_users": frozenset({"admin"}),
    "manage_accounts": frozenset({"admin"}),
    "manage_admin_roles": frozenset({"admin"}),
    "view_tutors": frozenset({"admin"}),
    "manage_tutor_verification": frozenset({"admin"}),
    "view_requests": frozenset({"admin"}),
    "view_activity": frozenset({"admin"}),
    "view_security": frozenset({"admin"}),
    "view_tasks": frozenset({"admin"}),
    "delete_tasks": frozenset({"admin"}),
    "view_groups": frozenset({"admin"}),
    "delete_groups": frozenset({"admin"}),
    "export_data": frozenset({"admin"}),
    "manage_retention": frozenset({"admin"}),
    "moderate_learning": frozenset({"admin"}),
}


def require_admin_permission(permission: str):
    if permission not in ADMIN_PERMISSION_MATRIX:
        raise RuntimeError(f"Unknown Admin permission: {permission}")

    def dependency(account: UserAccount = Depends(require_roles("admin"))) -> UserAccount:
        if account.role not in ADMIN_PERMISSION_MATRIX[permission]:
            raise HTTPException(status_code=403, detail=f"Admin permission required: {permission}.")
        return account

    return dependency


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


def _created_range(statement, column, created_from: date | None, created_to: date | None):
    if created_from:
        statement = statement.where(column >= created_from.isoformat())
    if created_to:
        statement = statement.where(column < (created_to + timedelta(days=1)).isoformat())
    return statement


@router.get("/api/admin/overview")
def admin_overview(db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_dashboard"))) -> dict:
    count = lambda model: int(db.scalar(select(func.count()).select_from(model)) or 0)
    now = datetime.now(timezone.utc)
    current_start = (now - timedelta(days=7)).isoformat()
    previous_start = (now - timedelta(days=14)).isoformat()
    def period_count(model, start: str, end: str | None = None, role: str | None = None) -> int:
        statement = select(func.count()).select_from(model).where(model.created_at >= start)
        if end is not None:
            statement = statement.where(model.created_at < end)
        if role is not None:
            statement = statement.where(UserAccount.role == role)
        return int(db.scalar(statement) or 0)
    trends = {}
    for key, model, role in (("students", UserAccount, "student"), ("tutors", UserAccount, "tutor"),
                             ("tutoring_requests", LearningPost, None)):
        current = period_count(model, current_start, role=role)
        previous = period_count(model, previous_start, current_start, role=role)
        trends[key] = {"last_7_days": current, "previous_7_days": previous, "change": current - previous}
    return {
        "students": count(Student), "tutors": count(Tutor), "tutoring_requests": count(LearningPost),
        "trends": trends,
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
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_users")),
) -> dict:
    statement = select(UserAccount).outerjoin(Student, Student.account_id == UserAccount.id).outerjoin(Tutor, Tutor.account_id == UserAccount.id)
    if role:
        statement = statement.where(UserAccount.role == role)
    if status_filter:
        statement = statement.where(UserAccount.status == status_filter)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(UserAccount.email.ilike(needle), Student.full_name.ilike(needle), Tutor.full_name.ilike(needle)))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, UserAccount.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(UserAccount.created_at.desc(), UserAccount.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [_account_payload(row, db) for row in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/users/{account_id}")
def admin_user_detail(account_id: int, request: Request, db: Session = Depends(get_db),
                      actor: UserAccount = Depends(require_admin_permission("view_users"))) -> dict:
    target = db.get(UserAccount, account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    _audit(db, request, actor, "user_inspected", str(target.id))
    activity = db.scalars(select(SecurityEvent).where(
        or_(
            SecurityEvent.account_id == target.id,
            SecurityEvent.attempted_email == target.email,
            SecurityEvent.details.ilike(f"%target={target.id}%"),
        )
    ).order_by(SecurityEvent.created_at.desc()).limit(30)).all()
    sessions = db.scalars(select(RefreshSession).where(
        RefreshSession.account_id == target.id,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > timestamp(),
    ).order_by(RefreshSession.last_used_at.desc()).limit(50)).all()
    return {**_account_payload(target, db), "recent_activity": [
        {"event_type": item.event_type, "created_at": item.created_at, "details": item.details}
        for item in activity
    ], "active_sessions": [{
        "id": item.id, "created_at": item.created_at, "last_used_at": item.last_used_at,
        "expires_at": item.expires_at, "user_agent": item.user_agent, "ip_address": item.ip_address,
    } for item in sessions]}


@router.post("/api/admin/users/{account_id}/admin-role")
def grant_admin_role(account_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                     actor: UserAccount = Depends(require_admin_permission("manage_admin_roles"))) -> dict:
    reason = str(payload.get("reason", "")).strip()
    if len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Provide a reason between 5 and 500 characters.")
    target = db.get(UserAccount, account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    if target.role == "admin":
        raise HTTPException(status_code=409, detail="This account already has Admin access.")
    previous_role = target.role
    target.role = "admin"
    db.query(RefreshSession).filter(RefreshSession.account_id == target.id,
        RefreshSession.revoked_at.is_(None)).update({"revoked_at": timestamp()}, synchronize_session=False)
    db.commit()
    _audit(db, request, actor, "admin_role_granted", str(target.id),
           f"previous_role={previous_role}; reason={reason}")
    db.refresh(target)
    return _account_payload(target, db)


@router.delete("/api/admin/users/{account_id}/admin-role")
def revoke_admin_role(account_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                      actor: UserAccount = Depends(require_admin_permission("manage_admin_roles"))) -> dict:
    reason = str(payload.get("reason", "")).strip()
    if len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Provide a reason between 5 and 500 characters.")
    target = db.get(UserAccount, account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    if target.role != "admin":
        raise HTTPException(status_code=409, detail="This account does not have Admin access.")
    active_admins = int(db.scalar(select(func.count()).select_from(UserAccount).where(
        UserAccount.role == "admin", UserAccount.status == "active"
    )) or 0)
    if active_admins <= 1 and target.status == "active":
        raise HTTPException(status_code=409, detail="The last active Admin cannot be demoted.")
    if target.id == actor.id:
        raise HTTPException(status_code=403, detail="You cannot revoke your own Admin access.")
    grant = db.scalar(select(SecurityEvent).where(
        SecurityEvent.event_type == "admin_admin_role_granted",
        SecurityEvent.attempted_email == str(target.id),
    ).order_by(SecurityEvent.id.desc()).limit(1))
    if grant is None or "previous_role=" not in grant.details:
        raise HTTPException(status_code=409, detail="This Admin account has no reversible role-grant record.")
    previous_role = grant.details.split("previous_role=", 1)[1].split(";", 1)[0].strip()
    if previous_role not in {"student", "tutor"}:
        raise HTTPException(status_code=409, detail="The previous account role cannot be safely restored.")
    target.role = previous_role
    db.query(RefreshSession).filter(RefreshSession.account_id == target.id,
        RefreshSession.revoked_at.is_(None)).update({"revoked_at": timestamp()}, synchronize_session=False)
    db.commit()
    _audit(db, request, actor, "admin_role_revoked", str(target.id),
           f"restored_role={previous_role}; reason={reason}")
    db.refresh(target)
    return _account_payload(target, db)


@router.delete("/api/admin/users/{account_id}/sessions/{session_id}")
def revoke_account_session(account_id: int, session_id: int, request: Request,
                           db: Session = Depends(get_db),
                           actor: UserAccount = Depends(require_admin_permission("manage_accounts"))) -> dict:
    target = db.get(UserAccount, account_id)
    session = db.get(RefreshSession, session_id)
    if target is None or session is None or session.account_id != account_id:
        raise HTTPException(status_code=404, detail="Account session not found.")
    if session.revoked_at is not None:
        raise HTTPException(status_code=409, detail="This session has already been revoked.")
    session.revoked_at = timestamp()
    db.commit()
    _audit(db, request, actor, "account_session_revoked", str(account_id),
           f"session_id={session_id}; reason=Admin security investigation")
    return {"revoked": True, "session_id": session_id}


@router.patch("/api/admin/users/{account_id}/status")
def update_user_status(
    account_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    actor: UserAccount = Depends(require_admin_permission("manage_accounts")),
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
                     actor: UserAccount = Depends(require_admin_permission("manage_accounts"))) -> dict:
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
    account_status: str | None = Query(default=None, pattern="^(active|banned|suspended)$"),
    q: str = Query(default="", max_length=120),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_tutors")),
) -> dict:
    statement = select(Tutor, TutorVerification, UserAccount).outerjoin(TutorVerification, TutorVerification.tutor_id == Tutor.id).outerjoin(UserAccount, UserAccount.id == Tutor.account_id)
    if verification_status == "pending":
        statement = statement.where(or_(TutorVerification.id.is_(None), TutorVerification.status == "pending"))
    elif verification_status:
        statement = statement.where(TutorVerification.status == verification_status)
    if account_status:
        statement = statement.where(UserAccount.status == account_status)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(Tutor.full_name.ilike(needle), Tutor.email.ilike(needle), UserAccount.email.ilike(needle)))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, UserAccount.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.execute(statement.order_by(Tutor.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": tutor.id, "account_id": account.id if account else None, "account_status": account.status if account else "legacy", "full_name": tutor.full_name, "email": tutor.email, "phone_number": tutor.phone_number,
        "subjects": tutor.subjects, "teaching_level": tutor.teaching_level, "experience_years": tutor.experience_years,
        "hourly_rate": tutor.hourly_rate, "bio": tutor.bio,
        "verification_status": verification.status if verification else "pending",
        "reviewed_at": verification.reviewed_at if verification else None,
        "review_note": verification.review_note if verification else "",
    } for tutor, verification, account in rows], "total": total, "offset": offset, "limit": limit}


@router.patch("/api/admin/tutors/{tutor_id}/verification")
def review_tutor(tutor_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                 actor: UserAccount = Depends(require_admin_permission("manage_tutor_verification"))) -> dict:
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
    owner_account_id: int | None = Query(default=None, ge=1),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_requests")),
) -> dict:
    statement = select(LearningPost)
    if status_filter:
        statement = statement.where(LearningPost.status == status_filter)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(LearningPost.author_name.ilike(needle), LearningPost.subject.ilike(needle)))
    if owner_account_id:
        student_profiles = select(Student.id).where(Student.account_id == owner_account_id)
        tutor_profiles = select(Tutor.id).where(Tutor.account_id == owner_account_id)
        statement = statement.where(or_(
            (LearningPost.author_profile_type == "student") & LearningPost.author_profile_id.in_(student_profiles),
            (LearningPost.author_profile_type == "tutor") & LearningPost.author_profile_id.in_(tutor_profiles),
        ))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, LearningPost.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(LearningPost.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": row.id, "type": row.post_type, "author": row.author_name, "subjects": row.subjects,
        "level": row.level, "status": row.status, "created_at": row.created_at,
    } for row in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/activity")
def admin_activity(
    event_type: str | None = Query(default=None, max_length=64),
    q: str = Query(default="", max_length=120),
    account_id: int | None = Query(default=None, ge=1),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_activity")),
) -> dict:
    statement = select(SecurityEvent)
    if event_type:
        statement = statement.where(SecurityEvent.event_type == event_type)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(SecurityEvent.event_type.ilike(needle),
            SecurityEvent.attempted_email.ilike(needle), SecurityEvent.details.ilike(needle),
            SecurityEvent.ip_address.ilike(needle),
            cast(SecurityEvent.account_id, String).ilike(needle)))
    if account_id:
        statement = statement.where(SecurityEvent.account_id == account_id)
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, SecurityEvent.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": row.id, "event_type": row.event_type, "account_id": row.account_id,
        "target": row.attempted_email, "ip_address": row.ip_address,
        "created_at": row.created_at, "details": row.details,
    } for row in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/security")
def admin_security(
    hours: int = Query(default=24, ge=1, le=720),
    min_events: int = Query(default=3, ge=1, le=1000),
    event_type: str | None = Query(default=None, max_length=64),
    q: str = Query(default="", max_length=120),
    account_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_security")),
) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    suspicious_types = [
        "login_failed", "login_locked", "login_succeeded", "refresh_token_reuse", "refresh_token_rejected",
        "refresh_token_expired", "access_denied", "access_token_rejected", "auth_rate_limited",
        "blocked_inactive_account", "admin_bootstrap_denied", "registration_succeeded",
        "refresh_succeeded", "session_revoked", "password_changed", "admin_account_banned", "admin_account_unbanned", "admin_account_suspended", "admin_account_reactivated",
    ]
    scoped = SecurityEvent.created_at >= cutoff
    statement = select(SecurityEvent).where(scoped, SecurityEvent.event_type.in_(suspicious_types))
    if event_type:
        statement = statement.where(SecurityEvent.event_type == event_type)
    if account_id:
        statement = statement.where(SecurityEvent.account_id == account_id)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(
            SecurityEvent.event_type.ilike(needle),
            SecurityEvent.attempted_email.ilike(needle),
            SecurityEvent.ip_address.ilike(needle),
            SecurityEvent.user_agent.ilike(needle),
            SecurityEvent.details.ilike(needle),
            cast(SecurityEvent.account_id, String).ilike(needle),
        ))
    events = db.scalars(statement.order_by(
        SecurityEvent.created_at.desc(), SecurityEvent.id.desc()
    ).limit(100)).all()
    failure_types = [
        "login_failed", "login_locked", "refresh_token_reuse", "refresh_token_rejected",
        "refresh_token_expired", "access_denied", "access_token_rejected", "auth_rate_limited",
        "blocked_inactive_account", "admin_bootstrap_denied",
    ]
    summary_scope = (scoped, SecurityEvent.event_type.in_(failure_types))
    ip_summaries = db.execute(select(
        SecurityEvent.ip_address, func.count(SecurityEvent.id), func.max(SecurityEvent.created_at)
    ).where(*summary_scope, SecurityEvent.ip_address != "").group_by(SecurityEvent.ip_address)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()
    account_summaries = db.execute(select(
        SecurityEvent.account_id, UserAccount.email, UserAccount.status,
        func.count(SecurityEvent.id), func.max(SecurityEvent.created_at),
    ).join(UserAccount, UserAccount.id == SecurityEvent.account_id)
     .where(*summary_scope, SecurityEvent.account_id.is_not(None))
     .group_by(SecurityEvent.account_id, UserAccount.email, UserAccount.status)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()
    attempted_summaries = db.execute(select(
        SecurityEvent.attempted_email, func.count(SecurityEvent.id), func.max(SecurityEvent.created_at)
    ).where(*summary_scope, SecurityEvent.account_id.is_(None), SecurityEvent.attempted_email != "")
     .group_by(SecurityEvent.attempted_email)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()
    return {
        "hours": hours, "min_events": min_events, "incident_count": len(events),
        "by_ip": [{"ip_address": ip, "count": count, "last_seen": last_seen} for ip, count, last_seen in ip_summaries],
        "by_account": [{
            "account_id": account_id, "email": email, "status": status,
            "count": count, "last_seen": last_seen,
        } for account_id, email, status, count, last_seen in account_summaries],
        "by_attempted_email": [{
            "email": email, "count": count, "last_seen": last_seen,
        } for email, count, last_seen in attempted_summaries],
        "events": [{
            "id": item.id, "event_type": item.event_type, "account_id": item.account_id,
            "target": item.attempted_email, "ip_address": item.ip_address,
            "user_agent": item.user_agent, "created_at": item.created_at, "details": item.details,
        } for item in events],
    }


@router.get("/api/admin/tasks")
def admin_tasks(
    q: str = Query(default="", max_length=120),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|completed)$"),
    owner_account_id: int | None = Query(default=None, ge=1),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_tasks")),
) -> dict:
    statement = select(PersonalLearningTask)
    if status_filter:
        statement = statement.where(PersonalLearningTask.completed == (status_filter == "completed"))
    if owner_account_id:
        statement = statement.where(PersonalLearningTask.owner_account_id == owner_account_id)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(PersonalLearningTask.title.ilike(needle),
            PersonalLearningTask.category.ilike(needle),
            cast(PersonalLearningTask.owner_account_id, String).ilike(needle)))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, PersonalLearningTask.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(PersonalLearningTask.created_at.desc(), PersonalLearningTask.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{"id": row.id, "owner_account_id": row.owner_account_id, "title": row.title,
        "category": row.category, "due_date": row.due_date.isoformat() if row.due_date else None,
        "completed": row.completed, "created_at": row.created_at} for row in rows],
        "total": total, "offset": offset, "limit": limit}


@router.delete("/api/admin/group-tasks/bulk")
def bulk_delete_group_tasks(payload: dict, request: Request, db: Session = Depends(get_db),
                            actor: UserAccount = Depends(require_admin_permission("delete_tasks"))) -> dict:
    ids = payload.get("task_ids")
    reason = str(payload.get("reason", "")).strip()
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=422, detail="Explicit confirmation is required before deleting group tasks.")
    if not isinstance(ids, list) or not ids or len(ids) > 50 or any(type(i) is not int for i in ids) or len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Select between 1 and 50 unique group task IDs.")
    if len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Provide a deletion reason between 5 and 500 characters.")
    results = []
    for task_id in ids:
        task = db.get(GroupLearningTask, task_id)
        if task is None:
            results.append({"task_id": task_id, "success": False, "error": "Group task not found."})
            continue
        group_name = db.scalar(select(LearningGroup.name).where(LearningGroup.id == task.group_id)) or "unknown"
        assignment_count = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).where(
            GroupTaskAssignment.task_id == task_id
        )) or 0)
        db.query(GroupTaskAssignment).filter(GroupTaskAssignment.task_id == task_id).delete(synchronize_session=False)
        db.delete(task)
        results.append({"task_id": task_id, "success": True, "group_name": group_name,
                        "assignments_removed": assignment_count})
    db.commit()
    for result in results:
        if result["success"]:
            _audit(db, request, actor, "group_task_deleted", str(result["task_id"]),
                   f"group={result['group_name']}; assignments={result['assignments_removed']}; reason={reason}")
    return {"results": results, "succeeded": sum(item["success"] for item in results),
            "failed": sum(not item["success"] for item in results)}


@router.get("/api/admin/groups")
def admin_groups(
    q: str = Query(default="", max_length=120),
    owner_account_id: int | None = Query(default=None, ge=1),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_groups")),
) -> dict:
    statement = select(LearningGroup, UserAccount).join(UserAccount, UserAccount.id == LearningGroup.owner_account_id)
    if owner_account_id:
        statement = statement.where(LearningGroup.owner_account_id == owner_account_id)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(LearningGroup.name.ilike(needle), UserAccount.email.ilike(needle),
            cast(LearningGroup.owner_account_id, String).ilike(needle)))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, LearningGroup.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.execute(statement.order_by(LearningGroup.created_at.desc(), LearningGroup.id.desc()).offset(offset).limit(limit)).all()
    result = []
    for group, owner in rows:
        members = int(db.scalar(select(func.count()).select_from(LearningGroupMember).where(LearningGroupMember.group_id == group.id)) or 0)
        tasks = int(db.scalar(select(func.count()).select_from(GroupLearningTask).where(GroupLearningTask.group_id == group.id)) or 0)
        assignments = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).join(
            GroupLearningTask, GroupTaskAssignment.task_id == GroupLearningTask.id
        ).where(GroupLearningTask.group_id == group.id)) or 0)
        result.append({"id": group.id, "name": group.name, "owner_account_id": group.owner_account_id,
            "owner_email": owner.email, "member_count": members, "task_count": tasks,
            "assignment_count": assignments, "created_at": group.created_at, "status": "active"})
    return {"items": result, "total": total, "offset": offset, "limit": limit}


@router.get("/api/admin/group-tasks")
def admin_group_tasks(
    q: str = Query(default="", max_length=120),
    owner_account_id: int | None = Query(default=None, ge=1),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_tasks")),
) -> dict:
    statement = select(GroupLearningTask, LearningGroup, UserAccount).join(
        LearningGroup, LearningGroup.id == GroupLearningTask.group_id
    ).join(UserAccount, UserAccount.id == GroupLearningTask.created_by_account_id)
    if owner_account_id:
        statement = statement.where(GroupLearningTask.created_by_account_id == owner_account_id)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(GroupLearningTask.title.ilike(needle),
            LearningGroup.name.ilike(needle), UserAccount.email.ilike(needle),
            cast(GroupLearningTask.id, String).ilike(needle)))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    statement = _created_range(statement, GroupLearningTask.created_at, created_from, created_to)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.execute(statement.order_by(GroupLearningTask.created_at.desc(), GroupLearningTask.id.desc())
                      .offset(offset).limit(limit)).all()
    items = []
    for task, group, creator in rows:
        assignments = db.execute(select(GroupTaskAssignment, UserAccount).join(
            UserAccount, UserAccount.id == GroupTaskAssignment.student_account_id
        ).where(GroupTaskAssignment.task_id == task.id).order_by(UserAccount.email)).all()
        completed = sum(1 for assignment, _account in assignments if assignment.completed)
        status_value = ("Unassigned" if not assignments else
                        "Completed" if completed == len(assignments) else
                        "In progress" if completed else "Assigned")
        items.append({
            "id": task.id, "title": task.title, "group_id": group.id, "group_name": group.name,
            "created_by_email": creator.email,
            "assigned_students": [{"account_id": account.id, "email": account.email,
                                   "completed": assignment.completed}
                                  for assignment, account in assignments],
            "assignment_count": len(assignments), "completed_count": completed,
            "status": status_value, "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at,
        })
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.delete("/api/admin/tasks/bulk")
def bulk_delete_personal_tasks(payload: dict, request: Request, db: Session = Depends(get_db),
                               actor: UserAccount = Depends(require_admin_permission("delete_tasks"))) -> dict:
    ids = payload.get("task_ids")
    reason = str(payload.get("reason", "")).strip()
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=422, detail="Explicit confirmation is required before deleting tasks.")
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


@router.get("/api/admin/groups")
def admin_groups(db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_groups"))) -> list[dict]:
    groups = db.scalars(select(LearningGroup).order_by(LearningGroup.created_at.desc()).limit(500)).all()
    result = []
    for group in groups:
        members = int(db.scalar(select(func.count()).select_from(LearningGroupMember).where(LearningGroupMember.group_id == group.id)) or 0)
        tasks = int(db.scalar(select(func.count()).select_from(GroupLearningTask).where(GroupLearningTask.group_id == group.id)) or 0)
        result.append({"id": group.id, "name": group.name, "owner_account_id": group.owner_account_id, "member_count": members, "task_count": tasks})
    return result


@router.delete("/api/admin/groups/{group_id}")
def admin_delete_group(group_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                       actor: UserAccount = Depends(require_admin_permission("delete_groups"))) -> dict:
    if payload.get("confirm") is not True or len(str(payload.get("reason", "")).strip()) < 5:
        raise HTTPException(status_code=422, detail="Explicit confirmation and a deletion reason are required.")
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
           f"name={group.name}; members={member_count}; tasks={len(task_ids)}; assignments={assignment_count}; reason={str(payload.get('reason', '')).strip()}")
    return {"deleted": True, "group_id": group_id, "members_removed": member_count,
            "tasks_removed": len(task_ids), "assignments_removed": assignment_count}




@router.delete("/api/admin/activity/purge")
def purge_old_success_activity(payload: dict, request: Request, db: Session = Depends(get_db),
                               actor: UserAccount = Depends(require_admin_permission("manage_retention"))) -> dict:
    before = str(payload.get("before", "")).strip()
    reason = str(payload.get("reason", "")).strip()
    if payload.get("confirm") is not True or len(reason) < 5 or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Explicit confirmation and a reason between 5 and 500 characters are required.")
    try:
        cutoff = datetime.fromisoformat(before.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Provide an ISO-8601 cutoff timestamp.") from exc
    try:
        retention_days = int(os.getenv("ACTIVITY_LOGIN_RETENTION_DAYS", "90"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="ACTIVITY_LOGIN_RETENTION_DAYS must be an integer.") from exc
    if not 90 <= retention_days <= 3650:
        raise HTTPException(status_code=503, detail="ACTIVITY_LOGIN_RETENTION_DAYS must be between 90 and 3650.")
    if cutoff > datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=retention_days):
        raise HTTPException(
            status_code=422,
            detail=f"Activity cleanup is limited to successful-login events older than the configured {retention_days}-day retention period.",
        )
    cutoff_text = cutoff.isoformat()
    query = db.query(SecurityEvent).filter(
        SecurityEvent.event_type == "login_succeeded", SecurityEvent.created_at < cutoff_text
    )
    removed = query.count()
    query.delete(synchronize_session=False)
    db.commit()
    _audit(db, request, actor, "activity_retention_cleanup", "login_succeeded",
           f"removed={removed}; before={cutoff_text}; reason={reason.strip()}")
    return {"removed": removed, "preserved": "All moderation, security-incident and Admin audit events."}


@router.get("/api/admin/export/{kind}")
def export_admin_data(
    kind: str, request: Request,
    q: str = Query(default="", max_length=120),
    role: str | None = Query(default=None, pattern="^(student|tutor|admin)$"),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    account_id: int | None = Query(default=None, ge=1),
    scope: str = Query(default="all", pattern="^(all|personal|group)$"),
    owner_account_id: int | None = Query(default=None, ge=1),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    limit: int = Query(default=10000, ge=1, le=10000),
    db: Session = Depends(get_db),
    actor: UserAccount = Depends(require_admin_permission("export_data")),
) -> StreamingResponse:
    if kind not in {"users", "tasks", "activity"}:
        raise HTTPException(status_code=404, detail="Supported exports are users, tasks and activity.")
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="The start date must not be after the end date.")
    start_value = created_from.isoformat() if created_from else None
    end_value = (created_to + timedelta(days=1)).isoformat() if created_to else None
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    exported_rows = 0
    if kind == "users":
        writer.writerow(["account_id", "email", "role", "status", "created_at"])
        statement = select(UserAccount)
        if role:
            statement = statement.where(UserAccount.role == role)
        if status_filter:
            statement = statement.where(UserAccount.status == status_filter)
        if q.strip():
            needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
            student_matches = select(Student.account_id).where(Student.full_name.ilike(needle))
            tutor_matches = select(Tutor.account_id).where(Tutor.full_name.ilike(needle))
            statement = statement.where(or_(UserAccount.email.ilike(needle),
                UserAccount.id.in_(student_matches), UserAccount.id.in_(tutor_matches)))
        if start_value:
            statement = statement.where(UserAccount.created_at >= start_value)
        if end_value:
            statement = statement.where(UserAccount.created_at < end_value)
        rows = db.scalars(statement.order_by(UserAccount.id.desc()).limit(limit)).all()
        for row in rows:
            writer.writerow([row.id, _csv_cell(row.email), _csv_cell(row.role), _csv_cell(row.status), _csv_cell(row.created_at)])
        exported_rows = len(rows)
    elif kind == "tasks":
        writer.writerow(["record_type", "task_id", "owner_account_id", "student_account_id", "title", "category", "group", "due_date", "completed", "created_at"])
        remaining = limit
        if scope in {"all", "personal"} and remaining:
            statement = select(PersonalLearningTask)
            if status_filter in {"open", "completed"}:
                statement = statement.where(PersonalLearningTask.completed == (status_filter == "completed"))
            if owner_account_id:
                statement = statement.where(PersonalLearningTask.owner_account_id == owner_account_id)
            if q.strip():
                needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
                statement = statement.where(or_(PersonalLearningTask.title.ilike(needle),
                    PersonalLearningTask.category.ilike(needle),
                    cast(PersonalLearningTask.owner_account_id, String).ilike(needle)))
            if start_value:
                statement = statement.where(PersonalLearningTask.created_at >= start_value)
            if end_value:
                statement = statement.where(PersonalLearningTask.created_at < end_value)
            personal = db.scalars(statement.order_by(PersonalLearningTask.id.desc()).limit(remaining)).all()
            for row in personal:
                writer.writerow(["personal", row.id, row.owner_account_id, "", _csv_cell(row.title),
                    _csv_cell(row.category), "", row.due_date.isoformat() if row.due_date else "",
                    row.completed, _csv_cell(row.created_at)])
            exported_rows += len(personal)
            remaining -= len(personal)
        if scope in {"all", "group"} and remaining:
            statement = select(GroupTaskAssignment, GroupLearningTask, LearningGroup, UserAccount).join(
                GroupLearningTask, GroupTaskAssignment.task_id == GroupLearningTask.id
            ).join(LearningGroup, LearningGroup.id == GroupLearningTask.group_id).join(
                UserAccount, UserAccount.id == GroupTaskAssignment.student_account_id
            )
            if status_filter in {"open", "completed"}:
                statement = statement.where(GroupTaskAssignment.completed == (status_filter == "completed"))
            if owner_account_id:
                statement = statement.where(GroupLearningTask.created_by_account_id == owner_account_id)
            if q.strip():
                needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
                statement = statement.where(or_(GroupLearningTask.title.ilike(needle),
                    LearningGroup.name.ilike(needle), UserAccount.email.ilike(needle)))
            if start_value:
                statement = statement.where(GroupLearningTask.created_at >= start_value)
            if end_value:
                statement = statement.where(GroupLearningTask.created_at < end_value)
            assignments = db.execute(statement.order_by(GroupTaskAssignment.id.desc()).limit(remaining)).all()
            for assignment, task, group, student in assignments:
                writer.writerow(["group_assignment", task.id, task.created_by_account_id, student.id,
                    _csv_cell(task.title), "", _csv_cell(group.name),
                    task.due_date.isoformat() if task.due_date else "", assignment.completed,
                    _csv_cell(assignment.assigned_at)])
            exported_rows += len(assignments)
    else:
        writer.writerow(["event_id", "event_type", "account_id", "target", "ip_address", "created_at", "details"])
        statement = select(SecurityEvent)
        if status_filter:
            statement = statement.where(SecurityEvent.event_type == status_filter)
        if account_id:
            statement = statement.where(SecurityEvent.account_id == account_id)
        if q.strip():
            needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
            statement = statement.where(or_(SecurityEvent.event_type.ilike(needle),
                SecurityEvent.attempted_email.ilike(needle), SecurityEvent.details.ilike(needle),
                SecurityEvent.ip_address.ilike(needle), cast(SecurityEvent.account_id, String).ilike(needle)))
        if start_value:
            statement = statement.where(SecurityEvent.created_at >= start_value)
        if end_value:
            statement = statement.where(SecurityEvent.created_at < end_value)
        rows = db.scalars(statement.order_by(SecurityEvent.id.desc()).limit(limit)).all()
        for row in rows:
            writer.writerow([row.id, _csv_cell(row.event_type), row.account_id,
                _csv_cell(row.attempted_email), _csv_cell(row.ip_address),
                _csv_cell(row.created_at), _csv_cell(row.details)])
        exported_rows = len(rows)
    _audit(db, request, actor, "data_exported", kind,
           f"rows={exported_rows}; limit={limit}; role={role or ''}; status={status_filter or ''}; account={account_id or ''}; scope={scope}; owner={owner_account_id or ''}; from={start_value or ''}; to={created_to.isoformat() if created_to else ''}; query={q[:120]}")
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="tutorinn-{kind}.csv"',
                 "Cache-Control": "no-store", "X-Exported-Rows": str(exported_rows),
                 "X-Export-Max-Rows": str(limit)})



# Retained legacy match-review routes now require the authenticated Admin role.
@router.get("/api/admin/matches")
def list_admin_matches(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected)$"),
                       db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("moderate_learning"))) -> list[dict]:
    return crud.list_admin_matches(review_status=review_status, db=db)


@router.get("/api/admin/responses", response_model=list[ResponseRead])
def list_admin_responses(review_status: str = Query(default="Pending", pattern="^(Pending|Approved|Rejected|Not required)$"),
                         db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("moderate_learning"))) -> list[InterestResponse]:
    return crud.list_admin_responses(review_status=review_status, db=db, _=_)


@router.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(response_id: int, db: Session = Depends(get_db),
                     _: UserAccount = Depends(require_admin_permission("moderate_learning"))) -> InterestResponse:
    return crud.approve_interest(response_id=response_id, db=db, _=_)


@router.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(response_id: int, db: Session = Depends(get_db),
                    _: UserAccount = Depends(require_admin_permission("moderate_learning"))) -> InterestResponse:
    return crud.reject_interest(response_id=response_id, db=db, _=_)
