"""
Dashboard endpoints with Redis caching for performance
"""
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import Opportunity, OpportunityStatus, OpportunityCategory
from app.db.models.ingestion import IngestionRun, IngestionStatus
from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Cache TTL constants
STATS_CACHE_TTL = 60  # 1 minute for dashboard stats
TOP_OPPS_CACHE_TTL = 120  # 2 minutes for top opportunities


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get dashboard statistics with caching"""
    cache_key = f"dashboard:stats:{current_user.id}:{db.info.get('workspace_id')}"
    
    # Try cache first
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    
    # Total opportunities by status
    status_counts = dict(
        db.query(Opportunity.status, func.count(Opportunity.id))
        .group_by(Opportunity.status)
        .all()
    )
    
    # Total by category
    category_counts = dict(
        db.query(Opportunity.category, func.count(Opportunity.id))
        .group_by(Opportunity.category)
        .all()
    )
    
    # New in last 24h
    new_24h = db.query(func.count(Opportunity.id)).filter(
        Opportunity.created_at >= now - timedelta(hours=24)
    ).scalar()
    
    # New in last 7 days
    new_7d = db.query(func.count(Opportunity.id)).filter(
        Opportunity.created_at >= now - timedelta(days=7)
    ).scalar()
    
    # Deadlines in next 7 days
    deadlines_7d = db.query(func.count(Opportunity.id)).filter(
        and_(
            Opportunity.deadline_at >= now,
            Opportunity.deadline_at <= now + timedelta(days=7),
            Opportunity.status.notin_([
                OpportunityStatus.WON,
                OpportunityStatus.LOST,
                OpportunityStatus.ARCHIVED,
            ])
        )
    ).scalar()
    
    # Win rate (WON / (WON + LOST))
    won_count = status_counts.get(OpportunityStatus.WON, 0)
    lost_count = status_counts.get(OpportunityStatus.LOST, 0)
    total_closed = won_count + lost_count
    win_rate = round((won_count / total_closed * 100), 1) if total_closed > 0 else 0
    
    # Average score of new opportunities
    avg_score = db.query(func.avg(Opportunity.score)).filter(
        Opportunity.status == OpportunityStatus.NEW
    ).scalar() or 0
    
    # Budget stats
    total_budget_won = db.query(func.sum(Opportunity.budget_amount)).filter(
        Opportunity.status == OpportunityStatus.WON,
        Opportunity.budget_amount.isnot(None)
    ).scalar() or 0
    
    total_budget_pipeline = db.query(func.sum(Opportunity.budget_amount)).filter(
        Opportunity.status.in_([
            OpportunityStatus.QUALIFIED,
            OpportunityStatus.IN_PROGRESS,
            OpportunityStatus.SUBMITTED,
        ]),
        Opportunity.budget_amount.isnot(None)
    ).scalar() or 0
    
    result = {
        "totals": {
            "all": sum(status_counts.values()),
            "new": status_counts.get(OpportunityStatus.NEW, 0),
            "review": status_counts.get(OpportunityStatus.REVIEW, 0),
            "qualified": status_counts.get(OpportunityStatus.QUALIFIED, 0),
            "in_progress": status_counts.get(OpportunityStatus.IN_PROGRESS, 0),
            "submitted": status_counts.get(OpportunityStatus.SUBMITTED, 0),
            "won": won_count,
            "lost": lost_count,
        },
        "by_category": {k.value: v for k, v in category_counts.items()},
        "new_24h": new_24h,
        "new_7d": new_7d,
        "deadlines_7d": deadlines_7d,
        "win_rate": win_rate,
        "avg_score_new": round(avg_score, 1),
        "budget_won": float(total_budget_won),
        "budget_pipeline": float(total_budget_pipeline),
    }
    
    # Cache the result
    cache_set(cache_key, result, STATS_CACHE_TTL)
    
    return result


@router.get("/top-opportunities")
def get_top_opportunities(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top scored opportunities with caching"""
    cache_key = f"dashboard:top:{current_user.id}:{db.info.get('workspace_id')}:{limit}"
    
    # Try cache first
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    opportunities = db.query(Opportunity).filter(
        Opportunity.status.in_([
            OpportunityStatus.NEW,
            OpportunityStatus.REVIEW,
            OpportunityStatus.QUALIFIED,
        ])
    ).order_by(Opportunity.score.desc()).limit(limit).all()
    
    result = [
        {
            "id": str(o.id),
            "title": o.title,
            "score": o.score,
            "status": o.status.value,
            "category": o.category.value,
            "deadline_at": o.deadline_at.isoformat() if o.deadline_at else None,
            "organization": o.organization,
            "budget_amount": float(o.budget_amount) if o.budget_amount else None,
        }
        for o in opportunities
    ]
    
    # Cache the result
    cache_set(cache_key, result, TOP_OPPS_CACHE_TTL)
    
    return result


@router.get("/upcoming-deadlines")
def get_upcoming_deadlines(
    days: int = Query(14, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get opportunities with upcoming deadlines"""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    
    opportunities = db.query(Opportunity).filter(
        and_(
            Opportunity.deadline_at >= now,
            Opportunity.deadline_at <= now + timedelta(days=days),
            Opportunity.status.notin_([
                OpportunityStatus.WON,
                OpportunityStatus.LOST,
                OpportunityStatus.ARCHIVED,
            ])
        )
    ).order_by(Opportunity.deadline_at).limit(limit).all()
    
    return [
        {
            "id": str(o.id),
            "title": o.title,
            "score": o.score,
            "status": o.status.value,
            "deadline_at": o.deadline_at.isoformat() if o.deadline_at else None,
            "days_remaining": (o.deadline_at.replace(tzinfo=timezone.utc) - now).days if o.deadline_at else None,
            "organization": o.organization,
        }
        for o in opportunities
    ]


@router.get("/recent-ingestions")
def get_recent_ingestions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent ingestion runs"""
    runs = db.query(IngestionRun).order_by(
        IngestionRun.started_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": str(r.id),
            "source_name": r.source_name,
            "status": r.status.value,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "items_new": r.items_new,
            "items_duplicate": r.items_duplicate,
            "items_error": r.items_error,
        }
        for r in runs
    ]
