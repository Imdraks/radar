"""
Activity logging service for tracking user actions
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Request

from app.db.models import ActivityLog, User


class ActivityLogger:
    """Service for logging user activities"""
    
    @staticmethod
    def log(
        db: Session,
        user: User,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        request: Optional[Request] = None,
    ) -> ActivityLog:
        """
        Log a user activity
        
        Args:
            db: Database session
            user: The user performing the action
            action: Action type (login, logout, view, create, update, delete, etc.)
            resource_type: Type of resource being accessed
            resource_id: ID of the resource
            details: Additional context
            request: FastAPI request for IP and user agent
        """
        # Get IP and user agent from request if available
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        
        log_entry = ActivityLog(
            user_id=user.id,
            user_tracking_id=user.tracking_id or f"USR-{str(user.id)[:6].upper()}",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        return log_entry
    
    @staticmethod
    def log_async(
        db: Session,
        user: User,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ActivityLog:
        """Log activity without request object (for background tasks)"""
        log_entry = ActivityLog(
            user_id=user.id,
            user_tracking_id=user.tracking_id or f"USR-{str(user.id)[:6].upper()}",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        return log_entry


# Actions constants for consistency
class Actions:
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    # CRUD
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    
    # Specific actions
    ANALYZE = "analyze"
    EXPORT = "export"
    ENRICH = "enrich"
    SEARCH = "search"
    RADAR_TRIGGER = "radar_trigger"
    
    # Admin actions
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    WHITELIST = "whitelist"
