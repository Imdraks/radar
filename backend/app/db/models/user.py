"""
User and Role models
"""
import uuid
import secrets
import string
from datetime import datetime
from enum import Enum as PyEnum
from app.core.encrypted_binary import EncryptedBinary
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, JSON, Integer, BigInteger, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, deferred

from app.db.base import Base


def generate_tracking_id():
    """Generate a unique tracking ID like USR-A1B2C3"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(chars) for _ in range(6))
    return f"USR-{code}"


class Role(str, PyEnum):
    """User roles for RBAC"""
    ADMIN = "admin"
    BIZDEV = "bizdev"
    PM = "pm"
    VIEWER = "viewer"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tracking_id = Column(String(15), unique=True, default=generate_tracking_id, index=True)  # Hidden ID for superadmin
    email = Column(String(255), unique=True, index=True, nullable=True)  # Nullable for SSO without email
    hashed_password = Column(String(255), nullable=True)  # Nullable for SSO users
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_whitelisted = Column(Boolean, default=False)  # Only whitelisted users can login
    
    is_collaborator = Column(Boolean, nullable=False, default=False, server_default='false')

    # New client owners must replace their one-time credential before workspace access.
    must_change_password = Column(Boolean, nullable=False, default=False, server_default='false')
    temporary_password_expires_at = Column(DateTime, nullable=True)
    security_setup_pending = Column(Boolean, nullable=False, default=False, server_default='false')

    # SSO fields
    auth_provider = Column(String(50), default='credentials')  # 'credentials' | 'google' | 'apple'
    avatar_url = Column(String(500), nullable=True)  # Profile picture from SSO
    avatar_image = deferred(Column(EncryptedBinary("user-avatar"), nullable=True))  # Sanitized JPEG, max 64 KiB

    @property
    def profile_avatar_url(self):
        if self.avatar_image:
            import base64
            return 'data:image/jpeg;base64,' + base64.b64encode(self.avatar_image).decode('ascii')
        return self.avatar_url
    
    # 2FA fields
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)
    backup_codes = Column(JSON, nullable=True)  # List of backup codes
    mfa_email_enabled = Column(Boolean, nullable=False, default=False, server_default='false')
    mfa_email = Column(String(500), nullable=True)  # Encrypted verified address, bound at enrollment.
    mfa_sms_enabled = Column(Boolean, nullable=False, default=False, server_default='false')
    mfa_phone = Column(String(255), nullable=True)  # Encrypted verified E.164 number.
    mfa_version = Column(Integer, nullable=False, default=0, server_default='0')
    mfa_totp_last_step = Column(BigInteger, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    passkeys = relationship("PasskeyCredential", back_populates="user", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    assigned_opportunities = relationship(
        "Opportunity",
        back_populates="assigned_to",
        foreign_keys="Opportunity.assigned_to_user_id"
    )
    notes = relationship("OpportunityNote", back_populates="author")
    tasks = relationship("OpportunityTask", back_populates="assigned_to")
    
    def __repr__(self):
        return f"<User {self.email}>"
