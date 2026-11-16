"""
User schemas with security validation
"""
from datetime import datetime
from typing import Optional, List
import re
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.models.user import Role


def validate_password_strength(password: str) -> str:
    """
    Validate password strength:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Le mot de passe doit contenir au moins une majuscule")
    if not re.search(r"[a-z]", password):
        raise ValueError("Le mot de passe doit contenir au moins une minuscule")
    if not re.search(r"\d", password):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Le mot de passe doit contenir au moins un caractère spécial (!@#$%^&*)")
    return password


def sanitize_string(value: str) -> str:
    """Sanitize string input to prevent XSS"""
    if not value:
        return value
    # Remove potentially dangerous characters
    dangerous = ['<', '>', '"', "'", '&', ';']
    for char in dangerous:
        value = value.replace(char, '')
    return value.strip()


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    role: Role = Role.VIEWER
    is_active: bool = True
    
    @field_validator('full_name')
    @classmethod
    def sanitize_full_name(cls, v):
        if v:
            return sanitize_string(v)
        return v


class UserCreate(UserBase):
    """Create user schema with strong password validation"""
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    """Update user schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    is_whitelisted: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    
    @field_validator('full_name')
    @classmethod
    def sanitize_full_name(cls, v):
        if v:
            return sanitize_string(v)
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v:
            return validate_password_strength(v)
        return v


class LinkedAccountResponse(BaseModel):
    """Linked SSO account"""
    provider: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User response schema"""
    id: int
    is_superuser: bool
    is_whitelisted: bool = False
    created_at: datetime
    last_login_at: Optional[datetime] = None
    auth_provider: Optional[str] = None
    avatar_url: Optional[str] = None
    linked_accounts: List[LinkedAccountResponse] = []

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    totp_code: Optional[str] = Field(default=None, max_length=40)  # Legacy TOTP/recovery only.


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login response - either tokens or 2FA required"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    temp_token: Optional[str] = None  # Temporary token to complete 2FA
    methods: List[str] = []
    destinations: dict = {}


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: str
    type: str
    exp: datetime
