"""Voluntary, explicitly accepted First Admin ownership transfer.

Flow: the current First Admin starts a transfer (password re-entry and the recipient's exact email),
an eligible existing Admin accepts within 24 hours, and the switch happens in one transaction so that
exactly one active First Admin exists afterwards. The former First Admin stays an ordinary Admin.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    enforce_auth_rate_limit, record_security_event, require_roles, timestamp, utc_now, verify_password,
)
from ..database import get_db
from ..models import FirstAdminTransfer, RefreshSession, UserAccount

router = APIRouter(tags=["First Admin transfer"])
TRANSFER_WINDOW = timedelta(hours=24)


class FirstAdminTransferStart(BaseModel):
    recipient_email: str = Field(min_length=3, max_length=255)
    confirm_recipient_email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


def _payload(row: FirstAdminTransfer, db: Session) -> dict:
    initiator = db.get(UserAccount, row.initiated_by_account_id)
    recipient = db.get(UserAccount, row.recipient_account_id)
    return {
        "id": row.id,
        "status": row.status,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "responded_at": row.responded_at,
        "initiator_email": initiator.email if initiator else None,
        "recipient_email": recipient.email if recipient else None,
    }


def _current_pending(db: Session) -> FirstAdminTransfer | None:
    """Return the pending transfer, marking it expired if its window has passed."""
    row = db.scalar(select(FirstAdminTransfer).where(FirstAdminTransfer.status == "pending").with_for_update())
    if row is None:
        return None
    if row.expires_at <= timestamp():
        row.status = "expired"
        row.responded_at = timestamp()
        db.commit()
        return None
    return row


def _eligible_recipient(recipient: UserAccount | None) -> bool:
    return (
        recipient is not None and recipient.role == "admin" and recipient.status == "active"
        and not recipient.is_first_admin
    )


@router.get("/api/admin/first-admin-transfer")
def get_first_admin_transfer(db: Session = Depends(get_db),
                             actor: UserAccount = Depends(require_roles("admin"))) -> dict:
    row = _current_pending(db)
    visible = row is not None and (actor.is_first_admin or row.recipient_account_id == actor.id)
    return {"pending": _payload(row, db) if visible else None,
            "can_start": actor.is_first_admin and row is None}


@router.post("/api/admin/first-admin-transfer", status_code=201)
def start_first_admin_transfer(payload: FirstAdminTransferStart, request: Request,
                               db: Session = Depends(get_db),
                               actor: UserAccount = Depends(require_roles("admin"))) -> dict:
    if not actor.is_first_admin:
        raise HTTPException(status_code=403, detail="Only the current First Admin can start an ownership transfer.")
    enforce_auth_rate_limit(
        db, request, "first_admin_transfer_start",
        limit_env="FIRST_ADMIN_TRANSFER_MAX_ATTEMPTS", window_env="FIRST_ADMIN_TRANSFER_WINDOW_SECONDS",
        default_limit=5, default_window_seconds=3600,
    )
    if not verify_password(payload.password, actor.password_hash):
        record_security_event(db, "first_admin_transfer_password_failed", request, account_id=actor.id)
        raise HTTPException(status_code=403, detail="Password confirmation failed.")
    recipient_email = payload.recipient_email.strip().lower()
    if recipient_email != payload.confirm_recipient_email.strip().lower():
        raise HTTPException(status_code=422, detail="The recipient email confirmation does not match.")
    recipient = db.scalar(select(UserAccount).where(UserAccount.email == recipient_email))
    if recipient is None or recipient.id == actor.id:
        raise HTTPException(status_code=422, detail="Choose another existing Admin account as the recipient.")
    if not _eligible_recipient(recipient):
        raise HTTPException(status_code=422, detail="The recipient must be an active Admin account (not a Student, Tutor, Moderator, suspended or First Admin account).")
    if _current_pending(db) is not None:
        raise HTTPException(status_code=409, detail="A First Admin transfer is already pending.")

    now = utc_now()
    row = FirstAdminTransfer(
        initiated_by_account_id=actor.id, recipient_account_id=recipient.id, status="pending",
        created_at=now.isoformat(), expires_at=(now + TRANSFER_WINDOW).isoformat(),
    )
    db.add(row)
    db.commit()
    record_security_event(db, "first_admin_transfer_started", request, account_id=actor.id,
                          attempted_email=recipient.email,
                          details=f"transfer_id={row.id}; recipient_account_id={recipient.id}")
    return _payload(row, db)


@router.delete("/api/admin/first-admin-transfer")
def cancel_first_admin_transfer(request: Request, db: Session = Depends(get_db),
                                actor: UserAccount = Depends(require_roles("admin"))) -> dict:
    row = _current_pending(db)
    if row is None:
        raise HTTPException(status_code=404, detail="No First Admin transfer is pending.")
    if row.initiated_by_account_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the initiating First Admin can cancel this transfer.")
    row.status = "cancelled"
    row.responded_at = timestamp()
    db.commit()
    record_security_event(db, "first_admin_transfer_cancelled", request, account_id=actor.id,
                          details=f"transfer_id={row.id}")
    return {"status": "cancelled"}


@router.post("/api/admin/first-admin-transfer/accept")
def accept_first_admin_transfer(request: Request, db: Session = Depends(get_db),
                                actor: UserAccount = Depends(require_roles("admin"))) -> dict:
    row = _current_pending(db)
    if row is None:
        raise HTTPException(status_code=409, detail="No First Admin transfer is pending, or it has expired.")
    if row.recipient_account_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the named recipient can accept this transfer.")
    initiator = db.get(UserAccount, row.initiated_by_account_id)
    if initiator is None or not initiator.is_first_admin:
        row.status = "cancelled"
        row.responded_at = timestamp()
        db.commit()
        raise HTTPException(status_code=409, detail="The transfer is no longer valid because the First Admin changed.")
    if not _eligible_recipient(actor):
        raise HTTPException(status_code=409, detail="Your account is no longer eligible to receive the First Admin role.")

    now = timestamp()
    initiator.is_first_admin = False
    actor.is_first_admin = True
    row.status = "accepted"
    row.responded_at = now
    sessions = db.scalars(select(RefreshSession).where(
        RefreshSession.account_id.in_([initiator.id, actor.id]),
        RefreshSession.revoked_at.is_(None),
    )).all()
    for session in sessions:
        session.revoked_at = now
    db.flush()
    if sum(1 for account in db.scalars(select(UserAccount).where(UserAccount.is_first_admin.is_(True))).all()) != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="The transfer could not be completed safely; no change was made.")
    db.commit()
    record_security_event(db, "first_admin_transfer_accepted", request, account_id=actor.id,
                          attempted_email=initiator.email,
                          details=f"transfer_id={row.id}; former_first_admin_account_id={initiator.id}; "
                                  f"former_first_admin_role=admin; new_first_admin_account_id={actor.id}; "
                                  f"sessions_revoked={len(sessions)}")
    return {"status": "accepted", "former_first_admin_role": initiator.role, "you_are_first_admin": True}


@router.post("/api/admin/first-admin-transfer/decline")
def decline_first_admin_transfer(request: Request, db: Session = Depends(get_db),
                                 actor: UserAccount = Depends(require_roles("admin"))) -> dict:
    row = _current_pending(db)
    if row is None:
        raise HTTPException(status_code=409, detail="No First Admin transfer is pending, or it has expired.")
    if row.recipient_account_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the named recipient can decline this transfer.")
    row.status = "declined"
    row.responded_at = timestamp()
    db.commit()
    record_security_event(db, "first_admin_transfer_declined", request, account_id=actor.id,
                          details=f"transfer_id={row.id}")
    return {"status": "declined"}
