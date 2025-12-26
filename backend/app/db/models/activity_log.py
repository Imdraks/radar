"""
Activity Log model for tracking user actions
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ActivityLog(Base):
    """Activity log for tracking all user actions"""
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User info
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_tracking_id = Column(String(10), nullable=False, index=True)  # Hidden ID like "USR-A1B2C3"
    
    # Action details
    action = Column(String(100), nullable=False, index=True)  # login, logout, view, create, update, delete, etc.
    resource_type = Column(String(100), nullable=True)  # opportunity, artist, dossier, etc.
    resource_id = Column(String(100), nullable=True)  # ID of the resource
    
    # Additional context
    details = Column(JSON, nullable=True)  # Extra details about the action
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", backref="activity_logs")
    
    def __repr__(self):
        return f"<ActivityLog {self.user_tracking_id} - {self.action}>"
