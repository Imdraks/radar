"""
API Leads (LeadItems) - Lead management with UUID-based entities

V2 API - Uses LeadItem model with UUIDs instead of legacy Opportunity (Integer IDs)

Routes:
GET /leads - Paginated list with server-side filters
GET /leads/{id} - Lead detail
PATCH /leads/{id} - Update (status, tags, assignment)
POST /leads/bulk-update - Bulk update
POST /leads/{id}/create-dossier - Create dossier from lead
GET /leads/stats - Statistics for filters
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, or_, and_

from app.db import get_db
from app.db.models.user import User
from app.db.models.collections import (
    LeadItem, LeadItemKind, LeadItemStatus, DossierV2,
    SourceDocumentV2, Evidence, DossierObjective, DossierState
)
from app.api.deps import get_current_user
from app.schemas.collections import (
    OpportunityResponse, OpportunityDetailResponse, OpportunityListResponse,
    UpdateOpportunityRequest, BulkUpdateOpportunitiesRequest,
    EvidenceSchema, SourceDocumentSchema, CreateDossierRequest,
    LeadItemStatusEnum, DossierObjectiveEnum
)
from app.workers.collection_pipeline import run_dossier_builder_task

router = APIRouter(prefix="/leads", tags=["Leads"])


# ================================================================
# GET /opportunities - Liste paginée avec filtres serveur
# ================================================================

@router.get("", response_model=OpportunityListResponse)
@router.get("/", response_model=OpportunityListResponse)
def list_opportunities(
    # Pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # Tri
    sort_by: str = Query("score_base", regex="^(score_base|created_at|deadline_at|budget_max|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    # Filtres
    search: Optional[str] = None,
    status: Optional[List[LeadItemStatusEnum]] = Query(None),
    score_min: Optional[int] = Query(None, ge=0, le=100),
    score_max: Optional[int] = Query(None, ge=0, le=100),
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    deadline_from: Optional[datetime] = None,
    deadline_to: Optional[datetime] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    source_name: Optional[str] = None,
    has_contact: Optional[bool] = None,
    has_deadline: Optional[bool] = None,
    has_dossier: Optional[bool] = None,
    tags: Optional[List[str]] = Query(None),
    assigned_to: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste paginée des opportunités avec filtres côté serveur.
    
    - **search**: Recherche dans titre, description, organisation
    - **status**: Filtrer par statut(s)
    - **score_min/max**: Plage de score
    - **budget_min/max**: Plage de budget
    - **deadline_from/to**: Plage de deadline
    - **has_contact**: Uniquement avec contact
    - **has_deadline**: Uniquement avec deadline
    """
    # Base query: seulement les OPPORTUNITY
    query = db.query(LeadItem).filter(LeadItem.kind == LeadItemKind.OPPORTUNITY.value)

    # ===== FILTRES =====
    
    # Recherche texte
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(LeadItem.title).like(search_term),
                func.lower(LeadItem.description).like(search_term),
                func.lower(LeadItem.organization_name).like(search_term),
            )
        )

    # Statuts
    if status:
        status_values = [s.value for s in status]
        query = query.filter(LeadItem.status.in_(status_values))

    # Score
    if score_min is not None:
        query = query.filter(LeadItem.score_base >= score_min)
    if score_max is not None:
        query = query.filter(LeadItem.score_base <= score_max)

    # Budget
    if budget_min is not None:
        query = query.filter(
            or_(
                LeadItem.budget_min >= budget_min,
                LeadItem.budget_max >= budget_min
            )
        )
    if budget_max is not None:
        query = query.filter(
            or_(
                LeadItem.budget_max <= budget_max,
                LeadItem.budget_min <= budget_max
            )
        )

    # Deadline
    if deadline_from:
        query = query.filter(LeadItem.deadline_at >= deadline_from)
    if deadline_to:
        query = query.filter(LeadItem.deadline_at <= deadline_to)

    # Localisation
    if region:
        query = query.filter(func.lower(LeadItem.location_region) == region.lower())
    if city:
        query = query.filter(func.lower(LeadItem.location_city).like(f"%{city.lower()}%"))

    # Source
    if source_name:
        query = query.filter(func.lower(LeadItem.source_name).like(f"%{source_name.lower()}%"))

    # Has contact
    if has_contact is not None:
        if has_contact:
            query = query.filter(
                or_(
                    LeadItem.contact_email.isnot(None),
                    LeadItem.contact_phone.isnot(None),
                    LeadItem.contact_url.isnot(None),
                )
            )
        else:
            query = query.filter(
                and_(
                    LeadItem.contact_email.is_(None),
                    LeadItem.contact_phone.is_(None),
                    LeadItem.contact_url.is_(None),
                )
            )

    # Has deadline
    if has_deadline is not None:
        if has_deadline:
            query = query.filter(LeadItem.deadline_at.isnot(None))
        else:
            query = query.filter(LeadItem.deadline_at.is_(None))

    # Has dossier
    if has_dossier is not None:
        dossier_ids = db.query(DossierV2.lead_item_id).subquery()
        if has_dossier:
            query = query.filter(LeadItem.id.in_(dossier_ids))
        else:
            query = query.filter(~LeadItem.id.in_(dossier_ids))

    # Tags (JSONB contains)
    if tags:
        for tag in tags:
            query = query.filter(LeadItem.tags.contains([tag]))

    # Assignation
    if assigned_to:
        query = query.filter(LeadItem.assigned_to == assigned_to)

    # ===== COMPTE TOTAL =====
    total = query.count()

    # ===== TRI =====
    sort_column = getattr(LeadItem, sort_by, LeadItem.score_base)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # ===== PAGINATION =====
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # ===== STATS POUR FILTRES =====
    stats = _compute_filter_stats(db)

    return OpportunityListResponse(
        items=[_lead_item_to_response(item, db) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
        score_distribution=stats.get("score_distribution"),
        budget_distribution=stats.get("budget_distribution"),
        status_counts=stats.get("status_counts"),
    )


# ================================================================
# GET /opportunities/{id} - Détail
# ================================================================

@router.get("/{opportunity_id}", response_model=OpportunityDetailResponse)
def get_opportunity(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail complet d'une opportunité avec evidence et documents"""
    item = db.query(LeadItem).filter(
        LeadItem.id == opportunity_id,
        LeadItem.kind == LeadItemKind.OPPORTUNITY.value
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    # Evidence
    evidence = db.query(Evidence).filter(
        Evidence.lead_item_id == opportunity_id
    ).all()

    # Documents sources
    documents = db.query(SourceDocumentV2).filter(
        SourceDocumentV2.lead_item_id == opportunity_id
    ).all()

    # Has dossier
    has_dossier = db.query(DossierV2).filter(
        DossierV2.lead_item_id == opportunity_id
    ).first() is not None

    return OpportunityDetailResponse(
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
        evidence=[EvidenceSchema.from_orm(e) for e in evidence],
        source_documents=[SourceDocumentSchema.from_orm(d) for d in documents],
        metadata=item.metadata,
    )


# ================================================================
# PATCH /opportunities/{id} - Mise à jour
# ================================================================

@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(
    opportunity_id: UUID,
    request: UpdateOpportunityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mettre à jour une opportunité (statut, tags, assignation)"""
    item = db.query(LeadItem).filter(
        LeadItem.id == opportunity_id,
        LeadItem.kind == LeadItemKind.OPPORTUNITY.value
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    if request.status:
        item.status = request.status.value
    if request.tags is not None:
        item.tags = request.tags
    if request.assigned_to is not None:
        item.assigned_to = request.assigned_to

    db.commit()
    db.refresh(item)

    return _lead_item_to_response(item, db)


# ================================================================
# POST /opportunities/bulk-update - Mise à jour en masse
# ================================================================

@router.post("/bulk-update")
def bulk_update_opportunities(
    request: BulkUpdateOpportunitiesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mise à jour en masse des opportunités"""
    items = db.query(LeadItem).filter(
        LeadItem.id.in_(request.ids),
        LeadItem.kind == LeadItemKind.OPPORTUNITY.value
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="Aucune opportunité trouvée")

    updated_count = 0
    for item in items:
        if request.status:
            item.status = request.status.value
        if request.assigned_to is not None:
            item.assigned_to = request.assigned_to
        if request.tags_add:
            current_tags = item.tags or []
            item.tags = list(set(current_tags + request.tags_add))
        if request.tags_remove:
            current_tags = item.tags or []
            item.tags = [t for t in current_tags if t not in request.tags_remove]
        updated_count += 1

    db.commit()

    return {"updated": updated_count, "message": f"{updated_count} opportunité(s) mise(s) à jour"}


# ================================================================
# POST /opportunities/{id}/create-dossier - Créer un dossier
# ================================================================

@router.post("/{opportunity_id}/create-dossier")
def create_dossier_from_opportunity(
    opportunity_id: UUID,
    objective: DossierObjectiveEnum = Query(...),
    target_entities: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Créer un dossier enrichi depuis une opportunité"""
    item = db.query(LeadItem).filter(
        LeadItem.id == opportunity_id,
        LeadItem.kind == LeadItemKind.OPPORTUNITY.value
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Opportunité non trouvée")

    # Vérifier si dossier existe déjà
    existing = db.query(DossierV2).filter(
        DossierV2.lead_item_id == opportunity_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Un dossier existe déjà pour cette opportunité")

    # Créer le dossier
    entities = [{"name": e, "type": "ORGANIZATION"} for e in (target_entities or [])]
    if not entities and item.organization_name:
        entities = [{"name": item.organization_name, "type": "ORGANIZATION"}]

    dossier = DossierV2(
        lead_item_id=opportunity_id,
        objective=objective.value,
        target_entities=entities,
        state=DossierState.PROCESSING.value,
    )
    db.add(dossier)
    db.commit()
    db.refresh(dossier)

    # Lancer la tâche d'enrichissement
    run_dossier_builder_task.delay(str(dossier.id))

    return {
        "dossier_id": str(dossier.id),
        "message": "Dossier en cours de création"
    }


# ================================================================
# GET /opportunities/stats - Statistiques pour filtres
# ================================================================

@router.get("/stats/distribution")
def get_opportunities_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Statistiques pour les filtres UI (distributions)"""
    return _compute_filter_stats(db)


# ================================================================
# HELPERS
# ================================================================

def _lead_item_to_response(item: LeadItem, db: Session) -> OpportunityResponse:
    """Convertit un LeadItem en réponse"""
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


def _compute_filter_stats(db: Session) -> dict:
    """Calcule les stats pour les filtres UI"""
    base_query = db.query(LeadItem).filter(LeadItem.kind == LeadItemKind.OPPORTUNITY.value)

    # Distribution des scores
    score_dist = {}
    for bucket_start in range(0, 100, 20):
        bucket_end = bucket_start + 20
        count = base_query.filter(
            LeadItem.score_base >= bucket_start,
            LeadItem.score_base < bucket_end
        ).count()
        score_dist[f"{bucket_start}-{bucket_end}"] = count

    # Distribution des budgets
    budget_ranges = [
        (0, 5000, "0-5k"),
        (5000, 15000, "5k-15k"),
        (15000, 50000, "15k-50k"),
        (50000, 100000, "50k-100k"),
        (100000, None, "100k+"),
    ]
    budget_dist = {}
    for min_val, max_val, label in budget_ranges:
        query = base_query.filter(LeadItem.budget_max >= min_val)
        if max_val:
            query = query.filter(LeadItem.budget_max < max_val)
        budget_dist[label] = query.count()

    # Comptage par statut
    status_counts = {}
    for status in LeadItemStatus:
        count = base_query.filter(LeadItem.status == status.value).count()
        status_counts[status.value] = count

    return {
        "score_distribution": score_dist,
        "budget_distribution": budget_dist,
        "status_counts": status_counts,
        "total": base_query.count(),
    }
