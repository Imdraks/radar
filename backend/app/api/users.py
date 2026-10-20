"""
User management endpoints
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.user import User, Role
from app.core.security import get_password_hash
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])


def user_to_response(user: User) -> dict:
    """Convert user model to response dict with linked accounts"""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_whitelisted": user.is_whitelisted or False,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "auth_provider": user.auth_provider,
        "avatar_url": user.avatar_url,
        "linked_accounts": [
            {
                "provider": acc.provider,
                "email": acc.email,
                "created_at": acc.created_at,
            }
            for acc in user.accounts
        ],
    }


@router.get("", response_model=List[UserResponse])
def list_users(
    role: Role = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users (admin only)"""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.order_by(User.email).all()
    return [user_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user_to_response(user)


@router.post("", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new user"""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=user_data.is_active,
        is_whitelisted=True,  # Users created by admin are automatically whitelisted
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_dict:
        update_dict["hashed_password"] = get_password_hash(update_dict.pop("password"))
    
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


# ============================================================================
# ADMIN SETTINGS
# ============================================================================

@router.get("/admin/settings")
def get_admin_settings(
    current_user: User = Depends(require_admin),
):
    """Get all admin settings"""
    from app.core.admin_settings import get_admin_settings as get_settings
    from app.services.email_service import email_service
    
    settings = get_settings()
    # Add email configuration status
    settings["email_configured"] = email_service.is_configured
    return settings


@router.put("/admin/settings")
def update_admin_settings(
    updates: dict,
    current_user: User = Depends(require_admin),
):
    """Update admin settings"""
    from app.core.admin_settings import set_admin_settings
    
    # Only allow specific settings to be updated
    allowed_keys = {"send_invitation_emails"}
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_keys}
    
    return set_admin_settings(filtered_updates)
