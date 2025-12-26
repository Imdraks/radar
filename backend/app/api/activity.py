"""
Activity logs API - Superadmin only
Real-time user activity tracking
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db.models import User, ActivityLog

router = APIRouter()


class ActivityLogResponse(BaseModel):
    """Activity log response"""
    id: UUID
    user_tracking_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserWithTrackingId(BaseModel):
    """User with tracking ID for admin view"""
    id: UUID
    tracking_id: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    is_whitelisted: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/logs", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_tracking_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    since_hours: Optional[int] = Query(None, ge=1, le=168),  # Max 7 days
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get activity logs - Superadmin only
    
    - **limit**: Number of logs to return (max 500)
    - **offset**: Pagination offset
    - **user_tracking_id**: Filter by user tracking ID
    - **action**: Filter by action type
    - **resource_type**: Filter by resource type
    - **since_hours**: Get logs from last N hours
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    query = db.query(ActivityLog).join(User, ActivityLog.user_id == User.id, isouter=True)
    
    if user_tracking_id:
        query = query.filter(ActivityLog.user_tracking_id == user_tracking_id)
    
    if action:
        query = query.filter(ActivityLog.action == action)
    
    if resource_type:
        query = query.filter(ActivityLog.resource_type == resource_type)
    
    if since_hours:
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        query = query.filter(ActivityLog.created_at >= since_time)
    
    logs = query.order_by(desc(ActivityLog.created_at)).offset(offset).limit(limit).all()
    
    # Enrich with user info
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        result.append(ActivityLogResponse(
            id=log.id,
            user_tracking_id=log.user_tracking_id,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at,
        ))
    
    return result


@router.get("/logs/stream")
async def get_logs_stream(
    since: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent logs since a timestamp (for polling)
    Returns logs newer than 'since' parameter
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    query = db.query(ActivityLog).join(User, ActivityLog.user_id == User.id, isouter=True)
    
    if since:
        query = query.filter(ActivityLog.created_at > since)
    else:
        # Default: last 5 minutes
        since_time = datetime.utcnow() - timedelta(minutes=5)
        query = query.filter(ActivityLog.created_at >= since_time)
    
    logs = query.order_by(desc(ActivityLog.created_at)).limit(limit).all()
    
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        result.append({
            "id": str(log.id),
            "user_tracking_id": log.user_tracking_id,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        })
    
    return {
        "logs": result,
        "count": len(result),
        "server_time": datetime.utcnow().isoformat(),
    }


@router.get("/users/tracking", response_model=List[UserWithTrackingId])
async def get_users_with_tracking(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all users with their tracking IDs - Superadmin only"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    users = db.query(User).order_by(desc(User.created_at)).all()
    
    return [
        UserWithTrackingId(
            id=u.id,
            tracking_id=u.tracking_id or f"USR-{str(u.id)[:6].upper()}",
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if u.role else "viewer",
            is_active=u.is_active,
            is_whitelisted=u.is_whitelisted,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/logs/stats")
async def get_activity_stats(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get activity statistics for the last N hours"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    since_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get counts by action
    from sqlalchemy import func
    
    action_counts = db.query(
        ActivityLog.action,
        func.count(ActivityLog.id).label('count')
    ).filter(
        ActivityLog.created_at >= since_time
    ).group_by(ActivityLog.action).all()
    
    # Get active users
    active_users = db.query(
        func.count(func.distinct(ActivityLog.user_id))
    ).filter(
        ActivityLog.created_at >= since_time
    ).scalar()
    
    # Get total logs
    total_logs = db.query(func.count(ActivityLog.id)).filter(
        ActivityLog.created_at >= since_time
    ).scalar()
    
    return {
        "period_hours": hours,
        "total_logs": total_logs,
        "active_users": active_users,
        "actions": {action: count for action, count in action_counts},
    }
