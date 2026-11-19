"""Remove a suspended workspace from use without erasing retained customer data."""

from datetime import datetime
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
from app.db.models.workspace import Workspace
from app.db.models.activity_log import ActivityLog


class DeleteWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    confirm_name: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=5, max_length=1000)
    acknowledged: Literal[True]


def remove_workspace(db, admin, id, data):
    if not admin.is_superuser:
        raise HTTPException(403, "Platform administrator required")
    workspace = (
        db.query(Workspace)
        .filter_by(id=id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not workspace:
        raise HTTPException(404, "Espace introuvable.")
    if not workspace.is_suspended:
        raise HTTPException(409, "Suspendez cet espace avant de le supprimer.")
    if data.confirm_name != workspace.name.strip():
        raise HTTPException(
            409, "Le nom de confirmation ne correspond pas à celui de l’espace."
        )
    workspace.deleted_at = datetime.utcnow()
    workspace.deleted_by = admin.id
    db.add(
        ActivityLog(
            user_id=admin.id,
            user_tracking_id=admin.tracking_id or "SYSTEM",
            action="client.deleted",
            resource_type="workspace",
            resource_id=str(workspace.id),
            details={
                "reason": data.reason,
                "data_retained": True,
                "name": workspace.name,
            },
        )
    )
    db.commit()
