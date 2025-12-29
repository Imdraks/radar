"""
API endpoints for artist analysis history and suggestions
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.artist_analysis import ArtistAnalysis
from app.intelligence.known_artists_db import (
    get_emerging_artists,
    get_rising_artists,
    get_budget_friendly_artists,
    get_genre_artists,
    KnownArtistData,
)

router = APIRouter()


class ArtistAnalysisResponse(BaseModel):
    id: int
    artist_name: str
    real_name: Optional[str]
    genre: Optional[str]
    image_url: Optional[str] = None  # Photo de l'artiste
    spotify_monthly_listeners: int
    youtube_subscribers: int
    instagram_followers: int
    tiktok_followers: int
    total_followers: int
    fee_min: float
    fee_max: float
    market_tier: Optional[str]
    popularity_score: float
    record_label: Optional[str]
    management: Optional[str]
    booking_agency: Optional[str]
    booking_email: Optional[str]
    market_trend: str
    confidence_score: float
    sources_scanned: Optional[str]
    created_at: datetime
    
    # AI Intelligence fields
    ai_score: Optional[float] = None
    ai_tier: Optional[str] = None
    growth_trend: Optional[str] = None
    predicted_listeners_30d: Optional[int] = None
    predicted_listeners_90d: Optional[int] = None
    predicted_listeners_180d: Optional[int] = None
    growth_rate_monthly: Optional[float] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    opportunities: Optional[List[str]] = None
    threats: Optional[List[str]] = None
    optimal_fee: Optional[float] = None
    negotiation_power: Optional[str] = None
    best_booking_window: Optional[str] = None
    event_type_fit: Optional[Dict[str, float]] = None
    territory_strength: Optional[Dict[str, float]] = None
    seasonal_demand: Optional[Dict[str, float]] = None
    risk_score: Optional[float] = None
    risk_factors: Optional[List[str]] = None
    opportunity_score: Optional[float] = None
    key_opportunities: Optional[List[str]] = None
    best_platforms: Optional[List[str]] = None
    engagement_rate: Optional[float] = None
    viral_potential: Optional[float] = None
    content_recommendations: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class ArtistAnalysisListResponse(BaseModel):
    items: List[ArtistAnalysisResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ArtistStatistics(BaseModel):
    total_analyses: int
    unique_artists: int
    avg_fee_min: float
    avg_fee_max: float
    total_fee_min: float = 0  # Sum of all unique artist fees
    total_fee_max: float = 0  # Sum of all unique artist fees
    most_searched_artist: Optional[str]
    tier_distribution: dict
    avg_ai_score: Optional[float] = None
    ai_tier_distribution: Optional[Dict[str, int]] = None


@router.get("/", response_model=ArtistAnalysisListResponse)
async def get_artist_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    genre: Optional[str] = None,
    market_tier: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|artist_name|fee_max|popularity_score)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated artist analysis history"""
    query = db.query(ArtistAnalysis)
    
    # Filters
    if search:
        query = query.filter(
            ArtistAnalysis.artist_name.ilike(f"%{search}%") |
            ArtistAnalysis.real_name.ilike(f"%{search}%")
        )
    if genre:
        query = query.filter(ArtistAnalysis.genre.ilike(f"%{genre}%"))
    if market_tier:
        query = query.filter(ArtistAnalysis.market_tier == market_tier)
    
    # Total count
    total = query.count()
    
    # Sorting
    sort_column = getattr(ArtistAnalysis, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Pagination
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    return ArtistAnalysisListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/statistics", response_model=ArtistStatistics)
async def get_artist_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get statistics about artist analyses"""
    total = db.query(ArtistAnalysis).count()
    unique = db.query(func.count(func.distinct(ArtistAnalysis.artist_name))).scalar()
    
    # Calculate average fees based on UNIQUE artists (latest analysis per artist)
    # Subquery to get the latest analysis ID for each artist
    from sqlalchemy import and_
    
    latest_per_artist = db.query(
        ArtistAnalysis.artist_name,
        func.max(ArtistAnalysis.id).label('latest_id')
    ).group_by(ArtistAnalysis.artist_name).subquery()
    
    # Get average fees from only the latest analysis of each unique artist
    avg_fees = db.query(
        func.avg(ArtistAnalysis.fee_min),
        func.avg(ArtistAnalysis.fee_max)
    ).join(
        latest_per_artist,
        and_(
            ArtistAnalysis.artist_name == latest_per_artist.c.artist_name,
            ArtistAnalysis.id == latest_per_artist.c.latest_id
        )
    ).first()
    
    # Also calculate total fees (sum) for display
    total_fees = db.query(
        func.sum(ArtistAnalysis.fee_min),
        func.sum(ArtistAnalysis.fee_max)
    ).join(
        latest_per_artist,
        and_(
            ArtistAnalysis.artist_name == latest_per_artist.c.artist_name,
            ArtistAnalysis.id == latest_per_artist.c.latest_id
        )
    ).first()
    
    # Most searched artist
    most_searched = db.query(
        ArtistAnalysis.artist_name,
        func.count(ArtistAnalysis.id).label('count')
    ).group_by(ArtistAnalysis.artist_name).order_by(desc('count')).first()
    
    # Tier distribution
    tiers = db.query(
        ArtistAnalysis.market_tier,
        func.count(ArtistAnalysis.id)
    ).group_by(ArtistAnalysis.market_tier).all()
    
    tier_distribution = {tier: count for tier, count in tiers if tier}
    
    # AI Statistics
    avg_ai_score = db.query(func.avg(ArtistAnalysis.ai_score)).filter(
        ArtistAnalysis.ai_score.isnot(None)
    ).scalar()
    
    ai_tiers = db.query(
        ArtistAnalysis.ai_tier,
        func.count(ArtistAnalysis.id)
    ).filter(ArtistAnalysis.ai_tier.isnot(None)).group_by(ArtistAnalysis.ai_tier).all()
    
    ai_tier_distribution = {tier: count for tier, count in ai_tiers if tier}
    
    return ArtistStatistics(
        total_analyses=total,
        unique_artists=unique or 0,
        avg_fee_min=float(avg_fees[0] or 0),
        avg_fee_max=float(avg_fees[1] or 0),
        total_fee_min=float(total_fees[0] or 0),
        total_fee_max=float(total_fees[1] or 0),
        most_searched_artist=most_searched[0] if most_searched else None,
        tier_distribution=tier_distribution,
        avg_ai_score=float(avg_ai_score) if avg_ai_score else None,
        ai_tier_distribution=ai_tier_distribution if ai_tier_distribution else None,
    )


# ===== SUGGESTIONS ENDPOINTS (AVANT les routes dynamiques!) =====

class ArtistSuggestion(BaseModel):
    name: str
    real_name: Optional[str]
    genre: str
    spotify_monthly_listeners: int
    youtube_subscribers: int
    instagram_followers: int
    tiktok_followers: int
    fee_min: int
    fee_max: int
    market_tier: str
    record_label: Optional[str]
    potential_reason: str


class SuggestionsResponse(BaseModel):
    emerging: List[ArtistSuggestion]
    rising: List[ArtistSuggestion]
    budget_friendly: List[ArtistSuggestion]


def artist_to_suggestion(artist: KnownArtistData, reason: str) -> ArtistSuggestion:
    """Convert KnownArtistData to ArtistSuggestion"""
    return ArtistSuggestion(
        name=artist.name,
        real_name=artist.real_name,
        genre=artist.genre,
        spotify_monthly_listeners=artist.spotify_monthly_listeners,
        youtube_subscribers=artist.youtube_subscribers,
        instagram_followers=artist.instagram_followers,
        tiktok_followers=artist.tiktok_followers,
        fee_min=artist.fee_min,
        fee_max=artist.fee_max,
        market_tier=artist.market_tier,
        record_label=artist.record_label,
        potential_reason=reason,
    )


@router.get("/suggestions/all", response_model=SuggestionsResponse)
async def get_all_suggestions(
    limit: int = Query(6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """Get all artist suggestions: emerging, rising, and budget-friendly"""
    
    # Artistes émergents avec fort potentiel
    emerging_artists = get_emerging_artists(limit=limit)
    emerging = [
        artist_to_suggestion(
            a, 
            f"Fort potentiel: {a.spotify_monthly_listeners:,} auditeurs pour seulement {a.fee_min:,}€-{a.fee_max:,}€"
        )
        for a in emerging_artists
    ]
    
    # Artistes en progression
    rising_artists = get_rising_artists(limit=limit)
    rising = [
        artist_to_suggestion(
            a,
            f"En forte progression: {a.spotify_monthly_listeners:,} auditeurs Spotify, bientôt établi"
        )
        for a in rising_artists
    ]
    
    # Meilleur rapport qualité/prix
    budget_artists = get_budget_friendly_artists(max_budget=15000, limit=limit)
    budget_friendly = [
        artist_to_suggestion(
            a,
            f"Excellent rapport: {a.spotify_monthly_listeners:,} auditeurs dès {a.fee_min:,}€"
        )
        for a in budget_artists
    ]
    
    return SuggestionsResponse(
        emerging=emerging,
        rising=rising,
        budget_friendly=budget_friendly,
    )


@router.get("/suggestions/emerging", response_model=List[ArtistSuggestion])
async def get_emerging_suggestions(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Get emerging artists with high potential"""
    artists = get_emerging_artists(limit=limit)
    return [
        artist_to_suggestion(
            a,
            f"Fort potentiel: {a.spotify_monthly_listeners:,} auditeurs pour seulement {a.fee_min:,}€-{a.fee_max:,}€"
        )
        for a in artists
    ]


@router.get("/suggestions/rising", response_model=List[ArtistSuggestion])
async def get_rising_suggestions(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Get rising artists close to becoming established"""
    artists = get_rising_artists(limit=limit)
    return [
        artist_to_suggestion(
            a,
            f"En forte progression: {a.spotify_monthly_listeners:,} auditeurs Spotify"
        )
        for a in artists
    ]


@router.get("/suggestions/budget", response_model=List[ArtistSuggestion])
async def get_budget_suggestions(
    max_budget: int = Query(15000, ge=1000),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Get best value artists for a given budget"""
    artists = get_budget_friendly_artists(max_budget=max_budget, limit=limit)
    return [
        artist_to_suggestion(
            a,
            f"Excellent rapport: {a.spotify_monthly_listeners:,} auditeurs dès {a.fee_min:,}€"
        )
        for a in artists
    ]


@router.get("/suggestions/genre/{genre}", response_model=List[ArtistSuggestion])
async def get_genre_suggestions(
    genre: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Get artists by genre"""
    artists = get_genre_artists(genre=genre, limit=limit)
    return [
        artist_to_suggestion(
            a,
            f"Genre {a.genre}: {a.spotify_monthly_listeners:,} auditeurs"
        )
        for a in artists
    ]


# ===== DYNAMIC ROUTES (après les routes statiques) =====

@router.get("/{analysis_id}", response_model=ArtistAnalysisResponse)
async def get_artist_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific artist analysis by ID"""
    analysis = db.query(ArtistAnalysis).filter(ArtistAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/{analysis_id}/full")
async def get_artist_analysis_full(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full JSON data for an artist analysis"""
    analysis = db.query(ArtistAnalysis).filter(ArtistAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis.full_data


@router.delete("/{analysis_id}")
async def delete_artist_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an artist analysis"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    analysis = db.query(ArtistAnalysis).filter(ArtistAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    
    return {"message": "Analysis deleted", "id": analysis_id}


@router.delete("/")
async def clear_artist_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all artist analysis history (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    count = db.query(ArtistAnalysis).count()
    db.query(ArtistAnalysis).delete()
    db.commit()
    
    return {"message": f"Deleted {count} analyses"}
