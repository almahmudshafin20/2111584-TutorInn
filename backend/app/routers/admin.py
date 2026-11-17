import csv
import json
import io
import os
import hmac
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.orm import Session

from .. import crud
from ..auth import record_security_event, require_roles, timestamp
from ..database import get_db
from ..notifications import send_account_deletion_outcome, send_former_user_content_verification, send_former_user_content_removal_outcome
from ..models import (
    AccountDeletionRequest, ContentReport, FormerUserContentRemovalRequest, FormerUserContentToken, GroupLearningTask, GroupTaskAssignment, InterestResponse, LearningGroup,
    LearningGroupMember, LearningPost, PersonalLearningTask, RefreshSession, RetainedContent,
    SecurityEvent, Student, Tutor, TutorVerification, UserAccount,
)
from ..schemas import AccountDeletionReviewInput, FormerUserContentRemovalReviewInput, ResponseRead

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
        details=(f"actor_role={actor.role}; target={target}; reason={reason.strip()}" if reason else f"actor_role={actor.role}; target={target}")[:2000],
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
        "deletion_pending_accounts": int(db.scalar(select(func.count()).select_from(UserAccount).where(UserAccount.status == "deletion_pending")) or 0),
        "pending_tutor_reviews": int(db.scalar(select(func.count()).select_from(Tutor).outerjoin(TutorVerification).where(
            or_(TutorVerification.id.is_(None), TutorVerification.status == "pending")
        )) or 0),
    }


