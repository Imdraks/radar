"""WebAuthn credentials and short-lived, single-use, account-bound ceremonies."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    LargeBinary,
    DateTime,
    ForeignKey,
    BigInteger,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_id = Column(LargeBinary, nullable=False, unique=True)
    public_key = Column(LargeBinary, nullable=False)
    sign_count = Column(BigInteger, nullable=False, default=0)
    name = Column(String(80), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    revoked_at = Column(DateTime)
    user = relationship("User", back_populates="passkeys")


class PasskeyChallenge(Base):
    __tablename__ = "passkey_challenges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose = Column(String(20), nullable=False)
    challenge = Column(LargeBinary, nullable=False)
    auth_version = Column(Integer, nullable=False)
    parent_token_hash = Column(String(64))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    __table_args__ = (
        Index("ix_passkey_challenge_user_created", "user_id", "created_at"),
    )
