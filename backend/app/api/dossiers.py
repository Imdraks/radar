"""
Dossier API endpoints
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.opportunity import Opportunity
from app.db.models.dossier import (
    Dossier, DossierState, 
    DossierEvidence, SourceDocument,
    WebEnrichmentRun
)
from app.workers.dossier_tasks import (
    build_dossier_task,
    web_enrich_task,
    full_dossier_pipeline_task,
    batch_build_dossiers_task,
)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class DossierSummary(BaseModel):
    """Summary of a dossier for list views"""
    id: UUID
    opportunity_id: UUID
    opportunity_title: str
    state: str
    summary_short: Optional[str]
    confidence_plus: int
    score_final: int
    quality_flags: List[str]
    missing_fields: List[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class DossierDetail(BaseModel):
    """Full dossier detail"""
    id: UUID
    opportunity_id: UUID
    state: str
    summary_short: Optional[str]
    summary_long: Optional[str]
    key_points: List[str]
    action_checklist: List[str]
    extracted_fields: dict
    confidence_plus: int
    score_final: int
    quality_flags: List[str]
    missing_fields: List[str]
    sources_used: List[str]
    gpt_model_used: Optional[str]
    tokens_used: int
    processing_time_ms: int
    created_at: str
    updated_at: str
    processed_at: Optional[str]
    enriched_at: Optional[str]
    
    # Related opportunity info
    opportunity_title: str
    opportunity_url: Optional[str]
    opportunity_organization: Optional[str]
    opportunity_score_base: int
    
    class Config:
        from_attributes = True


class EvidenceItem(BaseModel):
    """Evidence item"""
    id: UUID
    field_key: str
    value: Optional[str]
    provenance: str
    evidence_type: str
    evidence_ref: Optional[str]
    evidence_snippet: Optional[str]
    confidence: int
    source_url: Optional[str]
    retrieved_at: Optional[str]
    retrieval_method: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class SourceDocumentItem(BaseModel):
    """Source document item"""
    id: UUID
    doc_type: str
    source_url: Optional[str]
    fetched_at: Optional[str]
    created_at: str
    raw_text_preview: Optional[str] = Field(None, description="First 500 chars")
    
    class Config:
        from_attributes = True


class EnrichmentRunItem(BaseModel):
    """Enrichment run record"""
    id: UUID
    status: str
    target_fields: List[str]
    fields_found: List[str]
    fields_not_found: List[str]
    urls_consulted: List[str]
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    errors: List[str]
    
    class Config:
        from_attributes = True


class BuildDossierRequest(BaseModel):
    """Request to build a dossier"""
    force_rebuild: bool = False
    auto_enrich: bool = True


class EnrichDossierRequest(BaseModel):
    """Request to enrich a dossier"""
    target_fields: Optional[List[str]] = None
    auto_merge: bool = True


class BatchBuildRequest(BaseModel):
    """Request to build multiple dossiers"""
    opportunity_ids: List[UUID]
    force_rebuild: bool = False
    auto_enrich: bool = True


class TaskResponse(BaseModel):
    """Response for async task"""
    task_id: str
    message: str


# ============================================================================
# DOSSIER ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[DossierSummary])
async def list_dossiers(
    state: Optional[str] = Query(None, description="Filter by state"),
    q: Optional[str] = Query(None, description="Search in title/summary"),
    min_confidence: Optional[int] = Query(None, ge=0, le=100),
    has_missing_fields: Optional[bool] = Query(None, description="Only with missing fields"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List dossiers with filters"""
    query = db.query(Dossier).join(Opportunity)
    
    # Filter by state
    if state:
        try:
            state_enum = DossierState(state)
            query = query.filter(Dossier.state == state_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid state: {state}")
    
    # Search
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Opportunity.title.ilike(search),
                Dossier.summary_short.ilike(search),
                Dossier.summary_long.ilike(search),
            )
        )
    
    # Confidence filter
    if min_confidence is not None:
        query = query.filter(Dossier.confidence_plus >= min_confidence)
    
    # Missing fields filter
    if has_missing_fields is True:
        # JSON array not empty check varies by DB, using cast for postgres
        query = query.filter(Dossier.missing_fields != [])
    elif has_missing_fields is False:
        query = query.filter(Dossier.missing_fields == [])
    
    # Order by score_final desc
    query = query.order_by(Dossier.score_final.desc())
    
    # Pagination
    dossiers = query.offset(skip).limit(limit).all()
    
    return [
        DossierSummary(
            id=d.id,
            opportunity_id=d.opportunity_id,
            opportunity_title=d.opportunity.title if d.opportunity else "Unknown",
            state=d.state.value,
            summary_short=d.summary_short,
            confidence_plus=d.confidence_plus or 0,
            score_final=d.score_final or 0,
            quality_flags=d.quality_flags or [],
            missing_fields=d.missing_fields or [],
            created_at=d.created_at.isoformat() if d.created_at else "",
            updated_at=d.updated_at.isoformat() if d.updated_at else "",
        )
        for d in dossiers
    ]


