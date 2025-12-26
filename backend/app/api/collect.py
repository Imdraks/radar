"""
Unified Collection API - Standard (Sources) and Advanced (AI/ChatGPT)

POST /collect/standard  - Standard collection via configured sources -> Opportunities page
POST /collect/advanced  - AI-powered collection via ChatGPT -> Dossiers/Briefs page
GET  /collect/status/{run_id} - Get collection status
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.db.models.user import User
from app.db.models.source import SourceConfig
from app.db.models.ingestion import IngestionRun, IngestionStatus
from app.db.models.entity import Entity, EntityType, CollectionRun, ObjectiveType as DBObjectiveType
from app.api.deps import get_current_user
from app.workers.tasks import run_ingestion_task
from app.workers.ai_collection import run_ai_collection_task

router = APIRouter(prefix="/collect", tags=["Collection"])


# =====================
# Request/Response Models
# =====================

class StandardCollectRequest(BaseModel):
    """Request for standard collection via sources"""
    keywords: Optional[str] = Field(None, description="Keywords to search for, comma-separated")
    source_ids: Optional[List[str]] = Field(None, description="Specific source IDs to use")
    region: Optional[str] = None
    city: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class StandardCollectResponse(BaseModel):
    """Response for standard collection"""
    run_ids: List[str]
    source_count: int
    message: str


class EntityInput(BaseModel):
    """Entity input for advanced collection"""
    name: str
    type: str = "ORGANIZATION"  # PERSON, ORGANIZATION, TOPIC


class AdvancedCollectRequest(BaseModel):
    """Request for AI-powered advanced collection"""
    objective: str = Field(..., description="SPONSOR, BOOKING, PRESS, VENUE, SUPPLIER, GRANT")
    entities: List[EntityInput] = Field(..., min_length=1)
    secondary_keywords: Optional[List[str]] = []
    timeframe_days: int = Field(30, ge=7, le=365)
    require_contact: bool = False
    region: Optional[str] = None
    city: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class AdvancedCollectResponse(BaseModel):
    """Response for advanced collection"""
    run_id: str
    entities_created: List[str]
    message: str


class CollectionStatusResponse(BaseModel):
    """Collection status response"""
    id: str
    type: str  # "standard" or "advanced"
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    items_found: int = 0
    items_new: int = 0
    contacts_found: int = 0
    error_message: Optional[str] = None
    brief_id: Optional[str] = None


# =====================
# Standard Collection (Sources -> Opportunities)
# =====================

@router.post("/standard", response_model=StandardCollectResponse)
def start_standard_collection(
    request: StandardCollectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start standard collection from configured sources.
    Results will appear in the Opportunities page.
    
    This triggers ingestion from all active sources (or specific ones if source_ids provided)
    with optional filters for keywords, location, and budget.
    """
    # Get sources to process
    query = db.query(SourceConfig).filter(SourceConfig.is_active == True)
    
    if request.source_ids:
        query = query.filter(SourceConfig.id.in_(request.source_ids))
    
    sources = query.all()
    
    if not sources:
        raise HTTPException(
            status_code=400,
            detail="Aucune source active. Configurez des sources dans l'onglet Sources."
        )
    
    # Build search params
    search_params = {}
    if request.keywords:
        search_params['keywords'] = request.keywords
    if request.region:
        search_params['region'] = request.region
    if request.city:
        search_params['city'] = request.city
    if request.budget_min is not None:
        search_params['budget_min'] = request.budget_min
    if request.budget_max is not None:
        search_params['budget_max'] = request.budget_max
    
    # Trigger ingestion tasks for each source
    run_ids = []
    for source in sources:
        task = run_ingestion_task.delay(
            source_id=str(source.id),
            search_params=search_params if search_params else None
        )
        run_ids.append(task.id)
    
    return StandardCollectResponse(
        run_ids=run_ids,
        source_count=len(sources),
        message=f"Collecte standard lancée sur {len(sources)} source(s)"
    )


