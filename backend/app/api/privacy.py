"""Rights remain available independently of the workspace subscription."""

from datetime import datetime
from typing import Literal, Optional
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    get_current_platform_admin,
    resolve_workspace_id,
)
from app.api.subscription import is_workspace_admin
from app.db.models.privacy import PrivacyRequest
from app.db.models.workspace import Workspace


class PrivateJSONResponse(JSONResponse):
    def __init__(
        self,
        content,
        status_code: int = 200,
        headers=None,
        media_type=None,
        background=None,
    ):
        private_headers = {
            **(headers or {}),
            "Cache-Control": "no-store",
            "Vary": "Authorization",
        }
        super().__init__(
            content,
            status_code=status_code,
            headers=private_headers,
            media_type=media_type,
            background=background,
        )


router = APIRouter(
    prefix="/privacy", tags=["Privacy"], default_response_class=PrivateJSONResponse
)


class RightsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal[
        "access",
        "rectification",
        "erasure",
        "portability",
        "objection",
        "restriction",
        "cancellation",
        "switching",
    ]
    scope: Literal["personal", "workspace"] = "personal"
    details: str = Field(default="", max_length=3000)


class ResponseInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: Literal["in_progress", "answered", "refused"]
    response: str = Field(min_length=10, max_length=5000)
    reference: str = Field(min_length=3, max_length=150)


def serialize(row):
    return {
        k: getattr(row, k)
        for k in (
            "id",
            "workspace_id",
            "kind",
            "scope",
            "status",
            "details",
            "created_at",
            "response_due_at",
            "updated_at",
            "response",
        )
    }


@router.post("/requests", status_code=201)
def submit_request(
    data: RightsInput,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    workspace = None
    if workspace_id is not None:
        selected = resolve_workspace_id(db, user, workspace_id)
        workspace = db.query(Workspace).filter_by(id=selected).one()
    if data.scope == "workspace" or data.kind in {"switching", "cancellation"}:
        if not workspace or not is_workspace_admin(db, user, workspace):
            raise HTTPException(
                403,
                "L’administrateur de cet espace doit demander sa résiliation ou sa réversibilité",
            )
    now = datetime.utcnow()
    # A calendar month, not an invented fixed 30-day GDPR deadline. Commercial
    # switching deadlines are determined separately by the applicable contract/law.
    row = PrivacyRequest(
        user_id=user.id,
        workspace_id=workspace.id if workspace else None,
        kind=data.kind,
        scope=data.scope,
        details=data.details,
        response_due_at=now + relativedelta(months=1),
        created_at=now,
        updated_at=now,
        audit_log=[{"event": "received", "at": now.isoformat(), "by": user.id}],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.get("/requests")
def my_requests(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return [
        serialize(row)
        for row in db.query(PrivacyRequest)
        .filter_by(user_id=user.id)
        .order_by(PrivacyRequest.created_at.desc())
        .limit(100)
    ]


@router.get("/account-export")
def account_export(db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Explicit allowlist: no token, password hash, 2FA seed, invite or other member data.
    data = {
        "format": "radar-account-v1",
        "generated_at": datetime.utcnow().isoformat(),
        "scope": "account_identity_and_own_requests",
        "account": {
            k: getattr(user, k) for k in ("id", "email", "full_name", "created_at")
        },
        "requests": [
            serialize(row)
            for row in db.query(PrivacyRequest)
            .filter_by(user_id=user.id)
            .order_by(PrivacyRequest.id)
            .all()
        ],
        "coverage_note": "Cet export partiel ne remplace pas une réponse complète à une demande d’accès ni un export complet de workspace. Les données de projet et des tiers nécessitent une vérification de périmètre.",
    }
    from fastapi.encoders import jsonable_encoder

    return JSONResponse(
        jsonable_encoder(data),
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="radar-account.json"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/admin/requests")
def admin_requests(
    status: Optional[Literal["received", "in_progress", "answered", "refused"]] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_admin),
):
    query = db.query(PrivacyRequest)
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter(PrivacyRequest.status.in_(["received", "in_progress"]))
    return [
        {**serialize(row), "user_id": row.user_id, "audit_log": row.audit_log}
        for row in query.order_by(PrivacyRequest.response_due_at).limit(200)
    ]


@router.post("/admin/requests/{request_id}/respond")
def respond(
    request_id: int,
    data: ResponseInput,
    db: Session = Depends(get_db),
    admin=Depends(get_current_platform_admin),
):
    row = db.query(PrivacyRequest).filter_by(id=request_id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Demande introuvable")
    if row.status in {"answered", "refused"}:
        raise HTTPException(409, "Une réponse finale est déjà enregistrée")
    now = datetime.utcnow()
    row.status = data.status
    row.response = data.response
    row.updated_at = now
    row.audit_log = [
        *(row.audit_log or []),
        {
            "event": data.status,
            "by": admin.id,
            "at": now.isoformat(),
            "reference": data.reference,
        },
    ]
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.get("/workspace-export")
def workspace_export(workspace_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.api.legal_contracts import require_workspace_admin
    from app.services.workspace_export import archive
    from fastapi.responses import Response
    workspace = require_workspace_admin(db, user, workspace_id)
    data, manifest = archive(db, workspace.id)
    return Response(data, media_type="application/zip", headers={
        "Cache-Control": "no-store", "Vary": "Authorization",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'attachment; filename="radar-workspace-{workspace.id}.zip"',
        "X-Export-Format": manifest['format'],
    })


@router.get("/retention-inventory")
def retention_inventory(workspace_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.api.legal_contracts import require_workspace_admin
    from app.services.workspace_export import ownership_scopes
    from app.db.base import Base
    from sqlalchemy import select, literal, func, union_all
    workspace = require_workspace_admin(db, user, workspace_id)
    scopes = ownership_scopes(workspace.id)
    categories = {'projects':'Projets', 'billing_clients':'Contacts de facturation', 'invoices':'Factures',
                  'quotes':'Devis', 'discovery_artists':'Artistes', 'artist_snapshots':'Observations artistiques',
                  'workspace_members':'Membres', 'legal_acceptances':'Preuves contractuelles'}
    queries = []
    for name in categories:
        table = Base.metadata.tables[name]
        date_col = table.c.get('created_at')
        if date_col is None: date_col = table.c.get('accepted_at')
        queries.append(select(literal(name).label('dataset'), func.count().label('rows'),
                             func.min(date_col).label('oldest')).select_from(table).where(scopes[name]))
    rows = db.execute(union_all(*queries)).all()
    return {'workspace_id':workspace.id, 'automatic_erasure_enabled':False,
            'policy_status':'Les durées et exceptions doivent être définies dans la version contractuelle publiée ; aucune durée n’est inventée ici.',
            'datasets':[{'dataset':name,'label':categories[name],'count':count,'oldest_record_at':oldest} for name,count,oldest in rows],
            'notice':'Un enregistrement ancien n’est pas automatiquement effaçable. Examiner finalité, fin de contrat, obligations légales, litiges et sauvegardes avant toute action.'}
