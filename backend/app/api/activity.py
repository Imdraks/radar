"""Recorded activity, filtered and paginated; explicit platform rights are required."""

from datetime import datetime, timedelta, date, time, timezone
from typing import Optional, List
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, case, or_
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_platform_admin
from app.db.models import User, ActivityLog
from app.services.activity_projection import safe_details

router = APIRouter()


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: Optional[int] = None
    user_tracking_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime


class UserWithTrackingId(BaseModel):
    id: int
    tracking_id: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    is_whitelisted: bool
    last_login_at: Optional[datetime]
    created_at: datetime


def rows_query(db):
    return db.query(ActivityLog, User).outerjoin(User, ActivityLog.user_id == User.id)


def project(row, user):
    return ActivityLogResponse(
        id=row.id,
        user_id=row.user_id,
        user_tracking_id=row.user_tracking_id,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        details=safe_details(row.details),
        ip_address=row.ip_address,
        created_at=row.created_at,
    )


def ordered(query):
    return query.order_by(desc(ActivityLog.created_at), desc(ActivityLog.id))


def utc_naive(value):
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    )


@router.get("/logs/search")
def search_logs(
    q: str = Query("", max_length=100),
    author_id: Optional[int] = Query(None, gt=0),
    unassigned: bool = False,
    action: Optional[str] = Query(None, max_length=100),
    resource_type: Optional[str] = Query(None, max_length=100),
    since_hours: Optional[int] = Query(None, ge=1, le=744),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    if from_date == date.min:
        raise HTTPException(422, "La date de début dépasse la limite prise en charge.")
    if to_date == date.max:
        raise HTTPException(422, "La date de fin dépasse la limite prise en charge.")
    if from_date and to_date and from_date > to_date:
        raise HTTPException(422, "La date de début doit précéder la date de fin.")
    if since_hours and (from_date or to_date):
        raise HTTPException(
            422, "Choisissez une période relative ou des dates précises."
        )
    if author_id and unassigned:
        raise HTTPException(422, "Choisissez un seul filtre d’auteur.")
    query = rows_query(db)
    if q.strip():
        term = (
            "%"
            + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        query = query.filter(
            or_(
                *(
                    column.ilike(term, escape="\\")
                    for column in [
                        User.email,
                        User.full_name,
                        ActivityLog.user_tracking_id,
                        ActivityLog.action,
                        ActivityLog.resource_id,
                    ]
                )
            )
        )
    if author_id:
        query = query.filter(ActivityLog.user_id == author_id)
    if unassigned:
        query = query.filter(ActivityLog.user_id.is_(None))
    if action:
        query = query.filter(ActivityLog.action == action)
    if resource_type:
        query = query.filter(ActivityLog.resource_type == resource_type)
    if since_hours:
        query = query.filter(
            ActivityLog.created_at >= datetime.utcnow() - timedelta(hours=since_hours)
        )
    if from_date:
        start = datetime.combine(from_date, time.min, tzinfo=ZoneInfo("Europe/Paris"))
        query = query.filter(ActivityLog.created_at >= utc_naive(start))
    if to_date:
        end = datetime.combine(
            to_date + timedelta(days=1), time.min, tzinfo=ZoneInfo("Europe/Paris")
        )
        query = query.filter(ActivityLog.created_at < utc_naive(end))
    total, authors, logins, last = query.with_entities(
        func.count(ActivityLog.id),
        func.count(func.distinct(ActivityLog.user_id)),
        func.coalesce(func.sum(case((ActivityLog.action == "login", 1), else_=0)), 0),
        func.max(ActivityLog.created_at),
    ).one()
    items = [
        project(row, user)
        for row, user in ordered(query).offset((page - 1) * limit).limit(limit).all()
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "summary": {"authors": authors, "logins": logins, "last_event_at": last},
    }


@router.get("/logs/filters")
def log_filters(
    db: Session = Depends(get_db), admin: User = Depends(get_current_platform_admin)
):
    authors = (
        db.query(User.id, User.full_name, User.email)
        .join(ActivityLog, ActivityLog.user_id == User.id)
        .distinct()
        .order_by(User.full_name, User.id)
        .limit(1000)
        .all()
    )
    return {
        "authors": [
            {"id": row.id, "name": row.full_name, "email": row.email} for row in authors
        ],
        "actions": [
            row[0]
            for row in db.query(ActivityLog.action)
            .filter(ActivityLog.action != "")
            .distinct()
            .order_by(ActivityLog.action)
            .all()
        ],
        "resource_types": [
            row[0]
            for row in db.query(ActivityLog.resource_type)
            .filter(
                ActivityLog.resource_type.is_not(None), ActivityLog.resource_type != ""
            )
            .distinct()
            .order_by(ActivityLog.resource_type)
            .all()
        ],
    }


@router.get("/logs", response_model=List[ActivityLogResponse])
def get_activity_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_tracking_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    since_hours: Optional[int] = Query(None, ge=1, le=168),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    query = rows_query(db)
    if user_tracking_id:
        query = query.filter(ActivityLog.user_tracking_id == user_tracking_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    if resource_type:
        query = query.filter(ActivityLog.resource_type == resource_type)
    if since_hours:
        query = query.filter(
            ActivityLog.created_at >= datetime.utcnow() - timedelta(hours=since_hours)
        )
    return [
        project(row, user)
        for row, user in ordered(query).offset(offset).limit(limit).all()
    ]


@router.get("/logs/stream")
def get_logs_stream(
    since: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    cutoff = utc_naive(since) if since else datetime.utcnow() - timedelta(minutes=5)
    logs = [
        project(row, user)
        for row, user in ordered(rows_query(db).filter(ActivityLog.created_at > cutoff))
        .limit(limit)
        .all()
    ]
    return {
        "logs": logs,
        "count": len(logs),
        "server_time": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/users/tracking", response_model=List[UserWithTrackingId])
def get_users_with_tracking(
    db: Session = Depends(get_db), admin: User = Depends(get_current_platform_admin)
):
    return [
        UserWithTrackingId(
            id=u.id,
            tracking_id=u.tracking_id or f"USR-{str(u.id)[:6].upper()}",
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if u.role else "viewer",
            is_active=bool(u.is_active),
            is_whitelisted=bool(u.is_whitelisted),
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in db.query(User).order_by(desc(User.created_at)).all()
    ]


@router.get("/logs/stats")
def get_activity_stats(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    query = db.query(ActivityLog).filter(
        ActivityLog.created_at >= datetime.utcnow() - timedelta(hours=hours)
    )
    actions = (
        query.with_entities(ActivityLog.action, func.count(ActivityLog.id))
        .group_by(ActivityLog.action)
        .all()
    )
    authors = query.with_entities(
        func.count(func.distinct(ActivityLog.user_id))
    ).scalar()
    return {
        "period_hours": hours,
        "total_logs": sum(row[1] for row in actions),
        "active_users": authors,
        "actions": dict(actions),
    }
