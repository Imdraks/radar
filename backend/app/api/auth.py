"""
Authentication endpoints
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import get_db
from app.db.models.user import User, Role
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
)
from app.core.two_factor import two_factor_auth
from app.core.activity_logger import ActivityLogger, Actions
from app.schemas.user import UserLogin, Token, UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SetupCheck(BaseModel):
    """Response for setup check"""
    needs_setup: bool
    user_count: int


class InitialSetup(BaseModel):
    """Initial admin setup request"""
    email: EmailStr
    password: str
    full_name: str


@router.get("/setup-check", response_model=SetupCheck)
def check_needs_setup(db: Session = Depends(get_db)):
    """Check if initial setup is needed (no users exist)"""
    user_count = db.query(User).count()
    return SetupCheck(
        needs_setup=user_count == 0,
        user_count=user_count
    )


@router.post("/setup", response_model=UserResponse)
def initial_setup(
    data: InitialSetup,
    db: Session = Depends(get_db)
):
    """Create the first admin account (only works if no users exist)"""
    # Check if any users exist
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed. Use login instead.",
        )
    
    # Validate password
    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )
    
    # Create admin user
    admin = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=Role.ADMIN,
        is_active=True,
        is_superuser=True,
        is_whitelisted=True,  # Super admin is always whitelisted
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return admin


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    # Check whitelist - only superusers and whitelisted users can login
    if not user.is_superuser and not user.is_whitelisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé. Votre compte n'est pas autorisé. Contactez l'administrateur.",
        )
    
    # Log successful login
    ActivityLogger.log(
        db=db,
        user=user,
        action=Actions.LOGIN,
        details={"email": user.email},
        request=request,
    )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    user_id = verify_token(refresh_token, "refresh")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


# 2FA Models
class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: List[str]


class TwoFactorEnableRequest(BaseModel):
    code: str


class TwoFactorVerifyRequest(BaseModel):
    code: str


class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    has_backup_codes: bool


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
def get_2fa_status(
    current_user: User = Depends(get_current_user)
):
    """Check if 2FA is enabled for current user"""
    return TwoFactorStatusResponse(
        enabled=current_user.two_factor_enabled or False,
        has_backup_codes=bool(current_user.backup_codes)
    )


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize 2FA setup. Returns QR code and backup codes.
    User must confirm with /2fa/enable endpoint.
    """
    # Generate new secret
    secret = two_factor_auth.generate_secret()
    
    # Generate QR code
    qr_code = two_factor_auth.generate_qr_code(secret, current_user.email)
    
    # Generate backup codes
    backup_codes = two_factor_auth.generate_backup_codes(10)
    
    # Store pending secret (not yet enabled)
    current_user.two_factor_secret = secret
    current_user.backup_codes = backup_codes
    db.commit()
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes
    )


@router.post("/2fa/enable")
def enable_2fa(
    data: TwoFactorEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enable 2FA after verifying the first code from authenticator app.
    """
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /2fa/setup first."
        )
    
    # Verify the code
    if not two_factor_auth.verify_code(current_user.two_factor_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Enable 2FA
    current_user.two_factor_enabled = True
    db.commit()
    
    return {"status": "success", "message": "2FA enabled successfully"}


@router.post("/2fa/disable")
def disable_2fa(
    data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA (requires current 2FA code).
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    # Verify the code
    if not two_factor_auth.verify_code(current_user.two_factor_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.backup_codes = None
    db.commit()
    
    return {"status": "success", "message": "2FA disabled successfully"}


@router.post("/2fa/verify")
def verify_2fa_code(
    data: TwoFactorVerifyRequest,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Verify 2FA code during login (called after password verification).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Try TOTP code first
    if two_factor_auth.verify_code(user.two_factor_secret, data.code):
        return {"status": "success", "verified": True}
    
    # Try backup code
    if user.backup_codes:
        is_valid, used_code = two_factor_auth.verify_backup_code(
            data.code, 
            user.backup_codes
        )
        if is_valid and used_code:
            # Remove used backup code
            user.backup_codes = [c for c in user.backup_codes if c != used_code]
            db.commit()
            return {
                "status": "success", 
                "verified": True,
                "backup_code_used": True,
                "remaining_backup_codes": len(user.backup_codes)
            }
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid verification code"
    )


@router.post("/2fa/regenerate-backup-codes")
def regenerate_backup_codes(
    data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate new backup codes (requires current 2FA code).
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    # Verify the code
    if not two_factor_auth.verify_code(current_user.two_factor_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Generate new backup codes
    new_codes = two_factor_auth.generate_backup_codes(10)
    current_user.backup_codes = new_codes
    db.commit()
    
    return {"status": "success", "backup_codes": new_codes}
