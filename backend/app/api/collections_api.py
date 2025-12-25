"""
API Collections - Gestion des collectes (Standard et IA)

POST /collections - Créer une nouvelle collecte
GET /collections - Liste paginée des collectes
GET /collections/{id} - Détail d'une collecte
GET /collections/{id}/logs - Logs d'une collecte
GET /collections/{id}/results - Résultats d'une collecte
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db import get_db
from app.db.models.user import User
from app.db.models.collections import (
    CollectionV2, CollectionLog, CollectionResult, LeadItem,
    CollectionType, CollectionStatus
)
from app.api.deps import get_current_user
from app.schemas.collections import (
    CreateCollectionRequest, CollectionResponse, CollectionDetailResponse,
    CollectionListResponse, CollectionLogSchema, CollectionStatsSchema,
    CollectionTypeEnum, OpportunityResponse
)
from app.workers.collection_pipeline import (
    run_standard_collection,
    run_ai_collection
)

router = APIRouter(prefix="/collections", tags=["Collections"])


# ================================================================
# POST /collections - Créer une collecte
# ================================================================

@router.post("", response_model=CollectionResponse)
@router.post("/", response_model=CollectionResponse)
def create_collection(
    request: CreateCollectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Créer et lancer une nouvelle collecte.
    
    - **type**: STANDARD (sources configurées) ou AI (ChatGPT)
    - **params**: Paramètres selon le type
    """
    # Créer l'entrée collection
    collection = CollectionV2(
        type=request.type.value,
        name=request.name or f"Collecte {request.type.value} - {datetime.utcnow().strftime('%d/%m %H:%M')}",
        status=CollectionStatus.QUEUED.value,
        params=request.params,
        created_by=current_user.id,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    # Lancer la tâche Celery selon le type
    if request.type == CollectionTypeEnum.STANDARD:
        run_standard_collection.delay(str(collection.id))
    else:
        run_ai_collection.delay(str(collection.id))

    # Log de création
    log = CollectionLog(
        collection_id=collection.id,
        level="INFO",
        message=f"Collecte créée et mise en queue",
        context={"params": request.params}
    )
    db.add(log)
    db.commit()

    return _collection_to_response(collection, db)


# ================================================================
# GET /collections - Liste paginée
# ================================================================

@router.get("", response_model=CollectionListResponse)
@router.get("/", response_model=CollectionListResponse)
def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[CollectionTypeEnum] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste paginée des collectes avec filtres"""
    query = db.query(CollectionV2)

    # Filtres
    if type:
        query = query.filter(CollectionV2.type == type.value)
    if status:
        query = query.filter(CollectionV2.status == status)

    # Compte total
    total = query.count()

    # Pagination
    query = query.order_by(desc(CollectionV2.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    collections = query.all()

    return CollectionListResponse(
        items=[_collection_to_response(c, db) for c in collections],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ================================================================
# GET /collections/{id} - Détail
# ================================================================

@router.get("/{collection_id}", response_model=CollectionDetailResponse)
def get_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail complet d'une collecte avec logs et stats"""
    collection = db.query(CollectionV2).filter(CollectionV2.id == collection_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collecte non trouvée")

    # Logs récents (100 derniers)
    logs = db.query(CollectionLog).filter(
        CollectionLog.collection_id == collection_id
    ).order_by(desc(CollectionLog.ts)).limit(100).all()

    # Sources consultées (depuis les documents)
    from app.db.models.collections import SourceDocument
    sources = db.query(SourceDocument.url).filter(
        SourceDocument.collection_id == collection_id,
        SourceDocument.url.isnot(None)
    ).distinct().all()

    response = _collection_to_response(collection, db)
    
    return CollectionDetailResponse(
        **response.dict(),
        logs=[CollectionLogSchema.from_orm(log) for log in logs],
        sources_consulted=[s[0] for s in sources if s[0]],
    )


# ================================================================
# GET /collections/{id}/logs - Logs paginés
# ================================================================

@router.get("/{collection_id}/logs")
def get_collection_logs(
    collection_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Logs paginés d'une collecte"""
    collection = db.query(CollectionV2).filter(CollectionV2.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collecte non trouvée")

    query = db.query(CollectionLog).filter(CollectionLog.collection_id == collection_id)
    
    if level:
        query = query.filter(CollectionLog.level == level.upper())

    total = query.count()
    
    logs = query.order_by(desc(CollectionLog.ts)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "items": [CollectionLogSchema.from_orm(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


# ================================================================
# GET /collections/{id}/results - Résultats (lead_items)
# ================================================================

@router.get("/{collection_id}/results")
def get_collection_results(
    collection_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Résultats (lead_items) produits par une collecte"""
    collection = db.query(CollectionV2).filter(CollectionV2.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collecte non trouvée")

    query = db.query(LeadItem).join(CollectionResult).filter(
        CollectionResult.collection_id == collection_id
    )

    total = query.count()
    
    items = query.order_by(desc(LeadItem.score_base)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "items": [_lead_item_to_response(item, db) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


# ================================================================
# HELPERS
# ================================================================

def _collection_to_response(collection: CollectionV2, db: Session) -> CollectionResponse:
    """Convertit un modèle Collection en réponse API"""
    # Compter les résultats
    results_count = db.query(CollectionResult).filter(
        CollectionResult.collection_id == collection.id
    ).count()

    # Stats
    stats = None
    if collection.stats:
        stats = CollectionStatsSchema(**collection.stats)

    return CollectionResponse(
        id=collection.id,
        type=collection.type,
        status=collection.status,
        name=collection.name,
        params=collection.params,
        started_at=collection.started_at,
        finished_at=collection.finished_at,
        duration_seconds=collection.duration_seconds,
        stats=stats,
        error=collection.error,
        created_at=collection.created_at,
        results_count=results_count,
    )


def _lead_item_to_response(item: LeadItem, db: Session) -> OpportunityResponse:
    """Convertit un LeadItem en réponse"""
    from app.db.models.collections import DossierV2
    
    has_dossier = db.query(DossierV2).filter(
        DossierV2.lead_item_id == item.id
    ).first() is not None

    return OpportunityResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        organization_name=item.organization_name,
        url_primary=item.url_primary,
        source_name=item.source_name,
        source_type=item.source_type,
        published_at=item.published_at,
        deadline_at=item.deadline_at,
        location_city=item.location_city,
        location_region=item.location_region,
        budget_min=item.budget_min,
        budget_max=item.budget_max,
        budget_display=item.budget_display,
        contact_email=item.contact_email,
        contact_phone=item.contact_phone,
        contact_url=item.contact_url,
        contact_name=item.contact_name,
        has_contact=item.has_contact,
        has_deadline=item.has_deadline,
        score_base=item.score_base or 0,
        score_breakdown=item.score_breakdown,
        status=item.status,
        tags=item.tags,
        assigned_to=item.assigned_to,
        has_dossier=has_dossier,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
