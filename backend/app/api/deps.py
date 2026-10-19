"""
Authentication dependencies
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.user import User, Role
from app.core.security import verify_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    token = credentials.credentials
    user_id = verify_token(token, "access")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return user


def require_workspace_member(
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Require user to be a member of at least one workspace.
    Returns user with workspace_id attribute attached.
    """
    current_user.workspace_id = resolve_workspace_id(db, current_user, workspace_id)
    return current_user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


class RoleChecker:
    """Role-based access control dependency"""
    
    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user


# Pre-configured role checkers
require_admin = RoleChecker([Role.ADMIN])
require_bizdev = RoleChecker([Role.ADMIN, Role.BIZDEV])
require_pm = RoleChecker([Role.ADMIN, Role.BIZDEV, Role.PM])
require_viewer = RoleChecker([Role.ADMIN, Role.BIZDEV, Role.PM, Role.VIEWER])


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user only if admin or superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_current_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Platform grants require the explicit superuser flag, never an agency role."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Platform administrator required")
    return current_user


def resolve_workspace_id(db: Session, user: User, workspace_id: Optional[int] = None) -> int:
    from app.db.models.workspace import Workspace, WorkspaceMember
    from sqlalchemy import or_
    query = db.query(Workspace).outerjoin(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
    query = query.filter(or_(Workspace.owner_user_id == user.id, WorkspaceMember.user_id == user.id))
    if workspace_id is not None:
        query = query.filter(Workspace.id == workspace_id)
    workspace = query.order_by(Workspace.id).first()
    if not workspace:
        raise HTTPException(status_code=403, detail="NO_WORKSPACE_ACCESS")
    db.info["workspace_id"] = workspace.id
    return workspace.id


def get_user_workspace_id(
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> int:
    # Even platform users use explicit admin endpoints for cross-company access.
    return resolve_workspace_id(db, current_user, workspace_id)


def get_current_workspace(
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.db.models.workspace import Workspace
    ws_id = resolve_workspace_id(db, current_user, workspace_id)
    return db.query(Workspace).filter(Workspace.id == ws_id).one()


def get_current_workspace_id(
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> int:
    return resolve_workspace_id(db, current_user, workspace_id)


def require_feature(feature):
    from app.core.subscription import effective_features

    def check(workspace=Depends(get_current_workspace)):
        if feature not in effective_features(workspace):
            raise HTTPException(status_code=403, detail={"code": "FEATURE_NOT_AVAILABLE", "feature": feature.value})
        return workspace
    return check


async def require_workspace_write(
    request: Request,
    current_user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models.workspace import WorkspaceMember, WorkspaceRole
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if workspace.owner_user_id != current_user.id:
        member = db.query(WorkspaceMember).filter_by(workspace_id=workspace.id, user_id=current_user.id).first()
        if not member or member.role == WorkspaceRole.VIEWER:
            raise HTTPException(status_code=403, detail="Workspace write permission required")
    if "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            from app.db.models.workspace import Workspace
            for key in ("assignee_id", "owner_id", "assigned_to_user_id"):
                person_id = body.get(key)
                if person_id is not None:
                    try:
                        person_id = int(person_id)
                    except (TypeError, ValueError):
                        raise HTTPException(status_code=422, detail="Identifiant de collaborateur invalide")
                if person_id is not None and person_id != workspace.owner_user_id:
                    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace.id, user_id=person_id).first()
                    if not member:
                        raise HTTPException(status_code=422, detail="Le collaborateur doit appartenir au workspace")
            from app.db.models.agency import Project, Client, Deal
            from app.db.models.opportunity import Opportunity
            from app.db.models.billing import BillingClient
            references = {"client_id": BillingClient if "/billing/" in request.url.path else Client,
                          "project_id": Project, "deal_id": Deal, "opportunity_id": Opportunity}
            for key, model in references.items():
                resource_id = body.get(key)
                if resource_id is not None:
                    try:
                        resource_id = int(resource_id)
                    except (TypeError, ValueError):
                        raise HTTPException(status_code=422, detail="Identifiant de ressource invalide")
                if resource_id is not None and not db.query(model).filter(model.id == resource_id).first():
                    raise HTTPException(status_code=404, detail="Ressource liée introuvable dans ce workspace")

# Global user administration must never be granted by an agency's ADMIN role.
require_admin = get_current_platform_admin