@router.get("/api/admin/users")
def admin_users(
    role: str | None = Query(default=None, pattern="^(student|tutor|admin)$"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|banned|suspended|deletion_pending)$"),
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
    if target.status == "deletion_pending":
        raise HTTPException(status_code=409, detail="Review the pending account deletion request instead of changing this account status directly.")
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
        if target.status == "deletion_pending":
            results.append({"account_id": account_id, "success": False, "error": "Review the pending account deletion request instead."})
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
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db), _: UserAccount = Depends(require_admin_permission("view_security")),
) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    suspicious_types = [
        "login_failed", "login_locked", "login_succeeded", "refresh_token_reuse", "refresh_token_rejected",
        "refresh_token_expired", "access_denied", "access_token_rejected", "auth_rate_limited",
        "blocked_inactive_account", "refresh_blocked_inactive_account", "admin_bootstrap_denied", "registration_succeeded",
        "refresh_succeeded", "session_revoked", "password_changed", "account_status_changed",
        "bulk_account_status_changed", "account_session_revoked", "admin_role_granted", "admin_role_revoked",
    ]
    failure_types = [
        "login_failed", "login_locked", "refresh_token_reuse", "refresh_token_rejected",
        "refresh_token_expired", "access_denied", "access_token_rejected", "auth_rate_limited",
        "blocked_inactive_account", "refresh_blocked_inactive_account", "admin_bootstrap_denied",
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
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    events = db.scalars(statement.order_by(
        SecurityEvent.created_at.desc(), SecurityEvent.id.desc()
    ).offset(offset).limit(limit)).all()

    summary_scope = (scoped, SecurityEvent.event_type.in_(failure_types))
    ip_rows = db.execute(select(
        SecurityEvent.ip_address,
        func.count(SecurityEvent.id),
        func.max(SecurityEvent.created_at),
        func.count(func.distinct(SecurityEvent.account_id)),
    ).where(*summary_scope, SecurityEvent.ip_address != "")
     .group_by(SecurityEvent.ip_address)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()
    ip_event_rows = db.execute(select(
        SecurityEvent.ip_address, SecurityEvent.event_type,
    ).where(*summary_scope, SecurityEvent.ip_address.in_([row[0] for row in ip_rows]))
     .distinct()).all()
    ip_event_types: dict[str, list[str]] = {}
    for ip, kind in ip_event_rows:
        ip_event_types.setdefault(ip, []).append(kind)

    registration_identity = case(
        (SecurityEvent.account_id.is_not(None), cast(SecurityEvent.account_id, String)),
        (SecurityEvent.details.like("deleted_account_id=%"), SecurityEvent.details),
        else_=None,
    )
    registration_ip_rows = db.execute(select(
        SecurityEvent.ip_address, func.count(SecurityEvent.id), func.max(SecurityEvent.created_at),
        func.count(func.distinct(registration_identity)),
    ).where(scoped, SecurityEvent.event_type == "registration_succeeded", SecurityEvent.ip_address != "")
     .group_by(SecurityEvent.ip_address)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()

    account_rows = db.execute(select(
        SecurityEvent.account_id, UserAccount.email, UserAccount.status,
        func.count(SecurityEvent.id), func.max(SecurityEvent.created_at),
        func.count(func.distinct(SecurityEvent.ip_address)),
    ).join(UserAccount, UserAccount.id == SecurityEvent.account_id)
     .where(*summary_scope, SecurityEvent.account_id.is_not(None))
     .group_by(SecurityEvent.account_id, UserAccount.email, UserAccount.status)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()
    account_event_rows = db.execute(select(
        SecurityEvent.account_id, SecurityEvent.event_type,
    ).where(*summary_scope, SecurityEvent.account_id.in_([row[0] for row in account_rows]))
     .distinct()).all()
    account_event_types: dict[int, list[str]] = {}
    for account_key, kind in account_event_rows:
        account_event_types.setdefault(account_key, []).append(kind)

    attempted_summaries = db.execute(select(
        SecurityEvent.attempted_email, func.count(SecurityEvent.id), func.max(SecurityEvent.created_at)
    ).where(*summary_scope, SecurityEvent.account_id.is_(None), SecurityEvent.attempted_email != "")
     .group_by(SecurityEvent.attempted_email)
     .having(func.count(SecurityEvent.id) >= min_events)
     .order_by(func.count(SecurityEvent.id).desc()).limit(20)).all()

    hostile_events = db.scalars(select(SecurityEvent).where(
        scoped, SecurityEvent.event_type.in_(failure_types)
    ).order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc()).limit(50)).all()

    def serialize_event(item: SecurityEvent) -> dict:
        return {
            "id": item.id, "event_type": item.event_type, "account_id": item.account_id,
            "target": item.attempted_email, "ip_address": item.ip_address,
            "user_agent": item.user_agent, "created_at": item.created_at, "details": item.details,
        }

    return {
        "hours": hours, "min_events": min_events, "incident_count": total,
        "total": total, "offset": offset, "limit": limit,
        "by_ip": [{
            "ip_address": ip, "count": count, "last_seen": last_seen,
            "distinct_accounts": distinct_accounts, "event_types": sorted(ip_event_types.get(ip, [])),
        } for ip, count, last_seen, distinct_accounts in ip_rows],
        "registrations_by_ip": [{
            "ip_address": ip, "registrations": count, "last_seen": last_seen,
            "distinct_accounts": distinct_accounts,
        } for ip, count, last_seen, distinct_accounts in registration_ip_rows],
        "by_account": [{
            "account_id": account_key, "email": email, "status": status,
            "count": count, "last_seen": last_seen, "distinct_source_ips": distinct_ips,
            "event_types": sorted(account_event_types.get(account_key, [])),
        } for account_key, email, status, count, last_seen, distinct_ips in account_rows],
        "by_attempted_email": [{
            "email": email, "count": count, "last_seen": last_seen,
        } for email, count, last_seen in attempted_summaries],
        "events": [serialize_event(item) for item in events],
        "hostile_events": [serialize_event(item) for item in hostile_events],
    }


@router.get("/api/internal/maintenance/activity-retention")
def run_activity_retention(request: Request, db: Session = Depends(get_db)) -> dict:
    expected = os.getenv("CRON_SECRET", "").strip()
    authorization = request.headers.get("authorization", "")
    supplied = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if not expected:
        raise HTTPException(status_code=503, detail="Scheduled maintenance is not configured.")
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized maintenance request.")

    try:
        retention_days = int(os.getenv("ACTIVITY_RETENTION_DAYS", "90"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="ACTIVITY_RETENTION_DAYS must be an integer.") from exc
    if not 0 <= retention_days <= 3650:
        raise HTTPException(status_code=503, detail="ACTIVITY_RETENTION_DAYS must be between 0 and 3650.")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    last_run = db.scalar(select(SecurityEvent.created_at).where(
        SecurityEvent.event_type == "activity_retention_cleanup"
    ).order_by(SecurityEvent.created_at.desc()).limit(1))
    if last_run:
        last_run_at = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
        if last_run_at.tzinfo is None:
            last_run_at = last_run_at.replace(tzinfo=timezone.utc)
        if now - last_run_at < timedelta(hours=1):
            return {"skipped": True, "reason": "Cleanup already ran within the last hour.", "removed": 0}

    if retention_days == 0:
        record_security_event(
            db, "activity_retention_cleanup", request,
            details="disabled=true; removed=0; security incidents and audit evidence preserved",
        )
        return {"skipped": False, "disabled": True, "removed": 0, "retention_days": 0}

    cutoff = (now - timedelta(days=retention_days)).isoformat()
    removable = db.query(SecurityEvent).filter(
        SecurityEvent.created_at < cutoff,
        or_(
            SecurityEvent.event_type == "login_succeeded",
            SecurityEvent.event_type.like("auth_attempt_%"),
        ),
    )
    removed = removable.count()
    removable.delete(synchronize_session=False)
    db.commit()
    record_security_event(
        db, "activity_retention_cleanup", request,
        details=f"retention_days={retention_days}; removed={removed}; before={cutoff}; incidents_and_admin_audit_preserved=true",
    )
    return {
        "skipped": False, "disabled": False, "removed": removed,
        "retention_days": retention_days, "cutoff": cutoff,
        "preserved": "Security incidents, moderation history, password/session events and Admin audit evidence.",
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
        retention_days = int(os.getenv("ACTIVITY_RETENTION_DAYS", "90"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="ACTIVITY_RETENTION_DAYS must be an integer.") from exc
    if not 0 <= retention_days <= 3650:
        raise HTTPException(status_code=503, detail="ACTIVITY_RETENTION_DAYS must be between 0 and 3650.")
    if retention_days == 0:
        raise HTTPException(status_code=422, detail="Activity retention is disabled; indefinite retention is configured.")
    if cutoff > datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=retention_days):
        raise HTTPException(
            status_code=422,
            detail=f"Activity cleanup is limited to successful-login events older than the configured {retention_days}-day retention period.",
        )
    cutoff_text = cutoff.isoformat()
    query = db.query(SecurityEvent).filter(
        or_(
            SecurityEvent.event_type == "login_succeeded",
            SecurityEvent.event_type.like("auth_attempt_%"),
        ),
        SecurityEvent.created_at < cutoff_text,
    )
    removed = query.count()
    query.delete(synchronize_session=False)
    db.commit()
    _audit(db, request, actor, "activity_retention_cleanup", "login_and_rate_limit_counters",
           f"removed={removed}; before={cutoff_text}; reason={reason.strip()}")
    return {
        "removed": removed,
        "preserved": "All security incidents, moderation history and Admin audit events.",
    }


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
    return crud.list_admin_responses(review_status=review_status, db=db)


@router.post("/api/responses/{response_id}/approve", response_model=ResponseRead)
def approve_interest(response_id: int, db: Session = Depends(get_db),
                     _: UserAccount = Depends(require_admin_permission("moderate_learning"))) -> InterestResponse:
    return crud.approve_interest(response_id=response_id, db=db)


@router.post("/api/responses/{response_id}/reject", response_model=ResponseRead)
def reject_interest(response_id: int, db: Session = Depends(get_db),
                    _: UserAccount = Depends(require_admin_permission("moderate_learning"))) -> InterestResponse:
    return crud.reject_interest(response_id=response_id, db=db)


@router.get("/api/admin/account-deletion-requests")
def list_account_deletion_requests(
    status_filter: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: UserAccount = Depends(require_admin_permission("manage_accounts")),
) -> dict:
    statement = select(AccountDeletionRequest)
    if status_filter != "all":
        statement = statement.where(AccountDeletionRequest.status == status_filter)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(AccountDeletionRequest.requested_at.desc(), AccountDeletionRequest.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{
        "id": row.id, "account_email": row.account_email, "account_role": row.account_role,
        "reason": row.reason, "requested_option": row.requested_option, "final_option": row.final_option,
        "requested_account_action": row.requested_account_action,
        "requested_content_action": row.requested_content_action,
        "requested_content_ids": json.loads(row.requested_content_ids or "[]"),
        "requested_visibility": row.requested_visibility,
        "requested_anonymize_content": row.requested_anonymize_content,
        "final_account_action": row.final_account_action,
        "final_content_action": row.final_content_action,
        "final_content_ids": json.loads(row.final_content_ids or "[]") if row.final_content_ids else None,
        "final_visibility": row.final_visibility,
        "final_anonymize_content": row.final_anonymize_content,
        "available_content": [
            {"content_type": kind, "content_id": content_id}
            for kind, ids in _owned_deletion_content(db, db.get(UserAccount, row.account_id)).items()
            for content_id in sorted(ids)
        ] if row.account_id is not None and db.get(UserAccount, row.account_id) is not None else [],
        "notification_status": row.notification_status, "status": row.status, "requested_at": row.requested_at,
        "reviewed_at": row.reviewed_at, "reviewed_by_account_id": row.reviewed_by_account_id,
    } for row in rows], "total": total, "offset": offset, "limit": limit}



def _owned_deletion_content(db: Session, account: UserAccount) -> dict[str, set[int]]:
    """Return content records owned by an account, keyed by stable content type."""
    student = db.scalar(select(Student).where(Student.account_id == account.id))
    tutor = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    profile_id = student.id if student else (tutor.id if tutor else None)
    profile_type = "student" if student else ("tutor" if tutor else None)
    posts = set(db.scalars(select(LearningPost.id).where(
        LearningPost.author_profile_id == profile_id,
        LearningPost.author_profile_type == profile_type,
    )).all()) if profile_id is not None else set()
    groups = set(db.scalars(select(LearningGroup.id).where(
        LearningGroup.owner_account_id == account.id,
    )).all())
    tasks = select(GroupLearningTask.id).where(or_(
        GroupLearningTask.created_by_account_id == account.id,
        GroupLearningTask.group_id.in_(groups) if groups else False,
    ))
    return {
        "learning_post": posts,
        "personal_task": set(db.scalars(select(PersonalLearningTask.id).where(
            PersonalLearningTask.owner_account_id == account.id,
        )).all()),
        "learning_group": groups,
        "group_task": set(db.scalars(tasks).all()),
        "group_assignment": set(db.scalars(select(GroupTaskAssignment.id).where(
            GroupTaskAssignment.student_account_id == account.id,
        )).all()),
    }


def _selection_map(items: list[dict]) -> dict[str, set[int]]:
    selected = {kind: set() for kind in (
        "learning_post", "personal_task", "learning_group", "group_task", "group_assignment",
    )}
    raw_keys = [(item["content_type"], item["content_id"]) for item in items]
    if len(raw_keys) != len(set(raw_keys)):
        raise HTTPException(status_code=422, detail="A content item can only be selected once.")
    for item in items:
        kind, content_id = item["content_type"], item["content_id"]
        if kind not in selected or content_id <= 0:
            raise HTTPException(status_code=422, detail="The selected content list is invalid.")
        selected[kind].add(content_id)
    return selected


def _delete_selected_content(
    db: Session,
    account: UserAccount,
    deletion: AccountDeletionRequest,
    content_action: str,
    selected_items: list[dict],
    visibility: str,
    anonymize_content: bool,
) -> dict[str, int]:
    """Delete selected owned items and detach retained items before account removal."""
    owned = _owned_deletion_content(db, account)
    selected = _selection_map(selected_items)
    for kind, ids in selected.items():
        if not ids.issubset(owned[kind]):
            raise HTTPException(status_code=422, detail="One or more selected items are no longer owned by this account.")

    if content_action == "delete_all":
        to_delete = {kind: set(ids) for kind, ids in owned.items()}
    elif content_action == "delete_selected":
        to_delete = {kind: set(ids) for kind, ids in selected.items()}
    else:
        to_delete = {kind: set() for kind in owned}

    groups_to_delete = to_delete["learning_group"]
    if groups_to_delete:
        other_members = int(db.scalar(select(func.count()).select_from(LearningGroupMember).where(
            LearningGroupMember.group_id.in_(groups_to_delete),
            (LearningGroupMember.student_account_id.is_(None)) | (LearningGroupMember.student_account_id != account.id),
        )) or 0)
        other_assignments = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).join(
            GroupLearningTask, GroupTaskAssignment.task_id == GroupLearningTask.id,
        ).where(
            GroupLearningTask.group_id.in_(groups_to_delete),
            (GroupTaskAssignment.student_account_id.is_(None)) | (GroupTaskAssignment.student_account_id != account.id),
        )) or 0)
        if other_members or other_assignments:
            raise HTTPException(
                status_code=409,
                detail="This group still contains other students or their assignments. Retain the group or transfer its learning data before deleting it.",
            )

    tasks_to_delete = to_delete["group_task"]
    if tasks_to_delete:
        other_assignments = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).where(
            GroupTaskAssignment.task_id.in_(tasks_to_delete),
            (GroupTaskAssignment.student_account_id.is_(None)) | (GroupTaskAssignment.student_account_id != account.id),
        )) or 0)
        if other_assignments:
            raise HTTPException(
                status_code=409,
                detail="One or more selected group tasks contain other students' assignments. Retain or transfer those tasks before deleting them.",
            )

    if groups_to_delete:
        dependent_tasks = set(db.scalars(select(GroupLearningTask.id).where(
            GroupLearningTask.group_id.in_(groups_to_delete),
        )).all())
        tasks_to_delete.update(dependent_tasks)
    if tasks_to_delete:
        dependent_assignments = set(db.scalars(select(GroupTaskAssignment.id).where(
            GroupTaskAssignment.task_id.in_(tasks_to_delete),
        )).all())
        to_delete["group_assignment"].update(dependent_assignments)

    retained_counts: dict[str, int] = {}
    for kind, ids in owned.items():
        retained_ids = ids - to_delete[kind]
        retained_counts[kind] = len(retained_ids)
        for content_id in retained_ids:
            db.add(RetainedContent(
                deletion_request_id=deletion.id, content_type=kind, content_id=content_id,
                visibility=visibility, anonymized=anonymize_content, created_at=timestamp(),
            ))

    student = db.scalar(select(Student).where(Student.account_id == account.id))
    tutor = db.scalar(select(Tutor).where(Tutor.account_id == account.id))
    profile_id = student.id if student else (tutor.id if tutor else None)
    profile_type = "student" if student else ("tutor" if tutor else None)
    if profile_id is not None:
        retained_posts = owned["learning_post"] - to_delete["learning_post"]
        if retained_posts:
            updates = {"author_profile_id": None, "author_profile_type": None}
            if anonymize_content:
                updates["author_name"] = "Deleted user"
            db.query(LearningPost).filter(LearningPost.id.in_(retained_posts)).update(
                updates, synchronize_session=False,
            )
        db.query(InterestResponse).filter(
            InterestResponse.profile_id == profile_id,
            InterestResponse.profile_type == profile_type,
        ).delete(synchronize_session=False)
        db.query(ContentReport).filter(
            ContentReport.target_type == "profile",
            ContentReport.target_role == account.role,
            ContentReport.target_id == profile_id,
        ).delete(synchronize_session=False)

    deleted_posts = to_delete["learning_post"]
    if deleted_posts:
        db.query(InterestResponse).filter(InterestResponse.post_id.in_(deleted_posts)).delete(synchronize_session=False)
        db.query(ContentReport).filter(
            ContentReport.target_type.in_(["tutoring_post", "tutoring_request"]),
            ContentReport.target_id.in_(deleted_posts),
        ).delete(synchronize_session=False)
        db.query(LearningPost).filter(LearningPost.id.in_(deleted_posts)).delete(synchronize_session=False)

    retained_personal = owned["personal_task"] - to_delete["personal_task"]
    if retained_personal:
        db.query(PersonalLearningTask).filter(PersonalLearningTask.id.in_(retained_personal)).update(
            {"owner_account_id": None}, synchronize_session=False,
        )
    if to_delete["personal_task"]:
        db.query(PersonalLearningTask).filter(PersonalLearningTask.id.in_(to_delete["personal_task"])).delete(synchronize_session=False)

    retained_groups = owned["learning_group"] - groups_to_delete
    if retained_groups:
        db.query(LearningGroup).filter(LearningGroup.id.in_(retained_groups)).update(
            {"owner_account_id": None}, synchronize_session=False,
        )
    if groups_to_delete:
        db.query(LearningGroupMember).filter(LearningGroupMember.group_id.in_(groups_to_delete)).delete(synchronize_session=False)
        db.query(LearningGroup).filter(LearningGroup.id.in_(groups_to_delete)).delete(synchronize_session=False)

    retained_tasks = owned["group_task"] - tasks_to_delete
    if retained_tasks:
        db.query(GroupLearningTask).filter(GroupLearningTask.id.in_(retained_tasks)).update(
            {"created_by_account_id": None}, synchronize_session=False,
        )
    if tasks_to_delete:
        db.query(GroupTaskAssignment).filter(GroupTaskAssignment.task_id.in_(tasks_to_delete)).delete(synchronize_session=False)
        db.query(GroupLearningTask).filter(GroupLearningTask.id.in_(tasks_to_delete)).delete(synchronize_session=False)

    retained_assignments = owned["group_assignment"] - to_delete["group_assignment"]
    if retained_assignments:
        db.query(GroupTaskAssignment).filter(GroupTaskAssignment.id.in_(retained_assignments)).update(
            {"student_account_id": None}, synchronize_session=False,
        )
    if to_delete["group_assignment"]:
        db.query(GroupTaskAssignment).filter(GroupTaskAssignment.id.in_(to_delete["group_assignment"])).delete(synchronize_session=False)

    db.query(LearningGroupMember).filter(
        LearningGroupMember.student_account_id == account.id,
    ).delete(synchronize_session=False)
    db.query(ContentReport).filter(ContentReport.reporter_account_id == account.id).delete(synchronize_session=False)
    if tutor is not None:
        db.query(TutorVerification).filter(TutorVerification.tutor_id == tutor.id).delete(synchronize_session=False)
        db.delete(tutor)
    if student is not None:
        db.delete(student)

    email = account.email
    db.query(RefreshSession).filter(RefreshSession.account_id == account.id).delete(synchronize_session=False)
    db.query(SecurityEvent).filter(
        or_(SecurityEvent.account_id == account.id, SecurityEvent.attempted_email == email),
    ).update(
        {"account_id": None, "attempted_email": "", "details": "deleted_account_id=" + str(account.id)},
        synchronize_session=False,
    )
    deletion.account_id = None
    deletion.account_email = "[deleted]"
    deletion.reason = ""
    db.delete(account)
    db.flush()
    return retained_counts


