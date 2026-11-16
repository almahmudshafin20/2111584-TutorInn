from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth import get_current_account, record_security_event
from ..database import get_db
from ..models import ContentReport, LearningPost, ManagedSubject, SecurityEvent, Student, Tutor, UserAccount

router = APIRouter(tags=["Moderation and subjects"])
REPORT_REASONS = {"harassment", "spam", "misleading", "inappropriate", "impersonation", "other"}
TARGET_TYPES = {"profile", "tutoring_post", "tutoring_request"}
REPORT_STATUSES = {"pending", "in_review", "resolved", "dismissed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _admin(account: UserAccount = Depends(get_current_account)) -> UserAccount:
    if account.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return account


def _audit(db: Session, request: Request, actor: UserAccount, event: str, target: str, details: str = "") -> None:
    record_security_event(db, "admin_" + event, request, account_id=actor.id,
                          attempted_email=target[:255], details=details[:1800])


def _seed_catalogue(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(ManagedSubject)):
        return
    legacy: dict[str, str] = {}
    for profile in list(db.scalars(select(Student)).all()) + list(db.scalars(select(Tutor)).all()):
        for name in profile.subjects:
            legacy.setdefault(name.casefold(), name)
    for post in db.scalars(select(LearningPost)).all():
        for name in post.subjects:
            legacy.setdefault(name.casefold(), name)
    for name in sorted(legacy.values(), key=str.casefold):
        db.add(ManagedSubject(name=name, active=True, created_at=_now(), updated_at=_now()))
    if legacy:
        db.commit()


def _report_payload(item: ContentReport, db: Session) -> dict:
    reporter = db.get(UserAccount, item.reporter_account_id)
    target_label = "Unavailable target"
    if item.target_type == "profile":
        target = db.get(Student if item.target_role == "student" else Tutor, item.target_id)
        if target:
            target_label = f"{target.full_name} ({target.email})"
    else:
        target = db.get(LearningPost, item.target_id)
        if target:
            target_label = f"{target.author_name} — {', '.join(target.subjects)}"
    return {
        "id": item.id, "reporter_account_id": item.reporter_account_id,
        "reporter_email": reporter.email if reporter else "Deleted account",
        "target_type": item.target_type, "target_role": item.target_role, "target_id": item.target_id,
        "target_label": target_label, "reason": item.reason,
        "description": item.description, "status": item.status,
        "review_note": item.review_note, "reviewed_by_account_id": item.reviewed_by_account_id,
        "reviewed_at": item.reviewed_at, "created_at": item.created_at,
    }


@router.get("/api/subjects")
def active_subjects(db: Session = Depends(get_db)) -> list[str]:
    _seed_catalogue(db)
    return list(db.scalars(select(ManagedSubject.name).where(ManagedSubject.active.is_(True)).order_by(ManagedSubject.name)).all())


@router.post("/api/reports", status_code=status.HTTP_201_CREATED)
def create_report(payload: dict, request: Request, db: Session = Depends(get_db),
                  actor: UserAccount = Depends(get_current_account)) -> dict:
    target_type = str(payload.get("target_type", "")).strip()
    target_role = str(payload.get("target_role", "")).strip()
    reason = str(payload.get("reason", "")).strip()
    description = str(payload.get("description", "")).strip()
    try:
        target_id = int(payload.get("target_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="A valid target ID is required.")
    if target_type not in TARGET_TYPES or target_id < 1:
        raise HTTPException(status_code=422, detail="Choose a supported report target.")
    if reason not in REPORT_REASONS:
        raise HTTPException(status_code=422, detail="Choose a valid report reason.")
    if len(description) > 2000:
        raise HTTPException(status_code=422, detail="Description must be 2,000 characters or fewer.")
    if actor.role not in {"student", "tutor"}:
        raise HTTPException(status_code=403, detail="Only Student and Tutor accounts can submit reports.")
    if target_type == "profile":
        if target_role not in {"student", "tutor"}:
            raise HTTPException(status_code=422, detail="Choose whether the reported profile belongs to a Student or Tutor.")
        target = db.get(Student if target_role == "student" else Tutor, target_id)
        if target is None:
            raise HTTPException(status_code=404, detail="The reported profile was not found.")
        if target.account_id == actor.id:
            raise HTTPException(status_code=422, detail="You cannot report your own profile.")
    else:
        target_role = ""
        target = db.get(LearningPost, target_id)
        expected = "tutor" if target_type == "tutoring_post" else "student"
        if target is None or target.post_type != expected:
            raise HTTPException(status_code=404, detail="The reported tutoring content was not found.")
        if target.author_profile_type == actor.role:
            own_profile = db.scalar(select(Tutor.id if actor.role == "tutor" else Student.id).where(
                (Tutor.account_id if actor.role == "tutor" else Student.account_id) == actor.id
            ))
            if own_profile is not None and target.author_profile_id == own_profile:
                raise HTTPException(status_code=422, detail="You cannot report your own content.")
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent = int(db.scalar(select(func.count()).select_from(ContentReport).where(
        ContentReport.reporter_account_id == actor.id, ContentReport.created_at >= since
    )) or 0)
    if recent >= 10:
        raise HTTPException(status_code=429, detail="You have reached the daily report limit. Try again later.")
    duplicate = db.scalar(select(ContentReport).where(
        ContentReport.reporter_account_id == actor.id, ContentReport.target_type == target_type,
        ContentReport.target_id == target_id, ContentReport.status.in_(["pending", "in_review"]),
        ContentReport.created_at >= since,
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="You have already submitted an open report for this content.")
    item = ContentReport(reporter_account_id=actor.id, target_type=target_type, target_role=target_role or None,
                         target_id=target_id, reason=reason, description=description, status="pending", created_at=_now())
    db.add(item)
    db.commit()
    db.refresh(item)
    record_security_event(db, "content_report_submitted", request, account_id=actor.id,
                          details=f"report_id={item.id}; target_type={target_type}; target_id={target_id}")
    return {"id": item.id, "status": item.status, "created_at": item.created_at}


@router.get("/api/admin/reports")
def list_reports(status_filter: str | None = Query(default=None, alias="status", pattern="^(pending|in_review|resolved|dismissed)$"),
                 q: str = Query(default="", max_length=120), offset: int = Query(default=0, ge=0, le=100000),
                 limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db),
                 _: UserAccount = Depends(_admin)) -> dict:
    statement = select(ContentReport)
    if status_filter:
        statement = statement.where(ContentReport.status == status_filter)
    if q.strip():
        needle = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(ContentReport.reason.ilike(needle), ContentReport.description.ilike(needle),
                                        ContentReport.target_type.ilike(needle)))
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    items = db.scalars(statement.order_by(ContentReport.created_at.desc(), ContentReport.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [_report_payload(item, db) for item in items], "total": total, "offset": offset, "limit": limit}


@router.patch("/api/admin/reports/{report_id}")
def review_report(report_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                  actor: UserAccount = Depends(_admin)) -> dict:
    next_status = str(payload.get("status", "")).strip()
    note = str(payload.get("review_note", "")).strip()
    if next_status not in REPORT_STATUSES or next_status == "pending":
        raise HTTPException(status_code=422, detail="Choose in_review, resolved or dismissed.")
    if len(note) < 5 or len(note) > 1000:
        raise HTTPException(status_code=422, detail="Provide an Admin review note between 5 and 1,000 characters.")
    item = db.get(ContentReport, report_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    item.status = next_status
    item.review_note = note
    item.reviewed_by_account_id = actor.id
    item.reviewed_at = _now()
    db.commit()
    _audit(db, request, actor, "report_" + next_status, str(item.id),
           f"target_type={item.target_type}; target_id={item.target_id}; note={note}")
    db.refresh(item)
    return _report_payload(item, db)


@router.get("/api/admin/subjects")
def admin_subjects(db: Session = Depends(get_db), _: UserAccount = Depends(_admin)) -> list[dict]:
    _seed_catalogue(db)
    return [{"id": item.id, "name": item.name, "active": item.active, "created_at": item.created_at}
            for item in db.scalars(select(ManagedSubject).order_by(ManagedSubject.name)).all()]


@router.post("/api/admin/subjects", status_code=status.HTTP_201_CREATED)
def create_subject(payload: dict, request: Request, db: Session = Depends(get_db),
                   actor: UserAccount = Depends(_admin)) -> dict:
    name = str(payload.get("name", "")).strip()
    if not 2 <= len(name) <= 80:
        raise HTTPException(status_code=422, detail="Subject names must be between 2 and 80 characters.")
    _seed_catalogue(db)
    duplicate = db.scalar(select(ManagedSubject).where(func.lower(ManagedSubject.name) == name.casefold()))
    if duplicate:
        raise HTTPException(status_code=409, detail="A subject with this name already exists.")
    item = ManagedSubject(name=name, active=True, created_at=_now(), updated_at=_now())
    db.add(item)
    db.commit()
    db.refresh(item)
    _audit(db, request, actor, "subject_created", str(item.id), f"name={name}")
    return {"id": item.id, "name": item.name, "active": item.active, "created_at": item.created_at}


@router.patch("/api/admin/subjects/{subject_id}")
def update_subject(subject_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
                   actor: UserAccount = Depends(_admin)) -> dict:
    item = db.get(ManagedSubject, subject_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Subject not found.")
    name = str(payload.get("name", item.name)).strip()
    active = payload.get("active", item.active)
    if not 2 <= len(name) <= 80 or not isinstance(active, bool):
        raise HTTPException(status_code=422, detail="Provide a valid subject name and active flag.")
    duplicate = db.scalar(select(ManagedSubject).where(func.lower(ManagedSubject.name) == name.casefold(), ManagedSubject.id != item.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="A subject with this name already exists.")
    previous = item.name
    if name.casefold() != previous.casefold() and _subject_is_referenced(db, previous):
        raise HTTPException(status_code=409, detail="This subject is already used by profiles or tutoring listings. Deactivate it instead of renaming it.")
    item.name, item.active, item.updated_at = name, active, _now()
    db.commit()
    _audit(db, request, actor, "subject_updated", str(item.id), f"previous={previous}; name={name}; active={active}")
    db.refresh(item)
    return {"id": item.id, "name": item.name, "active": item.active, "created_at": item.created_at}


def _subject_is_referenced(db: Session, name: str) -> bool:
    needle = name.casefold()
    for profile in list(db.scalars(select(Student)).all()) + list(db.scalars(select(Tutor)).all()):
        if any(value.casefold() == needle for value in profile.subjects):
            return True
    for post in db.scalars(select(LearningPost)).all():
        if any(value.casefold() == needle for value in post.subjects):
            return True
    return False


@router.delete("/api/admin/subjects/{subject_id}")
def delete_subject(subject_id: int, request: Request, db: Session = Depends(get_db),
                   actor: UserAccount = Depends(_admin)) -> dict:
    item = db.get(ManagedSubject, subject_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Subject not found.")
    if _subject_is_referenced(db, item.name):
        raise HTTPException(status_code=409, detail="This subject is used by existing profiles or tutoring listings. Deactivate it instead.")
    db.delete(item)
    db.commit()
    _audit(db, request, actor, "subject_deleted", str(subject_id), f"name={needle}")
    return {"deleted": True, "subject_id": subject_id}
