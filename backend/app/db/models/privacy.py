"""Rights requests are case records, never automatic deletion instructions."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.db.base import Base


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind = Column(String(30), nullable=False)
    scope = Column(String(20), nullable=False)
    details = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="received")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    response_due_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    response = Column(Text, nullable=True)
    audit_log = Column(JSON, nullable=False, default=list)
