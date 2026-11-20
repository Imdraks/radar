"""Platform client provisioning and password delivery state; never plaintext secrets."""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ClientInvitation(Base):
    __tablename__ = "client_invitations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    kind = Column(String(24), nullable=False)  # account_setup or workspace_access
    status = Column(String(24), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent_at = Column(DateTime)
    expires_at = Column(DateTime)
    error_code = Column(
        String(80)
    )  # Stable operational code; never provider payload/credentials.
    __table_args__ = (
        Index("ix_client_invitation_workspace_created", "workspace_id", "created_at"),
    )
