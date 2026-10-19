"""
Discovery V3 API Endpoints
Handles artist discovery feed, search, and enrichment jobs.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.api.deps import get_db, get_current_user, get_user_workspace_id
from app.db.models.user import User
from app.db.models.discovery import (
    DiscoveryArtist,
    DiscoverySnapshot,
    DiscoveryComputedMetrics,
    DiscoveryCandidate,
    DiscoveryEnrichmentJob,
    DataQuality,
    TimingBucket,
    Recommendation,
    CandidateType,
    SnapshotSource,
    SnapshotStatus,
    JobStatus,
    JobStep,
    InputType,
)
from app.db.models.artist_analysis import ArtistAnalysis
from app.workers.discovery_pipeline import run_enrichment_pipeline

router = APIRouter(prefix="/discovery", tags=["discovery"])


# ============================================================================
# SCHEMAS
# ============================================================================

class FeedType(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    TRENDING = "TRENDING"


class FeedFilters(BaseModel):
    timing: Optional[List[str]] = None  # ["IMMINENT", "1_3M", "3_6M"]
    score_min: Optional[int] = None
    score_max: Optional[int] = None
    listeners_min: Optional[int] = None
    listeners_max: Optional[int] = None
    country: Optional[str] = None
    recommendation: Optional[List[str]] = None  # ["SIGN", "WATCH"]


class ArtistReason(BaseModel):
    label: str
    value: Optional[str] = None
    impact: Optional[int] = None


class ArtistCardResponse(BaseModel):
    """Response format for artist cards in feed."""
    id: Any
    name: str
    image_url: Optional[str] = None
    timing_bucket: Optional[str] = None
    timing_label: Optional[str] = None
    score: int = 0
    recommendation: Optional[str] = None
    monthly_listeners: Optional[int] = None
    followers: Optional[int] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    data_quality: Optional[str] = None
    drivers: List[ArtistReason] = []
    risks: List[ArtistReason] = []
    signals: List[str] = []
    rank_score: Optional[float] = None
    candidate_type: Optional[str] = None
    last_enriched_at: Optional[datetime] = None
    is_stale: bool = False


class FeedResponse(BaseModel):
    artists: List[ArtistCardResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    input_type: InputType = InputType.NAME


class JobResponse(BaseModel):
    id: str  # UUID as string
    artist_name: Optional[str] = None
    input_type: str
    input_value: str
    status: str
    current_step: Optional[str] = None
    progress: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class QueueResponse(BaseModel):
    jobs: List[JobResponse]
    running: int
    pending: int
    completed_24h: int


class ArtistDetailResponse(BaseModel):
    """Full artist detail for expanded view."""
    id: Any
    name: str
    normalized_name: str
    viberate_id: Optional[str] = None
    spotify_id: Optional[str] = None
    image_url: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    genres: List[str] = []
    
    evidence: List[dict] = []
    metric_classification: dict = {}
    prediction_validation: str = "not_calibrated"
    missing_data: List[str] = []
    # Latest metrics
    score: int = 0
    timing_bucket: Optional[str] = None
    recommendation: Optional[str] = None
    monthly_listeners: Optional[int] = None
    followers: Optional[int] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    data_quality: Optional[str] = None
    
    # Analysis
    drivers: List[ArtistReason] = []
    risks: List[ArtistReason] = []
    patterns: List[str] = []
    signals: List[str] = []
    summary: Optional[str] = None
    booking_range: Optional[dict] = None
    
    # AI Intelligence (from artist_analyses)
    ai_summary: Optional[str] = None
    ai_tier: Optional[str] = None
    ai_score: Optional[float] = None
    growth_trend: Optional[str] = None
    growth_rate_monthly: Optional[float] = None
    predicted_listeners_30d: Optional[int] = None
    predicted_listeners_90d: Optional[int] = None
    predicted_listeners_180d: Optional[int] = None
    confidence_score: Optional[float] = None
    
    # SWOT
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    opportunities: Optional[List[str]] = None
    threats: Optional[List[str]] = None
    
    # Booking Intelligence
    optimal_fee: Optional[float] = None
    negotiation_power: Optional[str] = None
    best_booking_window: Optional[str] = None
    event_type_fit: Optional[dict] = None
    territory_strength: Optional[dict] = None
    seasonal_demand: Optional[dict] = None
    
    # Content & Viral
    viral_potential: Optional[float] = None
    best_platforms: Optional[List[str]] = None
    content_recommendations: Optional[List[str]] = None
    ai_recommendations: Optional[List[str]] = None
    
    # Social breakdown
    instagram_followers: Optional[int] = None
    tiktok_followers: Optional[int] = None
    youtube_subscribers: Optional[int] = None
    
    # History
    last_enriched_at: Optional[datetime] = None
    created_at: datetime
    
    # Flags
    is_stale: bool = False
    has_spotify: bool = False
    has_viberate: bool = False


# ============================================================================
# FEED ENDPOINTS
# ============================================================================

@router.get("/feed/{feed_type}", response_model=FeedResponse)
async def get_discovery_feed(
    feed_type: FeedType,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    timing: Optional[str] = Query(None, description="Comma-separated timing filters"),
    score_min: Optional[int] = Query(None, ge=0, le=100),
    score_max: Optional[int] = Query(None, ge=0, le=100),
    listeners_min: Optional[int] = Query(None, ge=0),
    listeners_max: Optional[int] = Query(None),
    recommendation: Optional[str] = Query(None, description="Comma-separated recommendations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Get discovery feed (RECOMMENDED or TRENDING).
    Returns pre-computed candidates from DiscoveryCandidate table.
    """
    offset = (page - 1) * limit
    
    # Base query - join with artist only (metrics fetched in loop for latest)
    query = db.query(
        DiscoveryCandidate,
        DiscoveryArtist,
    ).join(
        DiscoveryArtist,
        DiscoveryCandidate.artist_id == DiscoveryArtist.id
    ).filter(
        DiscoveryCandidate.workspace_id == workspace_id,
        DiscoveryCandidate.candidate_type == feed_type.value,
        DiscoveryCandidate.ttl_expires_at > datetime.utcnow(),
    )
    
    # Note: Filtering by metrics fields disabled for now - fetch metrics in loop
    # TODO: Reimplement with proper subquery join for filtering
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    results = query.order_by(
        desc(DiscoveryCandidate.rank_score)
    ).offset(offset).limit(limit).all()
    
    # Map to response
    artists = []
    stale_threshold = datetime.utcnow() - timedelta(hours=24)
    
    for candidate, artist in results:
        # Get latest metrics for this artist
        metrics = db.query(DiscoveryComputedMetrics).filter(
            DiscoveryComputedMetrics.artist_id == artist.id
        ).order_by(desc(DiscoveryComputedMetrics.computed_at)).first()
        
        # Apply filters in memory (if any were specified)
        if timing:
            timing_list = [t.strip().upper() for t in timing.split(",")]
            if not metrics or metrics.timing_bucket not in timing_list:
                continue
        if score_min is not None and (not metrics or metrics.score < score_min):
            continue
        if score_max is not None and (not metrics or metrics.score > score_max):
            continue
        if listeners_min is not None and (not metrics or not metrics.monthly_listeners or metrics.monthly_listeners < listeners_min):
            continue
        if listeners_max is not None and (not metrics or not metrics.monthly_listeners or metrics.monthly_listeners > listeners_max):
            continue
        if recommendation:
            rec_list = [r.strip().upper() for r in recommendation.split(",")]
            if not metrics or metrics.recommendation not in rec_list:
                continue
        
        is_stale = bool(artist.last_enriched_at and artist.last_enriched_at < stale_threshold)
        
        # Get timing label
        timing_labels = {
            "IMMINENT": "< 1 mois",
            "1_3M": "1-3 mois",
            "3_6M": "3-6 mois",
            "6_12M": "6-12 mois",
            "LONG": "> 12 mois",
        }
        
        card = ArtistCardResponse(
            id=artist.id,
            name=artist.canonical_name,
            image_url=artist.image_url,
            timing_bucket=metrics.timing_bucket if metrics else None,
            timing_label=timing_labels.get(metrics.timing_bucket) if metrics else None,
            score=metrics.score if metrics else 0,
            recommendation=metrics.recommendation if metrics else None,
            monthly_listeners=metrics.monthly_listeners or None if metrics else None,
            followers=metrics.spotify_followers or metrics.total_social_followers or None if metrics else None,
            velocity=metrics.velocity if metrics else None,
            acceleration=metrics.acceleration if metrics else None,
            data_quality=metrics.data_quality if metrics else None,
            drivers=metrics.drivers[:3] if metrics and metrics.drivers else [],
            risks=metrics.penalties[:2] if metrics and metrics.penalties else [],
            signals=metrics.signals[:3] if metrics and metrics.signals else [],
            rank_score=candidate.rank_score,
            candidate_type=candidate.candidate_type,
            last_enriched_at=artist.last_enriched_at,
            is_stale=is_stale,
        )
        artists.append(card)
    
    return FeedResponse(
        artists=artists,
        total=total,
        page=page,
        limit=limit,
        has_more=(offset + limit) < total,
    )