@router.get("/{dossier_id}", response_model=DossierDetail)
async def get_dossier(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full dossier details"""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    
    if not dossier:
        raise HTTPException(404, "Dossier not found")
    
    opp = dossier.opportunity
    
    return DossierDetail(
        id=dossier.id,
        opportunity_id=dossier.opportunity_id,
        state=dossier.state.value,
        summary_short=dossier.summary_short,
        summary_long=dossier.summary_long,
        key_points=dossier.key_points or [],
        action_checklist=dossier.action_checklist or [],
        extracted_fields=dossier.extracted_fields or {},
        confidence_plus=dossier.confidence_plus or 0,
        score_final=dossier.score_final or 0,
        quality_flags=dossier.quality_flags or [],
        missing_fields=dossier.missing_fields or [],
        sources_used=dossier.sources_used or [],
        gpt_model_used=dossier.gpt_model_used,
        tokens_used=dossier.tokens_used or 0,
        processing_time_ms=dossier.processing_time_ms or 0,
        created_at=dossier.created_at.isoformat() if dossier.created_at else "",
        updated_at=dossier.updated_at.isoformat() if dossier.updated_at else "",
        processed_at=dossier.processed_at.isoformat() if dossier.processed_at else None,
        enriched_at=dossier.enriched_at.isoformat() if dossier.enriched_at else None,
        opportunity_title=opp.title if opp else "Unknown",
        opportunity_url=opp.url_primary if opp else None,
        opportunity_organization=opp.organization if opp else None,
        opportunity_score_base=opp.score if opp else 0,
    )


@router.get("/by-opportunity/{opportunity_id}", response_model=DossierDetail)
async def get_dossier_by_opportunity(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dossier for a specific opportunity"""
    dossier = db.query(Dossier).filter(
        Dossier.opportunity_id == opportunity_id
    ).first()
    
    if not dossier:
        raise HTTPException(404, "No dossier found for this opportunity")
    
    opp = dossier.opportunity
    
    return DossierDetail(
        id=dossier.id,
        opportunity_id=dossier.opportunity_id,
        state=dossier.state.value,
        summary_short=dossier.summary_short,
        summary_long=dossier.summary_long,
        key_points=dossier.key_points or [],
        action_checklist=dossier.action_checklist or [],
        extracted_fields=dossier.extracted_fields or {},
        confidence_plus=dossier.confidence_plus or 0,
        score_final=dossier.score_final or 0,
        quality_flags=dossier.quality_flags or [],
        missing_fields=dossier.missing_fields or [],
        sources_used=dossier.sources_used or [],
        gpt_model_used=dossier.gpt_model_used,
        tokens_used=dossier.tokens_used or 0,
        processing_time_ms=dossier.processing_time_ms or 0,
        created_at=dossier.created_at.isoformat() if dossier.created_at else "",
        updated_at=dossier.updated_at.isoformat() if dossier.updated_at else "",
        processed_at=dossier.processed_at.isoformat() if dossier.processed_at else None,
        enriched_at=dossier.enriched_at.isoformat() if dossier.enriched_at else None,
        opportunity_title=opp.title if opp else "Unknown",
        opportunity_url=opp.url_primary if opp else None,
        opportunity_organization=opp.organization if opp else None,
        opportunity_score_base=opp.score if opp else 0,
    )


@router.get("/{dossier_id}/evidence", response_model=List[EvidenceItem])
async def get_dossier_evidence(
    dossier_id: UUID,
    field_key: Optional[str] = Query(None, description="Filter by field"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all evidence for a dossier"""
    query = db.query(DossierEvidence).filter(
        DossierEvidence.dossier_id == dossier_id
    )
    
    if field_key:
        query = query.filter(DossierEvidence.field_key == field_key)
    
    evidence = query.order_by(DossierEvidence.confidence.desc()).all()
    
    return [
        EvidenceItem(
            id=e.id,
            field_key=e.field_key,
            value=e.value,
            provenance=e.provenance.value if e.provenance else "UNKNOWN",
            evidence_type=e.evidence_type.value if e.evidence_type else "UNKNOWN",
            evidence_ref=e.evidence_ref,
            evidence_snippet=e.evidence_snippet,
            confidence=e.confidence or 0,
            source_url=e.source_url,
            retrieved_at=e.retrieved_at.isoformat() if e.retrieved_at else None,
            retrieval_method=e.retrieval_method,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in evidence
    ]


@router.get("/{dossier_id}/sources", response_model=List[SourceDocumentItem])
async def get_dossier_sources(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get source documents used for a dossier"""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    
    if not dossier:
        raise HTTPException(404, "Dossier not found")
    
    # Get source documents for the opportunity
    docs = db.query(SourceDocument).filter(
        SourceDocument.opportunity_id == dossier.opportunity_id
    ).order_by(SourceDocument.created_at.desc()).all()
    
    return [
        SourceDocumentItem(
            id=d.id,
            doc_type=d.doc_type.value if d.doc_type else "UNKNOWN",
            source_url=d.source_url,
            fetched_at=d.fetched_at.isoformat() if d.fetched_at else None,
            created_at=d.created_at.isoformat() if d.created_at else "",
            raw_text_preview=d.raw_text[:500] if d.raw_text else None,
        )
        for d in docs
    ]


@router.get("/{dossier_id}/enrichments", response_model=List[EnrichmentRunItem])
async def get_dossier_enrichments(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get enrichment run history for a dossier"""
    runs = db.query(WebEnrichmentRun).filter(
        WebEnrichmentRun.dossier_id == dossier_id
    ).order_by(WebEnrichmentRun.started_at.desc()).all()
    
    return [
        EnrichmentRunItem(
            id=r.id,
            status=r.status,
            target_fields=r.target_fields or [],
            fields_found=r.fields_found or [],
            fields_not_found=r.fields_not_found or [],
            urls_consulted=r.urls_consulted or [],
            started_at=r.started_at.isoformat() if r.started_at else "",
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            duration_ms=r.duration_ms,
            errors=r.errors or [],
        )
        for r in runs
    ]


@router.delete("/{dossier_id}")
async def delete_dossier(
    dossier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dossier"""
    dossier = db.query(Dossier).filter(Dossier.id == dossier_id).first()
    
    if not dossier:
        raise HTTPException(404, "Dossier not found")
    
    db.delete(dossier)
    db.commit()
    
    return {"message": "Dossier deleted"}


# ============================================================================
# OPPORTUNITY -> DOSSIER ACTIONS
# ============================================================================

@router.post("/opportunities/{opportunity_id}/dossier/build", response_model=TaskResponse)
async def build_opportunity_dossier(
    opportunity_id: UUID,
    request: BuildDossierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build/rebuild a dossier for an opportunity"""
    # Check opportunity exists
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    
    # Queue the task
    task = build_dossier_task.delay(
        opportunity_id=str(opportunity_id),
        force_rebuild=request.force_rebuild,
        auto_enrich=request.auto_enrich
    )
    
    return TaskResponse(
        task_id=task.id,
        message=f"Dossier build started for opportunity {opportunity_id}"
    )


@router.post("/opportunities/{opportunity_id}/dossier/enrich", response_model=TaskResponse)
async def enrich_opportunity_dossier(
    opportunity_id: UUID,
    request: EnrichDossierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger web enrichment for an opportunity's dossier"""
    # Get dossier
    dossier = db.query(Dossier).filter(
        Dossier.opportunity_id == opportunity_id
    ).first()
    
    if not dossier:
        raise HTTPException(404, "Dossier not found for this opportunity. Build it first.")
    
    # Queue the task
    task = web_enrich_task.delay(
        dossier_id=str(dossier.id),
        target_fields=request.target_fields,
        auto_merge=request.auto_merge
    )
    
    return TaskResponse(
        task_id=task.id,
        message=f"Web enrichment started for dossier {dossier.id}"
    )


@router.post("/opportunities/{opportunity_id}/dossier/full-pipeline", response_model=TaskResponse)
async def full_pipeline_opportunity(
    opportunity_id: UUID,
    force_rebuild: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run full pipeline: build -> enrich -> merge"""
    # Check opportunity exists
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    
    # Queue the task
    task = full_dossier_pipeline_task.delay(
        opportunity_id=str(opportunity_id),
        force_rebuild=force_rebuild
    )
    
    return TaskResponse(
        task_id=task.id,
        message=f"Full dossier pipeline started for opportunity {opportunity_id}"
    )


@router.get("/opportunities/{opportunity_id}/dossier", response_model=DossierDetail)
async def get_opportunity_dossier(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dossier for an opportunity"""
    dossier = db.query(Dossier).filter(
        Dossier.opportunity_id == opportunity_id
    ).first()
    
    if not dossier:
        raise HTTPException(404, "Dossier not found for this opportunity")
    
    opp = dossier.opportunity
    
    return DossierDetail(
        id=dossier.id,
        opportunity_id=dossier.opportunity_id,
        state=dossier.state.value,
        summary_short=dossier.summary_short,
        summary_long=dossier.summary_long,
        key_points=dossier.key_points or [],
        action_checklist=dossier.action_checklist or [],
        extracted_fields=dossier.extracted_fields or {},
        confidence_plus=dossier.confidence_plus or 0,
        score_final=dossier.score_final or 0,
        quality_flags=dossier.quality_flags or [],
        missing_fields=dossier.missing_fields or [],
        sources_used=dossier.sources_used or [],
        gpt_model_used=dossier.gpt_model_used,
        tokens_used=dossier.tokens_used or 0,
        processing_time_ms=dossier.processing_time_ms or 0,
        created_at=dossier.created_at.isoformat() if dossier.created_at else "",
        updated_at=dossier.updated_at.isoformat() if dossier.updated_at else "",
        processed_at=dossier.processed_at.isoformat() if dossier.processed_at else None,
        enriched_at=dossier.enriched_at.isoformat() if dossier.enriched_at else None,
        opportunity_title=opp.title if opp else "Unknown",
        opportunity_url=opp.url_primary if opp else None,
        opportunity_organization=opp.organization if opp else None,
        opportunity_score_base=opp.score if opp else 0,
    )


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@router.post("/batch/build", response_model=TaskResponse)
async def batch_build_dossiers(
    request: BatchBuildRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build dossiers for multiple opportunities"""
    # Validate opportunities exist
    opp_ids = [str(oid) for oid in request.opportunity_ids]
    
    task = batch_build_dossiers_task.delay(
        opportunity_ids=opp_ids,
        force_rebuild=request.force_rebuild,
        auto_enrich=request.auto_enrich
    )
    
    return TaskResponse(
        task_id=task.id,
        message=f"Batch dossier build started for {len(opp_ids)} opportunities"
    )


# ============================================================================
# STATS
# ============================================================================

@router.get("/stats/overview")
async def get_dossier_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dossier statistics"""
    total = db.query(Dossier).count()
    ready = db.query(Dossier).filter(Dossier.state == DossierState.READY).count()
    processing = db.query(Dossier).filter(Dossier.state == DossierState.PROCESSING).count()
    failed = db.query(Dossier).filter(Dossier.state == DossierState.FAILED).count()
    
    # Count with missing fields
    with_missing = db.query(Dossier).filter(
        Dossier.state == DossierState.READY,
        Dossier.missing_fields != []
    ).count()
    
    # Average confidence
    from sqlalchemy import func
    avg_confidence = db.query(func.avg(Dossier.confidence_plus)).filter(
        Dossier.state == DossierState.READY
    ).scalar() or 0
    
    return {
        "total": total,
        "ready": ready,
        "processing": processing,
        "failed": failed,
        "with_missing_fields": with_missing,
        "average_confidence": round(avg_confidence, 1),
    }
