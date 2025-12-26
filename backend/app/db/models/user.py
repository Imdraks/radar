"""
User and Role models
"""
import uuid
import secrets
import string
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_id = Column(String(15), unique=True, default=generate_tracking_id, index=True)  # Hidden ID for superadmin
    email = Column(String(255), unique=True, index=True, nullable=True)  # Nullable for SSO without email
    hashed_password = Column(String(255), nullable=True)  # Nullable for SSO users
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_whitelisted = Column(Boolean, default=False)  # Only whitelisted users can login
    
    # SSO fields
    auth_provider = Column(String(50), default='credentials')  # 'credentials' | 'google' | 'apple'
    avatar_url = Column(String(500), nullable=True)  # Profile picture from SSO
    
    # 2FA fields
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)
    backup_codes = Column(JSON, nullable=True)  # List of backup codes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
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
