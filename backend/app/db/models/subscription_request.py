"""Commercial requests and durable administrative activation evidence."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.db.base import Base


class SubscriptionRequest(Base):
    __tablename__ = "subscription_requests"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    requested_value = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    decided_by = Column(Integer, ForeignKey("users.id"))
    decided_at = Column(DateTime)
    authorization_reference = Column(Text)
    previous_plan = Column(String(20))
