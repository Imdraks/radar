"""Production tools share the existing project, task, event and approval models."""

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Literal
from urllib.parse import urlsplit, urlencode
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    get_current_workspace,
    require_workspace_write,
    require_feature,
)
from app.core.subscription import Feature, effective_features
from app.core.config import settings
from app.db.models.agency import (
    Project,
    Asset,
    Client,
    AgencyTask,
    Deliverable,
    Approval,
    ApprovalStatus,
    DeliverableStatus,
)
from app.db.models.production_tools import ProductionTemplate, DeliverableReview
from app.db.models.production_event import ProductionEvent
from app.db.models.discovery import DiscoveryArtist
from app.db.models.workspace import Workspace
from app.services.production_context import internal_client


def fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            [row.name, row.link, row.drive_file_id, row.notes, str(row.updated_at)],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


router = APIRouter(
    prefix="/workbench",
    dependencies=[Depends(get_current_workspace), Depends(require_workspace_write)],
)
public_router = APIRouter()


def project_in(db, ws, id):
    row = (
        db.query(Project)
        .join(Client)
        .filter(Project.id == id, Client.workspace_id == ws.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Projet non trouvé")
    return row


@router.get("/search")
def search(
    q: str = Query(min_length=2, max_length=100),
    db: Session = Depends(get_db),
    ws=Depends(get_current_workspace),
):
    term = (
        "%"
        + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        + "%"
    )
    features = effective_features(ws)
    result = []

    def add(query, kind, name, href):
        for row in query.limit(10).all():
            result.append(
                {
                    "id": str(row.id),
                    "kind": kind,
                    "name": getattr(row, name),
                    "url": href(row),
                }
            )

    if Feature.PROJECTS in features:
        add(
            db.query(Project)
            .join(Client)
            .filter(
                Client.workspace_id == ws.id, Project.name.ilike(term, escape="\\")
            ),
            "project",
            "name",
            lambda r: f"/projects/{r.id}",
        )
        add(
            db.query(AgencyTask)
            .join(Project)
            .join(Client)
            .filter(
                Client.workspace_id == ws.id, AgencyTask.title.ilike(term, escape="\\")
            ),
            "task",
            "title",
            lambda r: f"/projects/{r.project_id}",
        )
        add(
            db.query(Deliverable)
            .join(Project)
            .join(Client)
            .filter(
                Client.workspace_id == ws.id, Deliverable.name.ilike(term, escape="\\")
            ),
            "deliverable",
            "name",
            lambda r: f"/projects/{r.project_id}",
        )
    if Feature.ASSETS in features:
        add(
            db.query(Asset)
            .join(Project)
            .join(Client)
            .filter(
                Client.workspace_id == ws.id,
                or_(Asset.workspace_id == ws.id, Asset.workspace_id.is_(None)),
                Asset.name.ilike(term, escape="\\"),
            ),
            "file",
            "name",
            lambda r: f"/projects/{r.project_id}",
        )
    if Feature.DISCOVERY in features:
        add(
            db.query(DiscoveryArtist)
            .filter_by(workspace_id=ws.id, is_deleted=False)
            .filter(DiscoveryArtist.canonical_name.ilike(term, escape="\\")),
            "artist",
            "canonical_name",
            lambda r: f"/discovery/{r.id}",
        )
    if Feature.CLIENTS in features:
        add(
            db.query(Client).filter(
                Client.workspace_id == ws.id, Client.name.ilike(term, escape="\\")
            ),
            "client",
            "name",
            lambda r: "/clients?" + urlencode({"q": r.name}),
        )
    if Feature.EVENTS in features:
        add(
            db.query(ProductionEvent)
            .filter_by(workspace_id=ws.id, archived=False)
            .filter(ProductionEvent.name.ilike(term, escape="\\")),
            "event",
            "name",
            lambda r: f"/events/{r.id}",
        )
    return result


class Instantiate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    starts_at: datetime
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.starts_at.tzinfo or (self.ends_at and self.ends_at.tzinfo):
            raise ValueError("Dates UTC sans fuseau attendues")
        if self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("La fin précède le début")
        if not self.name.strip():
            raise ValueError("Nom requis")
        return self


@router.post(
    "/templates/{id}/instantiate",
    status_code=201,
    dependencies=[Depends(require_feature(Feature.PROJECTS))],
)
def instantiate(
    id: int,
    data: Instantiate,
    db: Session = Depends(get_db),
    ws=Depends(get_current_workspace),
    user=Depends(get_current_user),
):
    template = db.query(ProductionTemplate).filter_by(id=id, workspace_id=ws.id).first()
    if not template:
        raise HTTPException(404, "Modèle non trouvé")
    if template.kind == "event" and Feature.EVENTS not in effective_features(ws):
        raise HTTPException(403, "Offre événementielle requise")
    if template.kind == "event" and not data.ends_at:
        raise HTTPException(422, "Fin de l’événement requise")
    project = Project(
        name=data.name.strip(),
        client_id=internal_client(db, ws.id).id,
        workspace_id=ws.id,
        owner_id=user.id,
        deadline=data.ends_at,
    )
    db.add(project)
    db.flush()
    for item in template.definition["tasks"]:
        db.add(
            AgencyTask(
                project_id=project.id,
                title=item["title"],
                due_date=data.starts_at + timedelta(days=item["day"]),
            )
        )
    for item in template.definition["deliverables"]:
        db.add(
            Deliverable(
                project_id=project.id,
                name=item["title"],
                due_date=data.starts_at + timedelta(days=item["day"]),
            )
        )
    event = None
    if template.kind == "event":
        event = ProductionEvent(
            workspace_id=ws.id,
            project_id=project.id,
            name=project.name,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
        )
        db.add(event)
        db.flush()
    db.commit()
    return {
        "project_id": project.id,
        "event_id": event.id if event else None,
        "url": f"/events/{event.id}" if event else f"/projects/{project.id}",
    }


@router.get(
    "/projects/{id}/connections",
    dependencies=[Depends(require_feature(Feature.PROJECTS))],
)
def connections(
    id: int, db: Session = Depends(get_db), ws=Depends(get_current_workspace)
):
    project = project_in(db, ws, id)
    event = (
        db.query(ProductionEvent).filter_by(project_id=id, workspace_id=ws.id).first()
        if Feature.EVENTS in effective_features(ws)
        else None
    )
    return {
        "event_id": event.id if event else None,
        "client_url": (
            "/clients?" + urlencode({"q": db.get(Client, project.client_id).name})
            if Feature.CLIENTS in effective_features(ws)
            else None
        ),
        "client_id": (
            project.client_id if Feature.CLIENTS in effective_features(ws) else None
        ),
    }


class ReviewInput(BaseModel):
    expires_in_days: int = Field(default=7, ge=1, le=30)


def scoped_deliverable(db, ws, id):
    row = (
        db.query(Deliverable)
        .join(Project)
        .join(Client)
        .filter(Deliverable.id == id, Client.workspace_id == ws.id)
        .with_for_update(of=Deliverable)
        .first()
    )
    if not row:
        raise HTTPException(404, "Livrable non trouvé")
    return row


@router.post(
    "/deliverables/{id}/reviews",
    status_code=201,
    dependencies=[Depends(require_feature(Feature.PROJECTS))],
)
def create_review(
    id: int,
    data: ReviewInput,
    db: Session = Depends(get_db),
    ws=Depends(get_current_workspace),
):
    row = scoped_deliverable(db, ws, id)
    if (
        not row.link
        or urlsplit(row.link).scheme not in {"http", "https"}
        or not urlsplit(row.link).netloc
    ):
        raise HTTPException(422, "Ajoutez un lien HTTP(S) de consultation au livrable")
    if urlsplit(row.link).username or urlsplit(row.link).password:
        raise HTTPException(422, "Lien avec identifiants interdit")
    db.query(DeliverableReview).filter_by(
        deliverable_id=id, workspace_id=ws.id, status="pending"
    ).update({"status": "revoked"})
    approval = (
        db.query(Approval)
        .filter_by(deliverable_id=id, status=ApprovalStatus.PENDING)
        .order_by(Approval.id.desc())
        .first()
    )
    if not approval:
        approval = Approval(deliverable_id=id)
        db.add(approval)
    row.status = DeliverableStatus.TO_REVIEW
    db.flush()
    token = secrets.token_urlsafe(32)
    review = DeliverableReview(
        workspace_id=ws.id,
        deliverable_id=id,
        approval_id=approval.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        fingerprint=fingerprint(row),
        snapshot={"name": row.name, "link": row.link},
        expires_at=datetime.utcnow() + timedelta(days=data.expires_in_days),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {
        "id": review.id,
        "url": settings.frontend_url.rstrip("/") + "/review#token=" + token,
        "expires_at": review.expires_at,
    }


@router.get(
    "/deliverables/{id}/reviews",
    dependencies=[Depends(require_feature(Feature.PROJECTS))],
)
def reviews(id: int, db: Session = Depends(get_db), ws=Depends(get_current_workspace)):
    scoped_deliverable(db, ws, id)
    return [
        {
            "id": r.id,
            "status": r.status,
            "reviewer_name": r.reviewer_name,
            "feedback": r.feedback,
            "expires_at": r.expires_at,
            "decided_at": r.decided_at,
        }
        for r in db.query(DeliverableReview)
        .filter_by(workspace_id=ws.id, deliverable_id=id)
        .order_by(DeliverableReview.id.desc())
        .limit(100)
    ]


@router.post(
    "/reviews/{id}/revoke", dependencies=[Depends(require_feature(Feature.PROJECTS))]
)
def revoke(id: int, db: Session = Depends(get_db), ws=Depends(get_current_workspace)):
    row = (
        db.query(DeliverableReview)
        .filter_by(id=id, workspace_id=ws.id)
        .with_for_update()
        .first()
    )
    if not row:
        raise HTTPException(404, "Validation non trouvée")
    if row.status != "pending":
        raise HTTPException(409, "Validation déjà traitée")
    row.status = "revoked"
    db.commit()
    return {"status": "revoked"}


class TokenInput(BaseModel):
    token: str = Field(min_length=40, max_length=100)


class DecisionInput(TokenInput):
    decision: Literal["approved", "changes"]
    name: str = Field(min_length=2, max_length=200)
    feedback: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def meaningful(self):
        if len(self.name.strip()) < 2:
            raise ValueError("Nom requis")
        if self.decision == "changes" and not self.feedback.strip():
            raise ValueError("Précisez les modifications demandées")
        return self


def find_review(db, token):
    row = (
        db.query(DeliverableReview)
        .filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest())
        .first()
    )
    if not row:
        raise HTTPException(404, "Lien non trouvé")
    ws = db.query(Workspace).filter_by(id=row.workspace_id).first()
    if (
        not ws
        or ws.is_suspended
        or row.expires_at < datetime.utcnow()
        or row.status == "revoked"
    ):
        raise HTTPException(410, "Lien expiré ou désactivé")
    if Feature.PROJECTS not in effective_features(ws):
        raise HTTPException(410, "Espace indisponible")
    deliverable = scoped_deliverable(db, ws, row.deliverable_id)
    row = (
        db.query(DeliverableReview)
        .filter_by(id=row.id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    if row.status == "revoked" or row.expires_at < datetime.utcnow():
        raise HTTPException(410, "Lien expiré ou désactivé")
    if row.status == "pending" and row.fingerprint != fingerprint(deliverable):
        raise HTTPException(
            409, "Le livrable a changé. Demandez un nouveau lien à votre interlocuteur."
        )
    return row, deliverable


@public_router.post("/resolve")
def resolve(data: TokenInput, db: Session = Depends(get_db)):
    row, _ = find_review(db, data.token)
    return {
        "name": row.snapshot["name"],
        "link": row.snapshot["link"],
        "status": row.status,
        "expires_at": row.expires_at,
    }


@public_router.post("/decide")
def decide(data: DecisionInput, db: Session = Depends(get_db)):
    row, deliverable = find_review(db, data.token)
    if row.status != "pending":
        raise HTTPException(409, "Une décision a déjà été enregistrée")
    row.status = data.decision
    row.reviewer_name = data.name.strip()
    row.feedback = data.feedback
    row.decided_at = datetime.utcnow()
    approval = db.get(Approval, row.approval_id)
    approval.status = (
        ApprovalStatus.APPROVED
        if data.decision == "approved"
        else ApprovalStatus.CHANGES
    )
    approval.feedback = (
        f"Validation externe — identité déclarée : {row.reviewer_name}\n{row.feedback}"
    )
    approval.decided_at = row.decided_at
    if data.decision == "approved":
        deliverable.status = DeliverableStatus.APPROVED
    else:
        deliverable.status = DeliverableStatus.CHANGES_REQUESTED
    db.commit()
    return {"status": row.status}


class PlanItem(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    day: int = Field(default=0, ge=-365, le=365)

    @field_validator("title")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Titre requis")
        return value.strip()


class PlanDefinition(BaseModel):
    tasks: list[PlanItem] = Field(default_factory=list, max_length=50)
    deliverables: list[PlanItem] = Field(default_factory=list, max_length=50)


class TemplateInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["project", "event"]
    definition: PlanDefinition

    @field_validator("name")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Nom requis")
        return value.strip()


@router.get("/templates", dependencies=[Depends(require_feature(Feature.PROJECTS))])
def templates(db: Session = Depends(get_db), ws=Depends(get_current_workspace)):
    return (
        db.query(ProductionTemplate)
        .filter_by(workspace_id=ws.id)
        .order_by(ProductionTemplate.created_at.desc(), ProductionTemplate.id.desc())
        .limit(200)
        .all()
    )


@router.post(
    "/templates",
    status_code=201,
    dependencies=[Depends(require_feature(Feature.PROJECTS))],
)
def save_template(
    data: TemplateInput,
    db: Session = Depends(get_db),
    ws=Depends(get_current_workspace),
):
    if data.kind == "event" and Feature.EVENTS not in effective_features(ws):
        raise HTTPException(403, "Offre événementielle requise")
    if db.query(ProductionTemplate.id).filter_by(workspace_id=ws.id).count() >= 200:
        raise HTTPException(409, "Limite de 200 modèles atteinte")
    row = ProductionTemplate(
        workspace_id=ws.id,
        name=data.name,
        kind=data.kind,
        definition=data.definition.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/projects/{id}/reviewable-deliverables",
    dependencies=[Depends(require_feature(Feature.PROJECTS))],
)
def reviewable(
    id: int, db: Session = Depends(get_db), ws=Depends(get_current_workspace)
):
    project_in_scope = project_in(db, ws, id)
    return [
        {"id": r.id, "name": r.name, "has_link": bool(r.link), "status": r.status.value}
        for r in db.query(Deliverable)
        .filter_by(project_id=project_in_scope.id)
        .order_by(Deliverable.id)
        .limit(200)
    ]
