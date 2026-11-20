"""Workspace-scoped reusable production plans and expiring deliverable reviews."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from app.db.base import Base


class ProductionTemplate(Base):
    __tablename__ = "production_templates"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    kind = Column(String(20), nullable=False)
    definition = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeliverableReview(Base):
    __tablename__ = "deliverable_reviews"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    deliverable_id = Column(
        Integer, ForeignKey("deliverables.id"), nullable=False, index=True
    )
    approval_id = Column(Integer, ForeignKey("approvals.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    fingerprint = Column(String(64), nullable=False)
    snapshot = Column(JSON, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    reviewer_name = Column(String(200))
    feedback = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at = Column(DateTime)