# ============================================================================
# SEARCH & ENRICHMENT
# ============================================================================

@router.post("/search", response_model=JobResponse)
async def search_artist(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Search for an artist and create enrichment job.
    Returns immediately with job ID for polling.
    """
    
    # Normalize name for dedup check
    normalized = DiscoveryArtist.normalize_name(request.query)
    
    # Check if artist already exists (anti-doublon)
    existing = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.workspace_id == workspace_id,
        DiscoveryArtist.normalized_name == normalized,
        DiscoveryArtist.is_deleted == False,
    ).first()
    
    if existing and existing.last_enriched_at:
        # Check if recent enough (< 24h)
        if existing.last_enriched_at > datetime.utcnow() - timedelta(hours=24):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ALREADY_EXISTS",
                    "message": f"Artiste '{request.query}' déjà dans la base (enrichi il y a moins de 24h)",
                    "artist_id": str(existing.id),
                }
            )
    
    # Check for running job on same input
    running_job = db.query(DiscoveryEnrichmentJob).filter(
        DiscoveryEnrichmentJob.workspace_id == workspace_id,
        DiscoveryEnrichmentJob.input_value == request.query,
        DiscoveryEnrichmentJob.status.in_(["QUEUED", "RUNNING"]),
    ).first()
    
    if running_job:
        return JobResponse(
            id=str(running_job.id),
            artist_name=running_job.artist.canonical_name if running_job.artist else None,
            input_type=running_job.input_type,
            input_value=running_job.input_value,
            status=running_job.status,
            current_step=running_job.current_step,
            progress=running_job.progress_pct,
            started_at=running_job.started_at,
        )
    
    # Create new enrichment job
    job = DiscoveryEnrichmentJob(
        workspace_id=workspace_id,
        input_type=request.input_type.value,
        input_value=request.query,
        status=JobStatus.QUEUED.value,
        current_step=JobStep.MATCH.value,
        progress_pct=0,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Trigger async pipeline
    run_enrichment_pipeline.delay(str(job.id))
    
    return JobResponse(
        id=str(job.id),
        input_type=job.input_type,
        input_value=job.input_value,
        status=job.status,
        current_step=job.current_step,
        progress=0,
        started_at=job.started_at,
    )


@router.post("/artist/{artist_id}/refresh", response_model=JobResponse)
async def refresh_artist(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Trigger re-enrichment of an existing artist.
    """
    
    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == artist_id,
        DiscoveryArtist.workspace_id == workspace_id,
        DiscoveryArtist.is_deleted == False,
    ).first()
    
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    # Check for running job
    running_job = db.query(DiscoveryEnrichmentJob).filter(
        DiscoveryEnrichmentJob.artist_id == artist_id,
        DiscoveryEnrichmentJob.status.in_(["QUEUED", "RUNNING"]),
    ).first()
    
    if running_job:
        return JobResponse(
            id=str(running_job.id),
            artist_name=artist.canonical_name,
            input_type=running_job.input_type,
            input_value=running_job.input_value,
            status=running_job.status,
            current_step=running_job.current_step,
            progress=running_job.progress_pct,
            started_at=running_job.started_at,
        )
    
    # Create new job
    job = DiscoveryEnrichmentJob(
        workspace_id=workspace_id,
        artist_id=artist_id,
        input_type=InputType.NAME.value,
        input_value=artist.canonical_name,
        status=JobStatus.QUEUED.value,
        current_step=JobStep.VIBERATE.value,  # Skip MATCH for existing artist
        progress_pct=0,
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Trigger async pipeline
    run_enrichment_pipeline.delay(str(job.id))
    
    return JobResponse(
        id=str(job.id),
        artist_name=artist.canonical_name,
        input_type=job.input_type,
        input_value=job.input_value,
        status=job.status,
        current_step=job.current_step,
        progress=0,
        started_at=job.started_at,
    )


# ============================================================================
# JOB QUEUE
# ============================================================================

@router.get("/queue", response_model=QueueResponse)
async def get_job_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Get current enrichment job queue for workspace.
    """
    
    # Get recent jobs (last 24h or still active)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    jobs_query = db.query(DiscoveryEnrichmentJob).outerjoin(
        DiscoveryArtist,
        DiscoveryEnrichmentJob.artist_id == DiscoveryArtist.id
    ).filter(
        DiscoveryEnrichmentJob.workspace_id == workspace_id,
        or_(
            DiscoveryEnrichmentJob.status.in_(["QUEUED", "RUNNING"]),
            DiscoveryEnrichmentJob.started_at >= cutoff,
        )
    ).order_by(
        desc(DiscoveryEnrichmentJob.started_at)
    ).limit(50).all()
    
    jobs = []
    running_count = 0
    pending_count = 0
    completed_count = 0
    
    for job in jobs_query:
        if job.status == "RUNNING":
            running_count += 1
        elif job.status == "QUEUED":
            pending_count += 1
        elif job.status == "DONE":
            completed_count += 1
        
        jobs.append(JobResponse(
            id=str(job.id),
            artist_name=job.artist.canonical_name if job.artist else None,
            input_type=job.input_type,
            input_value=job.input_value,
            status=job.status,
            current_step=job.current_step,
            progress=job.progress_pct,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
        ))
    
    return QueueResponse(
        jobs=jobs,
        running=running_count,
        pending=pending_count,
        completed_24h=completed_count,
    )


@router.get("/job/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Get status of a specific enrichment job.
    """
    
    job = db.query(DiscoveryEnrichmentJob).filter(
        DiscoveryEnrichmentJob.id == job_id,
        DiscoveryEnrichmentJob.workspace_id == workspace_id,
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    return JobResponse(
        id=str(job.id),
        artist_name=job.artist.canonical_name if job.artist else None,
        input_type=job.input_type,
        input_value=job.input_value,
        status=job.status,
        current_step=job.current_step,
        progress=job.progress_pct,
        error_code=job.error_code,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


# ============================================================================
# ARTIST DETAIL
# ============================================================================

@router.get("/artist/{artist_id}", response_model=ArtistDetailResponse)
async def get_artist_detail(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Get full artist detail with all metrics.
    """
    
    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == artist_id,
        DiscoveryArtist.workspace_id == workspace_id,
        DiscoveryArtist.is_deleted == False,
    ).first()
    
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    # Get latest metrics
    metrics = db.query(DiscoveryComputedMetrics).filter(
        DiscoveryComputedMetrics.artist_id == artist_id,
    ).order_by(desc(DiscoveryComputedMetrics.computed_at)).first()
    
    # Get AI intelligence from artist_analyses
    analysis = db.query(ArtistAnalysis).filter(
        ArtistAnalysis.workspace_id == workspace_id,
        ArtistAnalysis.artist_name == artist.canonical_name,
    ).order_by(desc(ArtistAnalysis.created_at)).first()
    
    snapshots = db.query(DiscoverySnapshot).filter(DiscoverySnapshot.artist_id == artist.id).order_by(
        desc(DiscoverySnapshot.fetched_at)).limit(20).all()
    latest_by_source = {}
    for snapshot in snapshots:
        latest_by_source.setdefault(snapshot.source, snapshot)
    estimated_listeners = any((snap.raw_payload or {}).get("monthly_listeners_estimated") for snap in latest_by_source.values())
    evidence = [{"source": snap.source, "collected_at": snap.fetched_at,
                 "status": snap.status, "error_code": snap.error_code,
                 "contains_deezer_data": bool((snap.raw_payload or {}).get("deezer_fans")),
                 "expires_at": snap.ttl_expires_at} for snap in latest_by_source.values()]
    missing = []
    if not metrics or not metrics.monthly_listeners or estimated_listeners:
        missing.append("monthly_listeners")
    if not metrics or not metrics.spotify_followers:
        missing.append("spotify_followers")
    if not metrics or not metrics.fee_estimate_min:
        missing.append("booking_fee_estimate")
    # Check if stale
    stale_threshold = datetime.utcnow() - timedelta(hours=24)
    is_stale = bool(artist.last_enriched_at and artist.last_enriched_at < stale_threshold)
    
    return ArtistDetailResponse(
        evidence=evidence,
        missing_data=missing,
        metric_classification={"score": "heuristic", "fee": "estimate", "growth": "projection",
                               "monthly_listeners": "estimate" if estimated_listeners else "collected_or_missing",
                               "confidence": "not_calibrated"},
        id=artist.id,
        name=artist.canonical_name,
        normalized_name=artist.normalized_name,
        viberate_id=artist.viberate_url,
        spotify_id=artist.spotify_artist_id,
        image_url=artist.image_url,
        country=artist.country,
        city=None,
        genres=artist.genres or [],
        
        score=metrics.score if metrics else 0,
        timing_bucket=metrics.timing_bucket if metrics else None,
        recommendation=metrics.recommendation if metrics else None,
        monthly_listeners=metrics.monthly_listeners if metrics and not estimated_listeners else None,
        followers=metrics.spotify_followers or metrics.total_social_followers or None if metrics else None,
        velocity=metrics.velocity if metrics else None,
        acceleration=metrics.acceleration if metrics else None,
        data_quality=metrics.data_quality if metrics else None,
        
        drivers=metrics.drivers or [] if metrics else [],
        risks=metrics.penalties or [] if metrics else [],
        patterns=metrics.patterns or [] if metrics else [],
        signals=metrics.signals or [] if metrics else [],
        summary=analysis.ai_summary if analysis else None,
        booking_range={"min": metrics.fee_estimate_min, "max": metrics.fee_estimate_max} if metrics and metrics.fee_estimate_min else None,
        
        # AI Intelligence
        ai_summary=analysis.ai_summary if analysis else None,
        ai_tier=analysis.ai_tier if analysis else None,
        ai_score=analysis.ai_score if analysis else None,
        growth_trend=analysis.growth_trend if analysis else None,
        growth_rate_monthly=analysis.growth_rate_monthly if analysis else None,
        predicted_listeners_30d=analysis.predicted_listeners_30d if analysis else None,
        predicted_listeners_90d=analysis.predicted_listeners_90d if analysis else None,
        predicted_listeners_180d=analysis.predicted_listeners_180d if analysis else None,
        confidence_score=None,  # No calibrated certainty percentage available.
        
        # SWOT
        strengths=analysis.strengths if analysis else None,
        weaknesses=analysis.weaknesses if analysis else None,
        opportunities=analysis.opportunities if analysis else None,
        threats=analysis.threats if analysis else None,
        
        # Booking Intelligence
        optimal_fee=None,  # Only the indicative min/max range is presented.
        negotiation_power=analysis.negotiation_power if analysis else None,
        best_booking_window=analysis.best_booking_window if analysis else None,
        event_type_fit=analysis.event_type_fit if analysis else None,
        territory_strength=analysis.territory_strength if analysis else None,
        seasonal_demand=analysis.seasonal_demand if analysis else None,
        
        # Content & Viral
        viral_potential=analysis.viral_potential if analysis else None,
        best_platforms=analysis.best_platforms if analysis else None,
        content_recommendations=analysis.content_recommendations if analysis else None,
        ai_recommendations=analysis.ai_recommendations if analysis else None,
        
        # Social breakdown
        instagram_followers=metrics.instagram_followers if metrics else None,
        tiktok_followers=metrics.tiktok_followers if metrics else None,
        youtube_subscribers=metrics.youtube_subscribers if metrics else None,
        
        last_enriched_at=artist.last_enriched_at,
        created_at=artist.created_at,
        
        is_stale=is_stale,
        has_spotify=artist.spotify_artist_id is not None,
        has_viberate=artist.viberate_url is not None,
    )


# ============================================================================
# ARTIST MANAGEMENT
# ============================================================================

@router.delete("/artist/{artist_id}")
async def delete_artist(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    Soft delete an artist from discovery.
    """
    
    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == artist_id,
        DiscoveryArtist.workspace_id == workspace_id,
    ).first()
    
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    artist.is_deleted = True
    db.commit()
    
    return {"status": "OK", "message": f"Artiste '{artist.canonical_name}' supprimé"}


@router.get("/artists", response_model=List[ArtistCardResponse])
async def list_all_artists(
    search: Optional[str] = Query(None, min_length=2),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
):
    """
    List all artists in workspace (for autocomplete, etc.).
    """
    offset = (page - 1) * limit
    
    query = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.workspace_id == workspace_id,
        DiscoveryArtist.is_deleted == False,
    )
    
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.filter(DiscoveryArtist.normalized_name.ilike(search_pattern))
    
    results = query.order_by(
        DiscoveryArtist.canonical_name
    ).offset(offset).limit(limit).all()
    
    artists = []
    stale_threshold = datetime.utcnow() - timedelta(hours=24)
    
    for artist in results:
        # Get latest metrics
        metrics = db.query(DiscoveryComputedMetrics).filter(
            DiscoveryComputedMetrics.artist_id == artist.id,
        ).order_by(desc(DiscoveryComputedMetrics.computed_at)).first()
        
        is_stale = bool(artist.last_enriched_at and artist.last_enriched_at < stale_threshold)
        
        card = ArtistCardResponse(
            id=artist.id,
            name=artist.canonical_name,
            image_url=artist.image_url,
            timing_bucket=metrics.timing_bucket if metrics else None,
            score=metrics.score if metrics else 0,
            recommendation=metrics.recommendation if metrics else None,
            monthly_listeners=metrics.monthly_listeners if metrics else None,
            velocity=metrics.velocity if metrics else None,
            data_quality=metrics.data_quality if metrics else None,
            last_enriched_at=artist.last_enriched_at,
            is_stale=is_stale,
        )
        artists.append(card)
    
    return artists
