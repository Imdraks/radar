"""
API Dossiers - Gestion des dossiers enrichis

GET /dossiers - Liste des dossiers
GET /dossiers/{id} - Détail d'un dossier complet
POST /dossiers - Créer un dossier directement (mode IA)
PATCH /dossiers/{id} - Mettre à jour un dossier
DELETE /dossiers/{id} - Supprimer un dossier
POST /dossiers/{id}/regenerate - Régénérer un dossier
GET /dossiers/{id}/evidence - Liste des evidence d'un dossier
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func

from app.db import get_db
from app.db.models.user import User
from app.db.models.collections import (
    DossierV2, LeadItem, LeadItemKind, Evidence, SourceDocument, DossierState
)
from app.api.deps import get_current_user
from app.schemas.collections import (
    DossierResponse, DossierDetailResponse, DossierListResponse,
    CreateDossierRequest, DossierUpdateRequest,
    EvidenceSchema, SourceDocumentSchema, DossierStateEnum, DossierObjectiveEnum
)
from app.workers.collection_pipeline import run_dossier_builder_task

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])


# ================================================================
# GET /dossiers - Liste des dossiers
# ================================================================

@router.get("", response_model=DossierListResponse)
@router.get("/", response_model=DossierListResponse)
def list_dossiers(
    # Pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # Tri
    sort_by: str = Query("updated_at", regex="^(updated_at|created_at|quality_score)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    # Filtres
    state: Optional[List[DossierStateEnum]] = Query(None),
    objective: Optional[List[DossierObjectiveEnum]] = Query(None),
    search: Optional[str] = None,
    quality_min: Optional[int] = Query(None, ge=0, le=100),
    entity_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste paginée des dossiers avec filtres.
    
    - **state**: Filtrer par état (PENDING, PROCESSING, READY, ERROR)
    - **objective**: Filtrer par objectif
    - **search**: Recherche dans le titre et contenu
    - **quality_min**: Score qualité minimum
    """
    query = db.query(DossierV2)

    # ===== FILTRES =====

    # État
    if state:
        state_values = [s.value for s in state]
        query = query.filter(DossierV2.state.in_(state_values))

    # Objectif
    if objective:
        objective_values = [o.value for o in objective]
        query = query.filter(DossierV2.objective.in_(objective_values))

    # Recherche texte (via lead_item)
    if search:
        search_term = f"%{search.lower()}%"
        lead_ids = db.query(LeadItem.id).filter(
            func.lower(LeadItem.title).like(search_term)
        ).subquery()
        query = query.filter(DossierV2.lead_item_id.in_(lead_ids))

    # Score qualité
    if quality_min is not None:
        query = query.filter(DossierV2.quality_score >= quality_min)

    # Entity name (JSONB search)
    if entity_name:
        # Recherche dans target_entities JSONB - cast en texte pour recherche
        from sqlalchemy.dialects.postgresql import TEXT
        query = query.filter(
            func.cast(DossierV2.target_entities, TEXT).ilike(f'%{entity_name}%')
        )

    # ===== COMPTE TOTAL =====
    total = query.count()

    # ===== TRI =====
    sort_column = getattr(DossierV2, sort_by, DossierV2.updated_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # ===== PAGINATION =====
    dossiers = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response
    items = []
    for dossier in dossiers:
        lead_item = db.query(LeadItem).filter(LeadItem.id == dossier.lead_item_id).first()
        items.append(_dossier_to_response(dossier, lead_item, db))

    return DossierListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ================================================================
# GET /dossiers/{id} - Détail d'un dossier
# ================================================================

@router.get("/{dossier_id}", response_model=DossierDetailResponse)
def get_dossier(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail complet d'un dossier avec evidence et sections"""
    dossier = db.query(DossierV2).filter(DossierV2.id == dossier_id).first()

    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    lead_item = db.query(LeadItem).filter(LeadItem.id == dossier.lead_item_id).first()

    # Evidence
    evidence = db.query(Evidence).filter(
        Evidence.dossier_id == dossier_id
    ).all()

    # Documents sources
    documents = db.query(SourceDocument).filter(
        SourceDocument.dossier_id == dossier_id
    ).all()

    return DossierDetailResponse(
        id=dossier.id,
        lead_item_id=dossier.lead_item_id,
        lead_item_title=lead_item.title if lead_item else None,
        lead_item_url=lead_item.url_primary if lead_item else None,
        objective=dossier.objective,
        target_entities=dossier.target_entities,
        state=dossier.state,
        sections=dossier.sections,
        summary=dossier.summary,
        key_findings=dossier.key_findings,
        recommendations=dossier.recommendations,
        quality_score=dossier.quality_score,
        quality_breakdown=dossier.quality_breakdown,
        tokens_used=dossier.tokens_used,
        model_used=dossier.model_used,
        processing_time_ms=dossier.processing_time_ms,
        error_message=dossier.error_message,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
        evidence=[EvidenceSchema.from_orm(e) for e in evidence],
        source_documents=[SourceDocumentSchema.from_orm(d) for d in documents],
    )


# ================================================================
# POST /dossiers - Créer un dossier (mode IA direct)
# ================================================================

@router.post("", response_model=DossierResponse)
@router.post("/", response_model=DossierResponse)
def create_dossier(
    request: CreateDossierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Créer un dossier directement (mode IA).
    
    Peut être créé:
    - Depuis un lead_item existant
    - Depuis une URL fournie (crée un lead_item temporaire)
    - Depuis un texte brut (crée un lead_item temporaire)
    """
    lead_item_id = request.lead_item_id

    # Si pas de lead_item_id, créer un lead_item temporaire
    if not lead_item_id:
        if not request.source_url and not request.source_text:
            raise HTTPException(
                status_code=400,
                detail="Fournir lead_item_id, source_url ou source_text"
            )

        # Créer lead_item temporaire
        lead_item = LeadItem(
            kind=LeadItemKind.DOSSIER_CANDIDATE.value,
            title=request.title or "Dossier sans titre",
            description=request.source_text[:500] if request.source_text else None,
            url_primary=request.source_url,
            source_name="manual",
            source_type="manual",
        )
        db.add(lead_item)
        db.flush()
        lead_item_id = lead_item.id

    # Vérifier si dossier existe déjà
    existing = db.query(DossierV2).filter(
        DossierV2.lead_item_id == lead_item_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Un dossier existe déjà pour ce lead_item")

    # Créer le dossier
    entities = [{"name": e, "type": "ORGANIZATION"} for e in (request.target_entities or [])]

    dossier = DossierV2(
        lead_item_id=lead_item_id,
        objective=request.objective.value,
        target_entities=entities,
        state=DossierState.PENDING.value,
    )
    db.add(dossier)
    db.commit()
    db.refresh(dossier)

    # Lancer la tâche d'enrichissement
    run_dossier_builder_task.delay(str(dossier.id))

    lead_item = db.query(LeadItem).filter(LeadItem.id == lead_item_id).first()
    return _dossier_to_response(dossier, lead_item, db)


# ================================================================
# PATCH /dossiers/{id} - Mettre à jour un dossier
# ================================================================

@router.patch("/{dossier_id}", response_model=DossierResponse)
def update_dossier(
    dossier_id: UUID,
    request: DossierUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mettre à jour un dossier (sections, target_entities)"""
    dossier = db.query(DossierV2).filter(DossierV2.id == dossier_id).first()

    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    if request.target_entities is not None:
        entities = [{"name": e, "type": "ORGANIZATION"} for e in request.target_entities]
        dossier.target_entities = entities

    if request.sections is not None:
        dossier.sections = request.sections

    if request.summary is not None:
        dossier.summary = request.summary

    if request.key_findings is not None:
        dossier.key_findings = request.key_findings

    if request.recommendations is not None:
        dossier.recommendations = request.recommendations

    db.commit()
    db.refresh(dossier)

    lead_item = db.query(LeadItem).filter(LeadItem.id == dossier.lead_item_id).first()
    return _dossier_to_response(dossier, lead_item, db)


# ================================================================
# DELETE /dossiers/{id} - Supprimer un dossier
# ================================================================

@router.delete("/{dossier_id}")
def delete_dossier(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un dossier et son evidence"""
    dossier = db.query(DossierV2).filter(DossierV2.id == dossier_id).first()

    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    # Supprimer evidence
    db.query(Evidence).filter(Evidence.dossier_id == dossier_id).delete()

    # Supprimer documents
    db.query(SourceDocument).filter(SourceDocument.dossier_id == dossier_id).delete()

    # Supprimer dossier
    db.delete(dossier)
    db.commit()

    return {"message": "Dossier supprimé"}


# ================================================================
# POST /dossiers/{id}/regenerate - Régénérer un dossier
# ================================================================

@router.post("/{dossier_id}/regenerate")
def regenerate_dossier(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Régénérer un dossier (relancer GPT)"""
    dossier = db.query(DossierV2).filter(DossierV2.id == dossier_id).first()

    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    # Reset state
    dossier.state = DossierState.PENDING.value
    dossier.error_message = None
    dossier.sections = None
    dossier.summary = None
    dossier.key_findings = None
    dossier.recommendations = None
    dossier.quality_score = None
    dossier.quality_breakdown = None
    dossier.tokens_used = None

    # Supprimer ancienne evidence
    db.query(Evidence).filter(Evidence.dossier_id == dossier_id).delete()

    db.commit()

    # Relancer la tâche
    run_dossier_builder_task.delay(str(dossier_id))

    return {"message": "Régénération lancée", "dossier_id": str(dossier_id)}


# ================================================================
# GET /dossiers/{id}/evidence - Evidence d'un dossier
# ================================================================

@router.get("/{dossier_id}/evidence", response_model=List[EvidenceSchema])
def get_dossier_evidence(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste des evidence d'un dossier"""
    dossier = db.query(DossierV2).filter(DossierV2.id == dossier_id).first()

    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    evidence = db.query(Evidence).filter(
        Evidence.dossier_id == dossier_id
    ).all()

    return [EvidenceSchema.from_orm(e) for e in evidence]


# ================================================================
# HELPERS
# ================================================================

def _dossier_to_response(dossier: DossierV2, lead_item: Optional[LeadItem], db: Session) -> DossierResponse:
    """Convertit un DossierV2 en réponse"""
    evidence_count = db.query(func.count(Evidence.id)).filter(
        Evidence.dossier_id == dossier.id
    ).scalar() or 0

    return DossierResponse(
        id=dossier.id,
        lead_item_id=dossier.lead_item_id,
        lead_item_title=lead_item.title if lead_item else None,
        lead_item_url=lead_item.url_primary if lead_item else None,
        objective=dossier.objective,
        target_entities=dossier.target_entities,
        state=dossier.state,
        quality_score=dossier.quality_score,
        error_message=dossier.error_message,
        evidence_count=evidence_count,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
    )
