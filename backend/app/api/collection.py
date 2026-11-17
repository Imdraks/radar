"""
Collection API endpoints for entity-based collection system.
POST /collect - Start a new collection run
GET /runs/{run_id} - Get collection run status
GET /briefs - List briefs
GET /briefs/{brief_id} - Get a specific brief
GET /entities - List entities
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
import json
import redis
from app.core.config import settings

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.entity import (
    Entity, EntityType, Document, Extract, Contact, Brief, 
    CollectionRun, ObjectiveType as DBObjectiveType
)
from app.db.models.source import SourceConfig
from app.schemas.collection import (
    CollectRequest, CollectResponse,
    CollectionRunResponse, SourceRunStatus,
    EntityResponse, ContactResponse, BriefResponse,
    DocumentResponse, ContactRanked, UsefulFact, TimelineEvent, SourceUsed,
    ObjectiveType, EntityType as SchemaEntityType
)
from app.workers.collection_tasks import run_collection_task

router = APIRouter(prefix="/collection", tags=["collection"])


# ========================
# POST /collect
# ========================

@router.post("", response_model=CollectResponse)
@router.post("/", response_model=CollectResponse)
def start_collection(
    request: CollectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new collection run.
    Creates entities if they don't exist, then triggers collection tasks.
    """
    # Get active sources
    sources = db.query(SourceConfig).filter(SourceConfig.is_active == True).all()
    
    if not sources:
        raise HTTPException(
            status_code=400,
            detail="Aucune source active configurée. Ajoutez des sources dans l'onglet Sources."
        )
    
    # Create or get entities
    entity_ids = []
    for entity_input in request.entities:
        normalized_name = entity_input.name.lower().strip()
        entity_type = EntityType[entity_input.type.value]
        
        # Check if entity exists
        entity = db.query(Entity).filter(
            Entity.normalized_name == normalized_name,
            Entity.entity_type == entity_type
        ).first()
        
        if not entity:
            entity = Entity(
                workspace_id=db.info["workspace_id"],
                name=entity_input.name.strip(),
                normalized_name=normalized_name,
                entity_type=entity_type,
            )
            db.add(entity)
            db.flush()
        
        entity_ids.append(entity.id)
    
    # Create collection run
    collection_run = CollectionRun(
        workspace_id=db.info["workspace_id"],
        objective=DBObjectiveType[request.objective.value],
        entities_requested=[{"id": str(eid), "name": e.name, "type": e.type.value} 
                           for eid, e in zip(entity_ids, request.entities)],
        secondary_keywords=request.secondary_keywords or [],
        timeframe_days=request.timeframe_days,
        require_contact=request.require_contact,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
        region=request.region,
        city=request.city,
        source_count=len(sources),
        status="RUNNING",
    )
    db.add(collection_run)
    db.commit()
    
    # Register ownership before dispatch; unknown/expired tasks are never publicly observable.
    task_id = str(uuid4())
    try:
        with redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=2) as cache:
            cache.setex(f"task_progress_owner:{task_id}", 86400,
                        json.dumps([current_user.id, db.info["workspace_id"]]))
    except redis.RedisError as exc:
        collection_run.status = "FAILED"
        db.commit()
        raise HTTPException(503, "Task progress service unavailable; collection not dispatched") from exc
    task = run_collection_task.apply_async(task_id=task_id, kwargs=dict(
        run_id=str(collection_run.id),
        entity_ids=[str(eid) for eid in entity_ids],
        objective=request.objective.value,
        secondary_keywords=request.secondary_keywords or [],
        timeframe_days=request.timeframe_days,
        require_contact=request.require_contact,
        filters={
            "budget_min": request.budget_min,
            "budget_max": request.budget_max,
            "region": request.region,
            "city": request.city,
        }
    ))
    
    return CollectResponse(
        run_id=collection_run.id,
        source_count=len(sources),
        task_ids=[task.id],
        entities_created=entity_ids,
        message=f"Collecte lancée pour {len(request.entities)} entité(s) sur {len(sources)} source(s)"
    )


# ========================
# GET /runs/{run_id}
# ========================