@router.patch("/api/admin/account-deletion-requests/{request_id}")
def review_account_deletion_request(
    request_id: int,
    payload: AccountDeletionReviewInput,
    request: Request,
    db: Session = Depends(get_db),
    actor: UserAccount = Depends(require_admin_permission("manage_accounts")),
) -> dict:
    deletion = db.scalar(select(AccountDeletionRequest).where(
        AccountDeletionRequest.id == request_id,
    ).with_for_update())
    if deletion is None:
        raise HTTPException(status_code=404, detail="Account deletion request not found.")
    if deletion.status != "pending" or deletion.account_id is None:
        raise HTTPException(status_code=409, detail="This deletion request has already been reviewed.")
    target = db.scalar(select(UserAccount).where(
        UserAccount.id == deletion.account_id,
    ).with_for_update())
    if target is None or target.status != "deletion_pending":
        raise HTTPException(status_code=409, detail="The requesting account is no longer awaiting deletion.")

    now = timestamp()
    note = payload.review_note.strip()
    if payload.status == "rejected":
        deletion.status = "rejected"
        deletion.reviewed_at = now
        deletion.reviewed_by_account_id = actor.id
        deletion.reason = ""
        target.status = "active"
        target.updated_at = now
        db.commit()
        _audit(db, request, actor, "account_deletion_rejected", str(deletion.id), note or "No review note")
        return {"id": deletion.id, "status": deletion.status, "account_status": target.status}

    if payload.content_action is not None:
        final_content_action = payload.content_action
    elif payload.deletion_option is not None:
        final_content_action = "retain_all" if payload.deletion_option == "anonymize" else "delete_all"
    else:
        final_content_action = deletion.requested_content_action

    if payload.deletion_option == "anonymize" and payload.content_action is None:
        final_anonymize = True
    elif payload.deletion_option == "complete" and payload.content_action is None:
        final_anonymize = False
    else:
        final_anonymize = (
            payload.anonymize_content
            if payload.anonymize_content is not None
            else deletion.requested_anonymize_content
        )
    final_visibility = payload.visibility or deletion.requested_visibility
    selected_items = (
        [item.model_dump() for item in payload.selected_content]
        if payload.selected_content is not None
        else json.loads(deletion.requested_content_ids or "[]")
    )
    if final_content_action == "delete_selected" and not selected_items:
        raise HTTPException(status_code=422, detail="Select at least one content item for the Admin's final selected-content decision.")
    if final_content_action != "delete_selected" and payload.selected_content:
        raise HTTPException(status_code=422, detail="Selected content is only valid with the selected-content decision.")

    deletion.final_account_action = "delete_account"
    deletion.final_content_action = final_content_action
    deletion.final_content_ids = json.dumps(selected_items if final_content_action == "delete_selected" else [], separators=(",", ":"))
    deletion.final_visibility = final_visibility
    deletion.final_anonymize_content = final_anonymize
    deletion.final_option = "complete" if final_content_action in {"delete_selected", "delete_all"} else "anonymize"
    deletion.status = "approved"
    deletion.reviewed_at = now
    deletion.reviewed_by_account_id = actor.id

    recipient_email = deletion.account_email
    deletion.former_user_email = recipient_email
    account_role = deletion.account_role
    try:
        retained_counts = _delete_selected_content(
            db, target, deletion, final_content_action, selected_items,
            final_visibility, final_anonymize,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    former_link_status = "not_required"
    retained_total = sum(retained_counts.values())
    if retained_total:
        raw_token = secrets.token_urlsafe(48)
        db.add(FormerUserContentToken(
            deletion_request_id=deletion.id,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
            created_at=timestamp(),
        ))
        db.commit()
        try:
            former_link_status = "sent" if send_former_user_content_verification(
                recipient_email, deletion.id, raw_token,
            ) else "not_configured"
        except Exception:
            former_link_status = "failed"

    notification_status = "not_configured"
    try:
        if send_account_deletion_outcome(
            recipient_email, deletion.id, account_role, deletion.final_option,
            content_action=final_content_action,
            visibility=final_visibility,
            anonymize_content=final_anonymize,
            retained_counts=retained_counts,
        ):
            notification_status = "sent"
    except Exception:
        notification_status = "failed"
    deletion.notification_status = notification_status
    db.commit()
    record_security_event(
        db, "admin_account_deletion_approved", request, account_id=actor.id,
        details=f"deletion_request_id={deletion.id}; content_action={final_content_action}",
    )
    return {
        "id": deletion.id, "status": "approved",
        "deleted": final_content_action in {"delete_all", "delete_selected"},
        "final_option": deletion.final_option, "final_content_action": final_content_action,
        "final_visibility": final_visibility, "final_anonymize_content": final_anonymize,
        "anonymized": final_anonymize,
        "retained_counts": retained_counts, "notification_status": notification_status,
        "former_user_link_status": former_link_status,
    }



@router.get("/api/admin/former-user-content-removal-requests")
def list_former_user_content_removal_requests(
    status_filter: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: UserAccount = Depends(require_admin_permission("manage_accounts")),
) -> dict:
    statement = select(FormerUserContentRemovalRequest)
    if status_filter != "all":
        statement = statement.where(FormerUserContentRemovalRequest.status == status_filter)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(
        FormerUserContentRemovalRequest.requested_at.desc(),
        FormerUserContentRemovalRequest.id.desc(),
    ).offset(offset).limit(limit)).all()
    items = []
    for row in rows:
        deletion = db.get(AccountDeletionRequest, row.deletion_request_id)
        retained = db.scalars(select(RetainedContent).where(
            RetainedContent.deletion_request_id == row.deletion_request_id,
        )).all()
        items.append({
            "id": row.id, "deletion_request_id": row.deletion_request_id,
            "account_email": deletion.account_email if deletion else "",
            "selected_content": json.loads(row.selected_content or "[]"),
            "available_retained_content": [
                {"content_type": item.content_type, "content_id": item.content_id, "visibility": item.visibility}
                for item in retained
            ],
            "status": row.status, "requested_at": row.requested_at,
            "reviewed_at": row.reviewed_at, "review_note": row.review_note,
        })
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.patch("/api/admin/former-user-content-removal-requests/{request_id}")
def review_former_user_content_removal_request(
    request_id: int,
    payload: FormerUserContentRemovalReviewInput,
    request: Request,
    db: Session = Depends(get_db),
    actor: UserAccount = Depends(require_admin_permission("manage_accounts")),
) -> dict:
    item = db.scalar(select(FormerUserContentRemovalRequest).where(
        FormerUserContentRemovalRequest.id == request_id,
    ).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Former-user removal request not found.")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="This former-user removal request has already been reviewed.")
    deletion = db.get(AccountDeletionRequest, item.deletion_request_id)
    if deletion is None or deletion.status != "approved" or deletion.account_id is not None:
        raise HTTPException(status_code=409, detail="The original account deletion record is not eligible for this review.")

    selected = json.loads(item.selected_content or "[]")
    retained_rows = db.scalars(select(RetainedContent).where(
        RetainedContent.deletion_request_id == item.deletion_request_id,
    ).with_for_update()).all()
    retained_map = {(row.content_type, row.content_id): row for row in retained_rows}
    keys = [(entry["content_type"], entry["content_id"]) for entry in selected]
    if any(key not in retained_map for key in keys):
        raise HTTPException(status_code=409, detail="One or more requested items are no longer retained.")

    if payload.status == "approved":
        for kind, content_id in keys:
            if kind == "learning_post":
                db.query(InterestResponse).filter(InterestResponse.post_id == content_id).delete(synchronize_session=False)
                db.query(ContentReport).filter(ContentReport.target_id == content_id,
                    ContentReport.target_type.in_(["tutoring_post", "tutoring_request"])).delete(synchronize_session=False)
                db.query(LearningPost).filter(LearningPost.id == content_id).delete(synchronize_session=False)
            elif kind == "personal_task":
                db.query(PersonalLearningTask).filter(PersonalLearningTask.id == content_id).delete(synchronize_session=False)
            elif kind == "group_assignment":
                db.query(GroupTaskAssignment).filter(GroupTaskAssignment.id == content_id).delete(synchronize_session=False)
            elif kind == "group_task":
                other_assignments = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).where(
                    GroupTaskAssignment.task_id == content_id,
                )) or 0)
                if other_assignments:
                    raise HTTPException(status_code=409, detail="A retained group task still has assignments. Admin must resolve those assignments first.")
                db.query(GroupLearningTask).filter(GroupLearningTask.id == content_id).delete(synchronize_session=False)
            elif kind == "learning_group":
                member_count = int(db.scalar(select(func.count()).select_from(LearningGroupMember).where(
                    LearningGroupMember.group_id == content_id,
                )) or 0)
                task_ids = list(db.scalars(select(GroupLearningTask.id).where(
                    GroupLearningTask.group_id == content_id,
                )).all())
                assignment_count = int(db.scalar(select(func.count()).select_from(GroupTaskAssignment).where(
                    GroupTaskAssignment.task_id.in_(task_ids),
                )) or 0) if task_ids else 0
                if member_count or assignment_count:
                    raise HTTPException(status_code=409, detail="A retained group still has members or assignments. Admin must resolve shared learning data before removal.")
                if task_ids:
                    assignment_ids = select(GroupTaskAssignment.id).where(
                        GroupTaskAssignment.task_id.in_(task_ids),
                    )
                    db.query(RetainedContent).filter(
                        RetainedContent.content_type == "group_assignment",
                        RetainedContent.content_id.in_(assignment_ids),
                    ).delete(synchronize_session=False)
                    db.query(RetainedContent).filter(
                        RetainedContent.content_type == "group_task",
                        RetainedContent.content_id.in_(task_ids),
                    ).delete(synchronize_session=False)
                    db.query(GroupLearningTask).filter(GroupLearningTask.id.in_(task_ids)).delete(synchronize_session=False)
                db.query(RetainedContent).filter(
                    RetainedContent.content_type == "learning_group",
                    RetainedContent.content_id == content_id,
                ).delete(synchronize_session=False)
                db.query(LearningGroup).filter(LearningGroup.id == content_id).delete(synchronize_session=False)
            db.delete(retained_map[(kind, content_id)])

    item.status = payload.status
    item.reviewed_at = timestamp()
    item.reviewed_by_account_id = actor.id
    item.review_note = payload.review_note.strip()
    retry_token = None
    if payload.status == "rejected":
        # Rejection must not strand the former user: issue a fresh one-time link.
        retry_token = secrets.token_urlsafe(48)
        db.add(FormerUserContentToken(
            deletion_request_id=deletion.id,
            token_hash=hashlib.sha256(retry_token.encode("utf-8")).hexdigest(),
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
            consumed_at=None,
            created_at=timestamp(),
        ))
    db.commit()
    _audit(db, request, actor, "former_user_content_removal_" + payload.status,
           str(item.id), f"deletion_request={deletion.id}; selected_items={len(selected)}; {item.review_note}")

    notification_status = "not_configured"
    retry_link_status = "not_applicable"
    try:
        if payload.status == "approved":
            sent = send_former_user_content_removal_outcome(
                deletion.former_user_email or deletion.account_email, item.id, payload.status, item.review_note,
            )
            notification_status = "sent" if sent else "not_configured"
        else:
            sent = send_former_user_content_verification(
                deletion.former_user_email or deletion.account_email, deletion.id, retry_token,
            )
            retry_link_status = "sent" if sent else "not_configured"
            notification_status = retry_link_status
    except Exception:
        notification_status = "failed"
        if payload.status == "rejected":
            retry_link_status = "failed"

    return {"id": item.id, "status": item.status, "reviewed_at": item.reviewed_at,
            "removed_items": len(selected) if payload.status == "approved" else 0,
            "notification_status": notification_status, "retry_link_status": retry_link_status}
