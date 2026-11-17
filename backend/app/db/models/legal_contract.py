"""Immutable published texts and explicit B2B acceptance evidence, separate from payments."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from app.db.base import Base


class LegalBundle(Base):
    __tablename__ = "legal_bundles"
    id = Column(Integer, primary_key=True)
    version = Column(String(80), nullable=False, unique=True)
    content_hash = Column(String(64), nullable=False)
    publisher = Column(JSON, nullable=False)
    documents = Column(JSON, nullable=False)
    review_reference = Column(String(300), nullable=False)
    published_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class LegalAcceptance(Base):
    __tablename__ = "legal_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "bundle_id",
            "plan",
            "commercial_reference",
            name="uq_legal_acceptance_offer",
        ),
    )
    id = Column(Integer, primary_key=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id", ondelete="SET NULL"), index=True
    )
    bundle_id = Column(Integer, ForeignKey("legal_bundles.id"), nullable=False)
    accepted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    representative = Column(JSON, nullable=False)
    workspace_name = Column(String(255), nullable=False)
    plan = Column(String(20), nullable=False)
    commercial_reference = Column(String(200), nullable=False)
    content_hash = Column(String(64), nullable=False)
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