@router.get("/runs/{run_id}", response_model=CollectionRunResponse)
def get_collection_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status and details of a collection run"""
    run = db.query(CollectionRun).filter(CollectionRun.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Collection run not found")
    
    return CollectionRunResponse(
        id=run.id,
        status=run.status,
        objective=ObjectiveType[run.objective.value],
        started_at=run.started_at,
        finished_at=run.finished_at,
        source_count=run.source_count,
        sources_success=run.sources_success,
        sources_failed=run.sources_failed,
        documents_new=run.documents_new,
        documents_updated=run.documents_updated,
        documents_fetched=run.documents_new + run.documents_updated,
        contacts_found=run.contacts_found,
        brief_id=run.brief_id,
        error_message=run.error_summary,
        entities_requested=run.entities_requested or [],
        source_runs=[SourceRunStatus(**sr) for sr in (run.source_runs or [])],
        error_summary=run.error_summary,
    )


# ========================
# GET /briefs
# ========================

@router.get("/briefs", response_model=List[BriefResponse])
def list_briefs(
    entity_id: Optional[UUID] = Query(None),
    objective: Optional[ObjectiveType] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List briefs with optional filters"""
    query = db.query(Brief).join(Entity)
    
    if entity_id:
        query = query.filter(Brief.entity_id == entity_id)
    if objective:
        query = query.filter(Brief.objective == DBObjectiveType[objective.value])
    
    query = query.order_by(Brief.generated_at.desc())
    briefs = query.offset(offset).limit(limit).all()
    
    return [_brief_to_response(b) for b in briefs]


@router.get("/briefs/{brief_id}", response_model=BriefResponse)
def get_brief(
    brief_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific brief by ID"""
    brief = db.query(Brief).filter(Brief.id == brief_id).first()
    
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    
    return _brief_to_response(brief)


def _brief_to_response(brief: Brief) -> BriefResponse:
    """Convert Brief model to response schema"""
    entity = brief.entity
    
    return BriefResponse(
        id=brief.id,
        entity_id=brief.entity_id,
        entity_name=entity.name if entity else None,
        entity_type=SchemaEntityType[entity.entity_type.value] if entity else None,
        objective=ObjectiveType[brief.objective.value],
        timeframe_days=brief.timeframe_days,
        overview=brief.overview,
        contacts_ranked=[ContactRanked(**c) for c in (brief.contacts_ranked or [])],
        useful_facts=[UsefulFact(**f) for f in (brief.useful_facts or [])],
        timeline=[TimelineEvent(**t) for t in (brief.timeline or [])],
        sources_used=[SourceUsed(**s) for s in (brief.sources_used or [])],
        document_count=brief.document_count,
        contact_count=brief.contact_count,
        completeness_score=brief.completeness_score,
        generated_at=brief.generated_at,
    )


# ========================
# GET /entities
# ========================

@router.get("/entities", response_model=List[EntityResponse])
def list_entities(
    entity_type: Optional[SchemaEntityType] = Query(None),
    search: Optional[str] = Query(None, min_length=2),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List entities with optional filters"""
    query = db.query(Entity)
    
    if entity_type:
        query = query.filter(Entity.entity_type == EntityType[entity_type.value])
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(Entity.normalized_name.ilike(search_term))
    
    query = query.order_by(Entity.updated_at.desc())
    entities = query.offset(offset).limit(limit).all()
    
    # Get document/contact counts
    results = []
    for entity in entities:
        doc_count = db.query(func.count(Document.id)).filter(Document.entity_id == entity.id).scalar()
        contact_count = db.query(func.count(Contact.id)).filter(Contact.entity_id == entity.id).scalar()
        
        results.append(EntityResponse(
            id=entity.id,
            name=entity.name,
            entity_type=SchemaEntityType[entity.entity_type.value],
            normalized_name=entity.normalized_name,
            aliases=entity.aliases or [],
            official_urls=entity.official_urls or [],
            description=entity.description,
            image_url=entity.image_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            document_count=doc_count,
            contact_count=contact_count,
        ))
    
    return results


@router.get("/entities/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific entity by ID"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    doc_count = db.query(func.count(Document.id)).filter(Document.entity_id == entity.id).scalar()
    contact_count = db.query(func.count(Contact.id)).filter(Contact.entity_id == entity.id).scalar()
    
    return EntityResponse(
        id=entity.id,
        name=entity.name,
        entity_type=SchemaEntityType[entity.entity_type.value],
        normalized_name=entity.normalized_name,
        aliases=entity.aliases or [],
        official_urls=entity.official_urls or [],
        description=entity.description,
        image_url=entity.image_url,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        document_count=doc_count,
        contact_count=contact_count,
    )


# ========================
# GET /entities/{entity_id}/contacts
# ========================

@router.get("/entities/{entity_id}/contacts", response_model=List[ContactResponse])
def get_entity_contacts(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all contacts for an entity, ordered by reliability"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    contacts = db.query(Contact).filter(
        Contact.entity_id == entity_id
    ).order_by(Contact.reliability_score.desc()).all()
    
    return contacts


# ========================
# GET /entities/{entity_id}/documents
# ========================

@router.get("/entities/{entity_id}/documents", response_model=List[DocumentResponse])
def get_entity_documents(
    entity_id: UUID,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all documents for an entity"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    documents = db.query(Document).filter(
        Document.entity_id == entity_id
    ).order_by(Document.published_at.desc().nullslast()).limit(limit).all()
    
    return documents
