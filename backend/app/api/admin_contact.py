"""Platform inbox for requests submitted through the public contact form."""

from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.db import get_db
from app.api.deps import get_current_platform_admin
from app.db.models.user import User
from app.db.models.contact_inquiry import ContactInquiry
from app.db.models.activity_log import ActivityLog

router = APIRouter(prefix="/admin/contact-requests", tags=["Platform contact requests"])


def summary(row):
    return dict(
        id=str(row.id),
        name=row.name,
        email=row.email,
        company=row.company,
        plan=row.plan,
        status=row.status,
        created_at=row.created_at,
        opened_at=row.opened_at,
        acknowledgement_status=row.acknowledgement_status,
    )


def detail(row):
    return {
        **summary(row),
        "phone": row.phone,
        "message": row.message,
        "privacy_notice_version": row.privacy_notice_version,
        "opened_by": row.opened_by,
        "acknowledgement_queued_at": row.acknowledgement_queued_at,
        "acknowledgement_sent_at": row.acknowledgement_sent_at,
        "acknowledgement_error": row.acknowledgement_error,
    }


def find(db, id, lock=False):
    query = db.query(ContactInquiry).filter_by(id=id)
    row = (query.with_for_update().populate_existing() if lock else query).first()
    if not row:
        raise HTTPException(404, "Demande introuvable.")
    return row


def audit(db, user, row, action, values=None):
    db.add(
        ActivityLog(
            user_id=user.id,
            user_tracking_id=user.tracking_id or "SYSTEM",
            action=action,
            resource_type="contact_inquiry",
            resource_id=str(row.id),
            details=values or {},
        )
    )


def enqueue(db, row):
    from app.workers.contact_tasks import acknowledge_opened_request

    try:
        acknowledge_opened_request.delay(str(row.id))
    except Exception:
        # The request remains accessible when the broker is unavailable.
        row = find(db, row.id, True)
        if row.acknowledgement_status == "pending":
            row.acknowledgement_status = "failed"
            row.acknowledgement_error = "QUEUE_UNAVAILABLE"
            db.commit()
    db.refresh(row)
    return detail(row)


@router.get("")
def list_requests(
    q: str = Query("", max_length=100),
    status: Literal["all", "new", "opened", "closed"] = "all",
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    query = db.query(ContactInquiry)
    if status != "all":
        query = query.filter(ContactInquiry.status == status)
    if q.strip():
        needle = (
            "%"
            + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        query = query.filter(
            or_(
                ContactInquiry.name.ilike(needle, escape="\\"),
                ContactInquiry.email.ilike(needle, escape="\\"),
                ContactInquiry.company.ilike(needle, escape="\\"),
            )
        )
    return {
        "items": [
            summary(row)
            for row in query.order_by(
                ContactInquiry.created_at.desc(), ContactInquiry.id
            )
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        ],
        "total": query.count(),
        "new_count": db.query(ContactInquiry).filter_by(status="new").count(),
        "page": page,
        "limit": limit,
    }


@router.get("/count")
def new_count(
    db: Session = Depends(get_db), admin: User = Depends(get_current_platform_admin)
):
    return {"new_count": db.query(ContactInquiry).filter_by(status="new").count()}


@router.get("/{id}")
def get_request(
    id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    return detail(find(db, id))


@router.post("/{id}/open")
def open_request(
    id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    row = find(db, id, True)
    first = row.opened_at is None
    if first:
        row.opened_at = datetime.utcnow()
        row.opened_by = admin.id
        row.status = "opened"
        row.acknowledgement_status = "pending"
        row.acknowledgement_queued_at = datetime.utcnow()
        audit(db, admin, row, "contact.opened")
        db.commit()
        return enqueue(db, row)
    return detail(row)


class UpdateStatus(BaseModel):
    status: Literal["opened", "closed"]


@router.patch("/{id}")
def set_status(
    id: UUID,
    data: UpdateStatus,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    row = find(db, id, True)
    if not row.opened_at:
        raise HTTPException(409, "Ouvrez d’abord le dossier.")
    if row.status != data.status:
        before = row.status
        row.status = data.status
        audit(
            db,
            admin,
            row,
            "contact.status_changed",
            {"previous": before, "status": row.status},
        )
        db.commit()
    return detail(row)


@router.post("/{id}/retry-acknowledgement", status_code=202)
def retry_acknowledgement(
    id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    row = find(db, id, True)
    if not row.opened_at or row.acknowledgement_status != "failed":
        raise HTTPException(409, "Seul un envoi en échec peut être relancé.")
    if (
        row.acknowledgement_queued_at
        and row.acknowledgement_queued_at > datetime.utcnow() - timedelta(seconds=60)
    ):
        raise HTTPException(
            429, "Attendez une minute avant de relancer l’accusé d’ouverture."
        )
    row.acknowledgement_status = "pending"
    row.acknowledgement_error = None
    row.acknowledgement_queued_at = datetime.utcnow()
    audit(db, admin, row, "contact.acknowledgement_retry_requested")
    db.commit()
    return enqueue(db, row)