# =====================
# Advanced Collection (ChatGPT -> Briefs/Dossiers)
# =====================

@router.post("/advanced", response_model=AdvancedCollectResponse)
def start_advanced_collection(
    request: AdvancedCollectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start AI-powered advanced collection using ChatGPT.
    Results will appear in the Dossiers page with generated briefs.
    
    This uses OpenAI to intelligently search for opportunities, contacts,
    and relevant information based on the objective and entities provided.
    """
    # Validate objective
    valid_objectives = ["SPONSOR", "BOOKING", "PRESS", "VENUE", "SUPPLIER", "GRANT"]
    if request.objective not in valid_objectives:
        raise HTTPException(
            status_code=400,
            detail=f"Objectif invalide. Valeurs possibles: {', '.join(valid_objectives)}"
        )
    
    # Create or get entities
    entity_ids = []
    for entity_input in request.entities:
        normalized_name = entity_input.name.lower().strip()
        
        # Map entity type
        try:
            entity_type = EntityType[entity_input.type]
        except KeyError:
            entity_type = EntityType.ORGANIZATION
        
        # Check if entity exists
        entity = db.query(Entity).filter(
            Entity.normalized_name == normalized_name,
            Entity.entity_type == entity_type
        ).first()
        
        if not entity:
            entity = Entity(
                name=entity_input.name.strip(),
                normalized_name=normalized_name,
                entity_type=entity_type,
            )
            db.add(entity)
            db.flush()
        
        entity_ids.append(entity.id)
    
    # Create collection run
    collection_run = CollectionRun(
        objective=DBObjectiveType[request.objective],
        entities_requested=[
            {"id": str(eid), "name": e.name, "type": e.type} 
            for eid, e in zip(entity_ids, request.entities)
        ],
        secondary_keywords=request.secondary_keywords or [],
        timeframe_days=request.timeframe_days,
        require_contact=request.require_contact,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
        region=request.region,
        city=request.city,
        source_count=1,  # ChatGPT is the single source
        status="RUNNING",
    )
    db.add(collection_run)
    db.commit()
    
    # Trigger AI collection task
    run_ai_collection_task.delay(
        run_id=str(collection_run.id),
        entity_ids=[str(eid) for eid in entity_ids],
        objective=request.objective,
        secondary_keywords=request.secondary_keywords or [],
        timeframe_days=request.timeframe_days,
        require_contact=request.require_contact,
        filters={
            "budget_min": request.budget_min,
            "budget_max": request.budget_max,
            "region": request.region,
            "city": request.city,
        }
    )
    
    return AdvancedCollectResponse(
        run_id=str(collection_run.id),
        entities_created=[str(eid) for eid in entity_ids],
        message=f"Collecte IA lancée pour {len(request.entities)} entité(s)"
    )


# =====================
# Collection Status
# =====================

@router.get("/standard/status", response_model=List[CollectionStatusResponse])
def get_standard_collection_status(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent standard collection runs status"""
    runs = db.query(IngestionRun).order_by(
        desc(IngestionRun.started_at)
    ).limit(limit).all()
    
    return [
        CollectionStatusResponse(
            id=str(run.id),
            type="standard",
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.completed_at,  # IngestionRun uses completed_at
            items_found=run.items_fetched or 0,
            items_new=run.items_new or 0,
            contacts_found=0,
            error_message=run.errors[0] if run.errors else None,  # First error from list
            brief_id=None,
        )
        for run in runs
    ]


@router.get("/advanced/status/{run_id}", response_model=CollectionStatusResponse)
def get_advanced_collection_status(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get advanced collection run status"""
    run = db.query(CollectionRun).filter(CollectionRun.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Collection run not found")
    
    return CollectionStatusResponse(
        id=str(run.id),
        type="advanced",
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        items_found=run.documents_new + run.documents_updated,
        items_new=run.documents_new,
        contacts_found=run.contacts_found,
        error_message=run.error_summary,
        brief_id=str(run.brief_id) if run.brief_id else None,
    )
