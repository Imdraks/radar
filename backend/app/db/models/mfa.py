"""Short-lived account security proofs. Never store raw codes or bearer challenges."""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class MFAChallenge(Base):
    __tablename__ = 'mfa_challenges'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    purpose = Column(String(30), nullable=False)
    method = Column(String(20), nullable=True)
    code_hash = Column(String(64), nullable=True)
    pending_secret = Column(String(255), nullable=True)
    destination = Column(String(500), nullable=True)  # Encrypted; never returned raw.
    auth_version = Column(Integer, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    send_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_sent_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    __table_args__ = (Index('ix_mfa_user_created', 'user_id', 'created_at'),)
