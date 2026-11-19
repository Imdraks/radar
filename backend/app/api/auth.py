"""
Authentication endpoints
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from secrets import compare_digest
from app.core.config import settings
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
from app.schemas.user import UserLogin, Token, UserResponse, LoginResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SetupCheck(BaseModel):
    """Response for setup check"""
    needs_setup: bool
    user_count: int
    setup_enabled: bool


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
        user_count=user_count,
        setup_enabled=bool(settings.bootstrap_token),
    )


@router.post("/setup", response_model=UserResponse)
def initial_setup(
    data: InitialSetup,
    db: Session = Depends(get_db),
    bootstrap_token: str = Header(default="", alias="X-Radar-Bootstrap-Token"),
):
    """Create the first admin account (only works if no users exist)"""
    if not settings.bootstrap_token or not compare_digest(bootstrap_token, settings.bootstrap_token):
        raise HTTPException(403, "Initialisation réservée à l’opérateur de la plateforme")
    return create_initial_admin(db, data)


def create_initial_admin(db: Session, data: InitialSetup):
    # Serialize setup across workers; the second concurrent attempt observes the first commit.
    db.execute(text("SELECT pg_advisory_xact_lock(7243321801)"))
    # Check if any users exist
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed. Use login instead.",
        )
    
    # Validate password (strong requirements)
    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    import re
    if not re.search(r'[A-Z]', data.password):
        raise HTTPException(status_code=400, detail="Password must contain an uppercase letter")
    if not re.search(r'[a-z]', data.password):
        raise HTTPException(status_code=400, detail="Password must contain a lowercase letter")
    if not re.search(r'[0-9]', data.password):
        raise HTTPException(status_code=400, detail="Password must contain a number")
    if not re.search(r'[^A-Za-z0-9]', data.password):
        raise HTTPException(status_code=400, detail="Password must contain a special character")
    
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


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens"""
    user = db.query(User).filter(User.email == credentials.email).with_for_update().first()
    
    if not user or not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.must_change_password and (not user.temporary_password_expires_at or user.temporary_password_expires_at <= datetime.utcnow()):
        raise HTTPException(401, 'Le mot de passe temporaire a expiré. Demandez une nouvelle invitation ou utilisez le lien de récupération.')

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
    
    from app.core import mfa
    user = mfa.lock_user(db, user.id)
    from app.core.login_sessions import trusted
    if mfa.methods(user) and not trusted(db, user, request):
        token, challenge = mfa.create_challenge(db, user, 'login')
        if not credentials.totp_code:
            db.commit()
            return LoginResponse(requires_2fa=True, temp_token=token, **mfa.options(user))
        # Compatibility for existing TOTP/recovery clients. Delivered codes require
        # the explicit challenge API and must never be guessed from a user ID.
        code = credentials.totp_code.strip()
        normalized = code.replace(' ', '').replace('-', '')
        method = 'totp' if len(normalized) == 6 and normalized.isascii() and normalized.isdigit() else 'recovery'
        mfa.verify(db, user, challenge, method, code)
    return finish_login(db, user, request)


def finish_login(db, user, request):
    # Freeze the revision whose factors were actually verified. Later ORM
    # refreshes/commits must not adopt a concurrently changed MFA policy.
    verified_version = user.mfa_version or 0
    # Auto-assign user to workspaces based on email invites
    from app.api.workspace import auto_assign_user_to_workspaces
    auto_assign_user_to_workspaces(db, user)
    
    db.refresh(user)
    if (user.mfa_version or 0) != verified_version or not user.is_active or not (user.is_whitelisted or user.is_superuser):
        raise HTTPException(401, 'La sécurité du compte a changé. Recommencez la connexion.')
    from app.core.mfa import issue_tokens, methods
    user.last_login_at = datetime.utcnow()
    tokens = issue_tokens(user, request=request)
    ActivityLogger.log(db=db, user=user, action=Actions.LOGIN,
        details={'email': user.email, '2fa_used': bool(methods(user))}, request=request)
    # Defer Drive provisioning until after every required login factor succeeds.
    from app.db.models.account import Account
    account = db.query(Account).filter(Account.user_id == user.id, Account.provider == 'google').first()
    if account:
        try:
            from app.workers.tasks import ensure_drive_structure_task
            from app.db.models.workspace import WorkspaceMember
            for member in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all():
                ensure_drive_structure_task.delay(user_id=user.id, workspace_id=member.workspace_id,
                                                 google_account_id=user.email)
        except Exception:
            import logging
            logging.getLogger(__name__).warning('Drive provisioning deferred after login')
    return LoginResponse(**tokens, requires_2fa=False)


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=Token)
def refresh_session(data: RefreshRequest, db: Session = Depends(get_db)):
    from app.core.security import decode_token
    from app.core.mfa import issue_tokens
    user_id = verify_token(data.refresh_token, 'refresh')
    if user_id is None:
        raise HTTPException(401, 'Session expirée. Reconnectez-vous.')
    user = db.query(User).filter(User.id == int(user_id)).first()
    payload = decode_token(data.refresh_token) or {}
    if not user or not user.is_active or not (user.is_whitelisted or user.is_superuser) or payload.get('mfa_ver', 0) != (user.mfa_version or 0):
        raise HTTPException(401, 'Session expirée. Reconnectez-vous.')
    from app.core.login_sessions import require_session
    session = require_session(db, user, payload, lock=True)
    return issue_tokens(user, auth_time=payload.get('auth_time', 0), session=session)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.post('/me/avatar', response_model=UserResponse)
def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.profile_avatar import thumbnail, MAX_UPLOAD
    try:
        content = file.file.read(MAX_UPLOAD + 1)
    finally:
        file.file.close()
    current_user.avatar_image = thumbnail(content)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete('/me/avatar', response_model=UserResponse)
def remove_avatar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.avatar_image = None
    db.commit()
    db.refresh(current_user)
    return current_user


# Legacy paths remain authenticated and explicitly direct clients to the new flow.
@router.get('/2fa/status')
def legacy_2fa_status(current_user: User = Depends(get_current_user)):
    from app.core.mfa import methods
    return {'enabled': bool(methods(current_user)), 'has_backup_codes': bool(current_user.backup_codes)}


@router.post('/2fa/setup')
@router.post('/2fa/enable')
@router.post('/2fa/disable')
@router.post('/2fa/verify')
@router.post('/2fa/regenerate-backup-codes')
def legacy_2fa_management(current_user: User = Depends(get_current_user)):
    raise HTTPException(410, 'Utilisez Paramètres > Sécurité et le parcours /auth/mfa avec réauthentification.')
