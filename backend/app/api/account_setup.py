"""First-login security progression, independent of any tenant business access."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db import get_db
from app.db.models.user import User
from app.db.models.workspace import Workspace, WorkspaceMember
from app.core import mfa
from app.core.activity_logger import ActivityLogger

router = APIRouter(prefix="/auth/account", tags=["Account setup"])


class CompleteSetup(BaseModel):
    security: Literal["later", "configured"]


@router.post("/setup/complete")
def complete(
    data: CompleteSetup,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = mfa.lock_user(db, user.id)
    if user.must_change_password:
        raise HTTPException(403, "Choisissez d’abord un nouveau mot de passe.")
    enabled = bool(mfa.methods(user))
    if data.security == "configured" and not enabled:
        raise HTTPException(
            409,
            "Aucune méthode de sécurité n’est activée. Terminez sa configuration ou choisissez « Plus tard ».",
        )
    if user.security_setup_pending:
        user.security_setup_pending = False
        ActivityLogger.log(
            db,
            user,
            "account.setup_completed",
            details={"security_choice": data.security, "factor_enabled": enabled},
        )
    return {"completed": True, "factor_enabled": enabled}


@router.get("/workspaces")
def workspaces(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.must_change_password:
        raise HTTPException(403, "PASSWORD_CHANGE_REQUIRED")
    rows = (
        db.query(Workspace)
        .outerjoin(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(
            or_(Workspace.owner_user_id == user.id, WorkspaceMember.user_id == user.id)
        )
        .distinct()
        .order_by(Workspace.name)
        .all()
    )
    return [dict(id=ws.id, name=ws.name, is_suspended=ws.is_suspended) for ws in rows]
