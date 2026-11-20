"""Public business requests, accessible only to platform administrators."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    company = Column(String(200), nullable=False, default="")
    phone = Column(String(40), nullable=False, default="")
    plan = Column(String(20), nullable=False, default="")
    message = Column(Text, nullable=False)
    privacy_notice_version = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="new")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    opened_at = Column(DateTime)
    opened_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    acknowledgement_status = Column(String(20), nullable=False, default="not_requested")
    acknowledgement_queued_at = Column(DateTime)
    acknowledgement_sent_at = Column(DateTime)
    acknowledgement_error = Column(String(50))
    __table_args__ = (
        Index("ix_contact_inquiry_status_created", "status", "created_at"),
    )
