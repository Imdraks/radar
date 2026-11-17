"""Immutable full credit notes; bank refunds remain separate, never simulated."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    JSON,
    UniqueConstraint,
)
from app.db.base import Base


class CreditNote(Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        UniqueConstraint("workspace_id", "reference", name="uq_credit_reference"),
        UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_credit_idempotency"
        ),
    )
    id = Column(Integer, primary_key=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, unique=True)
    reference = Column(String(50), nullable=False)
    idempotency_key = Column(String(80), nullable=False)
    issue_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    snapshot = Column(JSON, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
