"""One public catalog, workspace requests, and platform-only activation.
A request never changes effective rights and is never a payment confirmation.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_platform_admin, resolve_workspace_id
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.db.models.user import User
from app.db.models.subscription_request import SubscriptionRequest
from app.core.subscription import (
    Plan, Feature, PLAN_CONFIGS, NAV_SECTIONS, ADMIN_ONLY_FEATURES,
    effective_features, resolve_plan, get_plan_features, get_upgrade_message,
)

router = APIRouter(prefix="/subscription", tags=["Subscription"])


def get_workspace_for_user(db, user, workspace_id=None):
    ws_id = resolve_workspace_id(db, user, workspace_id)
    return db.query(Workspace).filter_by(id=ws_id).one()


def is_workspace_admin(db, user, workspace):
    if workspace.owner_user_id == user.id:
        return True
    return db.query(WorkspaceMember).filter_by(
        workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.ADMIN
    ).first() is not None


def serialize_subscription(db, workspace):
    plan = resolve_plan(workspace.plan, workspace.enabled_packs, workspace.addons)
    config = PLAN_CONFIGS[plan]
    member_ids = {m.user_id for m in db.query(WorkspaceMember).filter_by(workspace_id=workspace.id).all()}
    member_ids.add(workspace.owner_user_id)
    return {
        "workspace_id": workspace.id, "workspace_name": workspace.name,
        "plan": plan.value, "plan_display_name": config.display_name,
        "enabled_packs": [p.value for p in config.included_packs],
        "addons": [], "max_seats": workspace.max_seats,
        "current_seats": len(member_ids),
        "available_features": sorted(f.value for f in effective_features(workspace)),
        "plan_expires_at": workspace.plan_expires_at.isoformat() if workspace.plan_expires_at else None,
    }


@router.get("/plans")
async def get_available_plans():
    return [{**vars(config), "included_packs": [p.value for p in config.included_packs],
             "included_addons": [], "is_current": False, "is_recommended": False,
             "available_features": sorted(f.value for f in get_plan_features(plan))}
            for plan, config in PLAN_CONFIGS.items()]


@router.get("/addons")
async def get_available_addons():
    return []  # Extensions are negotiated, never self-service entitlement toggles.


@router.get("/pricing")
async def get_pricing_info():
    return {"plans": await get_available_plans(), "currency": "EUR", "prices_validated": False,
            "addons": {"name": "Radar Addons", "is_subscription": False,
                       "description": "Extensions et outils sur mesure après accord commercial"}}


@router.get("/current")
async def get_current_subscription(workspace_id: Optional[int] = None, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    return serialize_subscription(db, get_workspace_for_user(db, current_user, workspace_id))


@router.get("/features/{feature}")
async def check_feature_access(feature: Feature, workspace_id: Optional[int] = None,
                               db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    workspace = get_workspace_for_user(db, current_user, workspace_id)
    available = feature in effective_features(workspace)
    if feature in ADMIN_ONLY_FEATURES:
        available = current_user.is_superuser
    return {"feature": feature.value, "available": available,
            "upgrade_path": None if available else get_upgrade_message(feature, resolve_plan(workspace.plan))}


@router.get("/navigation")
async def get_navigation_config(workspace_id: Optional[int] = None, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    workspace = get_workspace_for_user(db, current_user, workspace_id)
    features = effective_features(workspace)
    sections = {}
    for section, items in NAV_SECTIONS.items():
        visible = [{"label": item.label, "path": item.path, "icon": item.icon,
                    "available": True, "locked": False, "admin_only": item.admin_only}
                   for item in items
                   if (not item.admin_only or is_workspace_admin(db, current_user, workspace))
                   and (item.feature is None or item.feature in features)]
        if visible:
            sections[section] = visible
    return {"sections": sections}


class ChangePlanRequest(BaseModel):
    plan: Plan


class AddonRequest(BaseModel):
    description: str = Field(min_length=3, max_length=100)


def submit_request(db, user, workspace_id, kind, value):
    workspace = get_workspace_for_user(db, user, workspace_id)
    if not is_workspace_admin(db, user, workspace):
        raise HTTPException(status_code=403, detail="Workspace administrator required")
    # Serialize submissions for this workspace and reuse identical pending requests.
    db.query(Workspace).filter_by(id=workspace.id).with_for_update().one()
    existing = db.query(SubscriptionRequest).filter_by(workspace_id=workspace.id, kind=kind,
                                                       requested_value=value, status="pending").first()
    if not existing:
        existing = SubscriptionRequest(workspace_id=workspace.id, requested_by=user.id,
                                       kind=kind, requested_value=value)
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return {"request_id": existing.id, "status": existing.status,
            "message": "Demande enregistrée. Aucun droit modifié ; activation après autorisation administrative."}


@router.post("/change-plan", status_code=202)
async def change_plan(request: ChangePlanRequest, workspace_id: Optional[int] = None,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return submit_request(db, current_user, workspace_id, "plan", request.plan.value)


@router.post("/addon-requests", status_code=202)
async def request_addon(request: AddonRequest, workspace_id: Optional[int] = None,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return submit_request(db, current_user, workspace_id, "addon", request.description)


@router.post("/toggle-addon")
@router.post("/toggle-pack")
async def retired_toggle(workspace_id: Optional[int] = None, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    get_workspace_for_user(db, current_user, workspace_id)
    raise HTTPException(status_code=409, detail="Activation directe désactivée. Utilisez une demande commerciale.")


@router.get("/requests")
async def list_requests(workspace_id: Optional[int] = None, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    workspace = get_workspace_for_user(db, current_user, workspace_id)
    if not is_workspace_admin(db, current_user, workspace):
        raise HTTPException(status_code=403, detail="Workspace administrator required")
    return db.query(SubscriptionRequest).filter_by(workspace_id=workspace.id).order_by(
        SubscriptionRequest.id.desc()).limit(100).all()


class Decision(BaseModel):
    approve: bool
    authorization_reference: str = Field(min_length=5, max_length=2000)


@router.get("/admin/requests")
async def admin_requests(db: Session = Depends(get_db), admin: User = Depends(get_current_platform_admin)):
    return db.query(SubscriptionRequest).filter_by(status="pending").order_by(SubscriptionRequest.id).limit(100).all()


@router.get("/admin/workspace/{workspace_id}")
async def admin_get_workspace_subscription(workspace_id: int, db: Session = Depends(get_db),
                                            admin: User = Depends(get_current_platform_admin)):
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    return serialize_subscription(db, workspace)


@router.post("/admin/requests/{request_id}/decision")
async def decide_request(request_id: int, decision: Decision, db: Session = Depends(get_db),
                          admin: User = Depends(get_current_platform_admin)):
    entry = db.query(SubscriptionRequest).filter_by(id=request_id).with_for_update().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    if entry.status != "pending":
        raise HTTPException(status_code=409, detail="Demande déjà traitée")
    if decision.approve and entry.kind != "plan":
        raise HTTPException(status_code=409, detail="Extension sur mesure : livraison et droits spécifiques à valider séparément")
    workspace = db.query(Workspace).filter_by(id=entry.workspace_id).with_for_update().one()
    entry.previous_plan = workspace.plan
    if decision.approve:
        plan = Plan(entry.requested_value)
        config = PLAN_CONFIGS[plan]
        workspace.plan = plan.value
        workspace.enabled_packs = [p.value for p in config.included_packs]
        workspace.addons = []
        # Keep existing contractual seats; do not create new commercial limits.
        # Explicit activation supersedes expiry of the previous grant.
        workspace.plan_expires_at = None
    entry.status = "approved" if decision.approve else "rejected"
    entry.decided_by = admin.id
    entry.decided_at = datetime.utcnow()
    entry.authorization_reference = decision.authorization_reference
    db.commit()
    return {"request_id": entry.id, "status": entry.status, "subscription": serialize_subscription(db, workspace)}


# Legacy write URLs remain authenticated but cannot bypass the audited approval path.
@router.patch("/admin/workspace/{workspace_id}")
@router.post("/admin/migrate-workspaces")
async def retired_admin_write(db: Session = Depends(get_db), admin: User = Depends(get_current_platform_admin)):
    raise HTTPException(status_code=409, detail="Utilisez les décisions tracées ; migration via Alembic uniquement")
