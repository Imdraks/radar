"""Radar's own customer quotes and external contract evidence, separate from agency billing."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    JSON,
    Numeric,
    ForeignKey,
    LargeBinary,
    Index,
)
from sqlalchemy.orm import deferred
from app.core.encrypted_binary import EncryptedBinary
from app.db.base import Base


class PlatformQuote(Base):
    __tablename__ = "platform_quotes"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id", ondelete="SET NULL"), index=True
    )
    order_id = Column(
        Integer, ForeignKey("subscription_requests.id", ondelete="SET NULL")
    )
    status = Column(String(20), nullable=False, default="draft")
    issuer = Column(JSON, nullable=False)
    buyer = Column(JSON, nullable=False)
    lines = Column(JSON, nullable=False)
    total_ht = Column(Numeric(16, 2), nullable=False)
    total_tax = Column(Numeric(16, 2), nullable=False)
    total_ttc = Column(Numeric(16, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    valid_until = Column(Date, nullable=False)
    notes = Column(String(3000), nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    issued_at = Column(DateTime)
    content_hash = Column(String(64))

    @property
    def reference(self):
        year = (
            self.created_at.replace(tzinfo=timezone.utc)
            .astimezone(ZoneInfo("Europe/Paris"))
            .year
        )
        return f"RAD-DEV-{year}-{self.id:06d}"


class ExternalClientContract(Base):
    __tablename__ = "external_client_contracts"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id", ondelete="SET NULL"), index=True
    )
    order_id = Column(
        Integer,
        ForeignKey("subscription_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    quote_id = Column(Integer, ForeignKey("platform_quotes.id", ondelete="SET NULL"))
    plan = Column(String(20))
    reference = Column(String(200), nullable=False)
    signer = Column(String(255), nullable=False)
    signed_on = Column(Date, nullable=False)
    status = Column(String(24), nullable=False, default="pending_review")
    document = deferred(Column(EncryptedBinary("platform-contract"), nullable=False))
    document_hash = Column(String(64), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    review_reference = Column(String(1000))
