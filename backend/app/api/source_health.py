"""
Source Health API - Quality and stability monitoring
"""
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db import get_db
from app.db.models import SourceConfig, SourceHealth
from app.api.deps import get_current_user, get_current_admin_user
from app.schemas.radar_features import (
    SourceHealthMetrics,
    SourceHealthListResponse,
    SourceHealthSummary,
    SourceHealthOverview,
    SourceUpdateRequest,
)
from app.core.cache import cache_get, cache_set

# Cache TTLs
HEALTH_OVERVIEW_TTL = 300  # 5 minutes

router = APIRouter(prefix="/sources", tags=["sources"])


def compute_health_score(metrics: dict) -> int:
    """
    Compute health score from metrics.
    100 = perfect, 0 = completely broken
    """
    score = 100
    
    # Penalize low success rate
    success_rate = metrics.get("success_rate", 1.0)
    if success_rate < 0.9:
        score -= int((0.9 - success_rate) * 50)
    
    # Penalize high latency
    avg_latency = metrics.get("avg_latency_ms", 0)
    if avg_latency > 5000:
        score -= 20
    elif avg_latency > 2000:
        score -= 10
    
    # Penalize high duplicate rate
    dup_rate = metrics.get("duplicates_rate", 0)
    if dup_rate > 0.8:
        score -= 30
    elif dup_rate > 0.5:
        score -= 15
    
    # Penalize no items found
    items_found = metrics.get("items_found", 0)
    if items_found == 0:
        score -= 20
    
    return max(0, min(100, score))


def get_recommendation(avg_score: float, error_rate: float, items: int) -> Optional[str]:
    """Generate recommendation based on metrics"""
    if avg_score < 30:
        return "disable"
    elif avg_score < 50 or error_rate > 0.3:
        return "repair"
    elif avg_score > 80 and items > 10:
        return "prioritize"
    return None


@router.get("/health", response_model=SourceHealthListResponse)
def get_sources_health(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    source_id: Optional[int] = None,
    min_score: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get source health metrics"""
    if not date_from:
        date_from = date.today() - timedelta(days=7)
    if not date_to:
        date_to = date.today()
    
    query = db.query(SourceHealth).filter(
        SourceHealth.date >= date_from,
        SourceHealth.date <= date_to,
    )
    
    if source_id:
        query = query.filter(SourceHealth.source_id == source_id)
    
    if min_score is not None:
        query = query.filter(SourceHealth.health_score >= min_score)
    
    health_records = query.order_by(
        SourceHealth.date.desc(),
        SourceHealth.health_score.asc()
    ).limit(limit).all()
    
    # Get source names
    source_ids = list(set(h.source_id for h in health_records))
    sources = {s.id: s.name for s in db.query(SourceConfig).filter(
        SourceConfig.id.in_(source_ids)
    ).all()}
    
    metrics = []
    for h in health_records:
        metrics.append(SourceHealthMetrics(
            source_id=h.source_id,
            source_name=sources.get(h.source_id, "Unknown"),
            date=h.date,
            requests=h.requests,
            success_rate=h.success_rate,
            avg_latency_ms=h.avg_latency_ms,
            items_found=h.items_found,
            items_kept=h.items_kept,
            items_new=h.items_new,
            duplicates_rate=h.duplicates_rate,
            health_score=h.health_score,
            last_error=h.last_error,
            error_types=h.error_types or {},
        ))
    
    return SourceHealthListResponse(
        sources=metrics,
        total=len(metrics),
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/health/overview", response_model=SourceHealthOverview)
def get_sources_health_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get overview of all sources health"""
    # Check cache first
    cache_key = "source_health:overview"
    cached = cache_get(cache_key)
    if cached:
        return SourceHealthOverview(**cached)
    
    # Get all sources
    sources = db.query(SourceConfig).all()
    
    # Get health data for last 7 days
    week_ago = date.today() - timedelta(days=7)
    
    summaries = []
    total_health = 0
    sources_needing_attention = 0
    
    for source in sources:
        # Get health records for this source
        health_records = db.query(SourceHealth).filter(
            SourceHealth.source_id == source.id,
            SourceHealth.date >= week_ago,
        ).all()
        
        if health_records:
            avg_health = sum(h.health_score for h in health_records) / len(health_records)
            total_items = sum(h.items_new for h in health_records)
            total_errors = sum(h.error_count for h in health_records)
            total_requests = sum(h.requests for h in health_records)
            error_rate = total_errors / total_requests if total_requests > 0 else 0
        else:
            avg_health = 100 if source.is_active else 0
            total_items = 0
            error_rate = 0
        
        recommendation = get_recommendation(avg_health, error_rate, total_items)
        
        if recommendation == "disable" or recommendation == "repair":
            sources_needing_attention += 1
        
        summaries.append(SourceHealthSummary(
            source_id=source.id,
            source_name=source.name,
            is_active=source.is_active,
            avg_health_score=round(avg_health, 1),
            total_items_last_7_days=total_items,
            error_rate_last_7_days=round(error_rate, 3),
            recommendation=recommendation,
        ))
        
        total_health += avg_health
    
    # Sort by health score (worst first)
    summaries.sort(key=lambda s: s.avg_health_score)
    
    active_count = sum(1 for s in sources if s.is_active)
    
    result = SourceHealthOverview(
        sources=summaries,
        total_active=active_count,
        total_inactive=len(sources) - active_count,
        avg_health_score=round(total_health / len(sources), 1) if sources else 0,
        sources_needing_attention=sources_needing_attention,
    )
    
    # Cache the result
    cache_set(cache_key, result.model_dump(mode="json"), HEALTH_OVERVIEW_TTL)
    
    return result


@router.get("/health/{source_id}", response_model=List[SourceHealthMetrics])
def get_source_health_history(
    source_id: int,
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get health history for a specific source"""
    source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    date_from = date.today() - timedelta(days=days)
    
    health_records = db.query(SourceHealth).filter(
        SourceHealth.source_id == source_id,
        SourceHealth.date >= date_from,
    ).order_by(SourceHealth.date.desc()).all()
    
    return [
        SourceHealthMetrics(
            source_id=h.source_id,
            source_name=source.name,
            date=h.date,
            requests=h.requests,
            success_rate=h.success_rate,
            avg_latency_ms=h.avg_latency_ms,
            items_found=h.items_found,
            items_kept=h.items_kept,
            items_new=h.items_new,
            duplicates_rate=h.duplicates_rate,
            health_score=h.health_score,
            last_error=h.last_error,
            error_types=h.error_types or {},
        )
        for h in health_records
    ]


# Retained legacy helper; configuration writes use api/sources.py.
def update_source(
    source_id: int,
    data: SourceUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user),
):
    """Update source configuration (enable/disable)"""
    source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    if data.is_active is not None:
        source.is_active = data.is_active
        source.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(source)
    
    return {
        "id": str(source.id),
        "name": source.name,
        "is_active": source.is_active,
        "updated_at": source.updated_at.isoformat(),
    }


# Retained legacy helper; configuration lists use api/sources.py.
def list_sources(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all source configurations"""
    query = db.query(SourceConfig)
    
    if is_active is not None:
        query = query.filter(SourceConfig.is_active == is_active)
    
    sources = query.order_by(SourceConfig.name).all()
    
    return {
        "sources": [
            {
                "id": str(s.id),
                "name": s.name,
                "source_type": s.source_type.value if s.source_type else None,
                "url": s.url,
                "is_active": s.is_active,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                "total_items_fetched": s.total_items_fetched,
                "total_errors": s.total_errors,
            }
            for s in sources
        ],
        "total": len(sources),
    }
