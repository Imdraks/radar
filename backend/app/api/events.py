"""Agency event lifecycle reusing projects, tasks, deliverables and assets."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator, condecimal
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_workspace, require_feature, require_workspace_write
from app.core.subscription import Feature, effective_features
from app.db.models.agency import Project, Client, ProjectStatus
from app.db.models.discovery import DiscoveryArtist
from app.db.models.production_event import ProductionEvent, EventArtist, EventExpense
from app.services.production_context import internal_client

Money = condecimal(ge=0, max_digits=14, decimal_places=2)

router = APIRouter(prefix="/events", dependencies=[Depends(require_feature(Feature.EVENTS)), Depends(require_workspace_write)])


class EventInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    venue: str | None = Field(None, max_length=500)
    starts_at: datetime
    ends_at: datetime
    forecast_budget: Optional[Money] = None
    project_id: int | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.starts_at.tzinfo or self.ends_at.tzinfo:
            raise ValueError("Dates UTC sans suffixe attendues")
        if self.ends_at < self.starts_at:
            raise ValueError("La fin doit suivre le début")
        return self


class EventUpdate(EventInput):
    archived: bool = False


def find_event(db, workspace, event_id):
    event = db.query(ProductionEvent).filter_by(id=event_id, workspace_id=workspace.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return event


@router.get("")
def list_events(db: Session = Depends(get_db), workspace=Depends(get_current_workspace)):
    return db.query(ProductionEvent).filter_by(workspace_id=workspace.id, archived=False).order_by(ProductionEvent.starts_at).limit(200).all()


@router.post("", status_code=201)
def create_event(data: EventInput, db: Session = Depends(get_db), workspace=Depends(get_current_workspace), user=Depends(get_current_user)):
    if data.project_id:
        project = db.query(Project).join(Client).filter(Project.id == data.project_id, Client.workspace_id == workspace.id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Projet non trouvé")
        if db.query(ProductionEvent).filter_by(project_id=project.id).first():
            raise HTTPException(status_code=409, detail="Ce projet est déjà associé à un événement")
    else:
        client = internal_client(db, workspace.id)
        project = Project(name=data.name, client_id=client.id, workspace_id=workspace.id, owner_id=user.id,
                          status=ProjectStatus.ACTIVE, deadline=data.ends_at)
        db.add(project)
        db.flush()
    event = ProductionEvent(**data.model_dump(exclude={"project_id"}), project_id=project.id, workspace_id=workspace.id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}")
def event_detail(event_id: int, db: Session = Depends(get_db), workspace=Depends(get_current_workspace)):
    event = find_event(db, workspace, event_id)
    artists = db.query(DiscoveryArtist).join(EventArtist, EventArtist.artist_id == DiscoveryArtist.id).filter(
        EventArtist.event_id == event.id, DiscoveryArtist.workspace_id == workspace.id, DiscoveryArtist.is_deleted == False).all()
    return {"event": event, "artists": [{"id": a.id, "name": a.canonical_name} for a in artists],
            "production_url": f"/projects/{event.project_id}", "map_url": "/map"}


@router.put("/{event_id}")
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db), workspace=Depends(get_current_workspace)):
    event = find_event(db, workspace, event_id)
    if data.project_id is not None and data.project_id != event.project_id:
        raise HTTPException(status_code=409, detail="Le projet de production ne peut pas être remplacé")
    for key, value in data.model_dump(exclude={"project_id"}).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/artists/{artist_id}", status_code=201)
def add_artist(event_id: int, artist_id: UUID, db: Session = Depends(get_db), workspace=Depends(get_current_workspace)):
    event = find_event(db, workspace, event_id)
    db.query(ProductionEvent).filter_by(id=event.id).with_for_update().one()
    artist = db.query(DiscoveryArtist).filter_by(id=artist_id, workspace_id=workspace.id, is_deleted=False).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    if not db.query(EventArtist).filter_by(event_id=event.id, artist_id=artist.id).first():
        db.add(EventArtist(event_id=event.id, artist_id=artist.id))
        db.commit()
    return {"event_id": event.id, "artist_id": artist.id}


class ExpenseInput(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    amount: Money


@router.get("/{event_id}/expenses", dependencies=[Depends(require_feature(Feature.INVOICES))])
def list_expenses(event_id: int, db: Session = Depends(get_db), workspace=Depends(get_current_workspace)):
    event = find_event(db, workspace, event_id)
    return db.query(EventExpense).filter_by(event_id=event.id).all()


@router.post("/{event_id}/expenses", status_code=201, dependencies=[Depends(require_feature(Feature.INVOICES))])
def add_expense(event_id: int, data: ExpenseInput, db: Session = Depends(get_db), workspace=Depends(get_current_workspace)):
    event = find_event(db, workspace, event_id)
    expense = EventExpense(event_id=event.id, **data.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense
