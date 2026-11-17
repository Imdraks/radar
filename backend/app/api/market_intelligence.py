"""
Market Intelligence API — Unified feed for market trends, alerts, and fee estimates.
Aggregates data from discovery artists, events, and scoring to produce actionable insights.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, and_, case, desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.user import User
from app.api.deps import get_current_user, get_user_workspace_id
from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market-intelligence", tags=["market-intelligence"])


@router.get("/feed")
def get_intelligence_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
) -> Dict[str, Any]:
    """Unified market intelligence feed — combines trending artists, market alerts,
    fee estimates, event insights, and price trends into a single feed."""

    cache_key = f"market-intel:feed:{workspace_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        from app.db.models.discovery import DiscoveryArtist, DiscoveryComputedMetrics
    except ImportError:
        return {"feed": [], "kpis": {}, "trends": {}}

    now = datetime.utcnow()

    # ── 1. KPIs ──
    total_artists = db.query(func.count(DiscoveryArtist.id)).filter(
        DiscoveryArtist.workspace_id == workspace_id,
        DiscoveryArtist.is_deleted == False,
    ).scalar() or 0

    scored_q = (
        db.query(DiscoveryComputedMetrics)
        .join(DiscoveryArtist, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(DiscoveryArtist.workspace_id == workspace_id, DiscoveryArtist.is_deleted == False)
    )

    avg_score = db.query(func.avg(DiscoveryComputedMetrics.score)).join(
        DiscoveryArtist, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id
    ).filter(
        DiscoveryArtist.workspace_id == workspace_id, DiscoveryArtist.is_deleted == False,
    ).scalar() or 0

    high_score = scored_q.filter(DiscoveryComputedMetrics.score >= 75).count()
    rising_count = scored_q.filter(DiscoveryComputedMetrics.velocity > 0).count()

    # Fee ranges
    fee_data = (
        db.query(
            func.avg(DiscoveryComputedMetrics.fee_estimate_min).label("avg_fee_min"),
            func.avg(DiscoveryComputedMetrics.fee_estimate_max).label("avg_fee_max"),
            func.min(DiscoveryComputedMetrics.fee_estimate_min).label("min_fee"),
            func.max(DiscoveryComputedMetrics.fee_estimate_max).label("max_fee"),
        )
        .join(DiscoveryArtist, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.is_deleted == False,
            DiscoveryComputedMetrics.fee_estimate_min.isnot(None),
            DiscoveryComputedMetrics.fee_estimate_min > 0,
        )
        .first()
    )

    # Events count
    events_total = 0
    events_upcoming = 0
    try:
        from app.db.models.artist_event import ArtistEvent
        events_total = db.query(func.count(ArtistEvent.id)).filter(
            ArtistEvent.workspace_id == workspace_id, ArtistEvent.is_deleted == False,
        ).scalar() or 0
        events_upcoming = db.query(func.count(ArtistEvent.id)).filter(
            ArtistEvent.workspace_id == workspace_id, ArtistEvent.is_deleted == False,
            ArtistEvent.event_date >= now,
        ).scalar() or 0
    except Exception as exc:
        db.rollback()
        logger.exception("Market intelligence data unavailable")
        raise HTTPException(503, "Market intelligence data unavailable") from exc

    kpis = {
        "total_artists": total_artists,
        "avg_score": round(float(avg_score), 1),
        "high_score_count": high_score,
        "rising_count": rising_count,
        "avg_fee_min": int(fee_data.avg_fee_min or 0) if fee_data else 0,
        "avg_fee_max": int(fee_data.avg_fee_max or 0) if fee_data else 0,
        "fee_range_min": int(fee_data.min_fee or 0) if fee_data else 0,
        "fee_range_max": int(fee_data.max_fee or 0) if fee_data else 0,
        "events_total": events_total,
        "events_upcoming": events_upcoming,
    }

    # ── 2. Build feed items ──
    feed: List[Dict[str, Any]] = []

    # --- Trending artists (velocity > 0, sorted by velocity desc) ---
    trending = (
        db.query(
            DiscoveryArtist.id,
            DiscoveryArtist.canonical_name,
            DiscoveryArtist.image_url,
            DiscoveryArtist.genres,
            DiscoveryComputedMetrics.score,
            DiscoveryComputedMetrics.velocity,
            DiscoveryComputedMetrics.acceleration,
            DiscoveryComputedMetrics.monthly_listeners,
            DiscoveryComputedMetrics.fee_estimate_min,
            DiscoveryComputedMetrics.fee_estimate_max,
            DiscoveryComputedMetrics.recommendation,
            DiscoveryComputedMetrics.timing_bucket,
            DiscoveryComputedMetrics.drivers,
            DiscoveryComputedMetrics.signals,
            DiscoveryComputedMetrics.confidence_index,
            DiscoveryComputedMetrics.spotify_followers,
            DiscoveryComputedMetrics.instagram_followers,
            DiscoveryComputedMetrics.tiktok_followers,
            DiscoveryComputedMetrics.total_social_followers,
        )
        .join(DiscoveryComputedMetrics, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.is_deleted == False,
            DiscoveryComputedMetrics.velocity.isnot(None),
            DiscoveryComputedMetrics.velocity > 0,
        )
        .order_by(desc(DiscoveryComputedMetrics.velocity))
        .limit(10)
        .all()
    )

    for a in trending:
        feed.append({
            "type": "trending_artist",
            "priority": "high" if (a.velocity or 0) > 5 else "medium",
            "artist_id": str(a.id),
            "artist_name": a.canonical_name,
            "artist_image": a.image_url,
            "genres": (a.genres or [])[:3],
            "score": a.score or 0,
            "velocity": round(a.velocity or 0, 2),
            "acceleration": round(a.acceleration or 0, 2),
            "monthly_listeners": a.monthly_listeners or 0,
            "fee_min": a.fee_estimate_min or 0,
            "fee_max": a.fee_estimate_max or 0,
            "recommendation": a.recommendation or "WATCHLIST",
            "timing": a.timing_bucket or "UNKNOWN",
            "confidence": a.confidence_index or 0,
            "drivers": (a.drivers or [])[:3],
            "signals": (a.signals or [])[:3],
            "social": {
                "spotify": a.spotify_followers or 0,
                "instagram": a.instagram_followers or 0,
                "tiktok": a.tiktok_followers or 0,
                "total": a.total_social_followers or 0,
            },
            "message": f"{a.canonical_name} — croissance de +{round(a.velocity or 0, 1)}% sur la période",
        })

    # --- Fee estimation alerts (artists with high score but low fee = good deal) ---
    good_deals = (
        db.query(
            DiscoveryArtist.id,
            DiscoveryArtist.canonical_name,
            DiscoveryArtist.image_url,
            DiscoveryArtist.genres,
            DiscoveryComputedMetrics.score,
            DiscoveryComputedMetrics.monthly_listeners,
            DiscoveryComputedMetrics.fee_estimate_min,
            DiscoveryComputedMetrics.fee_estimate_max,
            DiscoveryComputedMetrics.velocity,
            DiscoveryComputedMetrics.recommendation,
        )
        .join(DiscoveryComputedMetrics, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.is_deleted == False,
            DiscoveryComputedMetrics.score >= 60,
            DiscoveryComputedMetrics.fee_estimate_max.isnot(None),
            DiscoveryComputedMetrics.fee_estimate_max > 0,
            DiscoveryComputedMetrics.fee_estimate_max <= 15000,  # Under 15k = good deal for score >= 60
        )
        .order_by(desc(DiscoveryComputedMetrics.score))
        .limit(8)
        .all()
    )

    for a in good_deals:
        feed.append({
            "type": "fee_opportunity",
            "priority": "high" if (a.score or 0) >= 75 else "medium",
            "artist_id": str(a.id),
            "artist_name": a.canonical_name,
            "artist_image": a.image_url,
            "genres": (a.genres or [])[:3],
            "score": a.score or 0,
            "monthly_listeners": a.monthly_listeners or 0,
            "fee_min": a.fee_estimate_min or 0,
            "fee_max": a.fee_estimate_max or 0,
            "velocity": round(a.velocity or 0, 2),
            "recommendation": a.recommendation or "WATCHLIST",
            "message": f"{a.canonical_name} — score {a.score}, cachet estimé {a.fee_estimate_min or '?'}–{a.fee_estimate_max or '?'}€",
        })

    # --- High-potential alerts (score > 80, recommendation BOOK) ---
    book_now = (
        db.query(
            DiscoveryArtist.id,
            DiscoveryArtist.canonical_name,
            DiscoveryArtist.image_url,
            DiscoveryArtist.genres,
            DiscoveryComputedMetrics.score,
            DiscoveryComputedMetrics.monthly_listeners,
            DiscoveryComputedMetrics.fee_estimate_min,
            DiscoveryComputedMetrics.fee_estimate_max,
            DiscoveryComputedMetrics.velocity,
            DiscoveryComputedMetrics.timing_bucket,
            DiscoveryComputedMetrics.recommendation,
        )
        .join(DiscoveryComputedMetrics, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.is_deleted == False,
            DiscoveryComputedMetrics.recommendation == "BOOK",
        )
        .order_by(desc(DiscoveryComputedMetrics.score))
        .limit(5)
        .all()
    )

    for a in book_now:
        feed.append({
            "type": "book_alert",
            "priority": "critical",
            "artist_id": str(a.id),
            "artist_name": a.canonical_name,
            "artist_image": a.image_url,
            "genres": (a.genres or [])[:3],
            "score": a.score or 0,
            "monthly_listeners": a.monthly_listeners or 0,
            "fee_min": a.fee_estimate_min or 0,
            "fee_max": a.fee_estimate_max or 0,
            "velocity": round(a.velocity or 0, 2),
            "timing": a.timing_bucket or "UNKNOWN",
            "recommendation": "BOOK",
            "message": f"{a.canonical_name} — score {a.score}, recommandation BOOK",
        })

    # --- Upcoming events with price info ---
    try:
        from app.db.models.artist_event import ArtistEvent
        upcoming = (
            db.query(ArtistEvent)
            .filter(
                ArtistEvent.workspace_id == workspace_id,
                ArtistEvent.is_deleted == False,
                ArtistEvent.event_date >= now,
                ArtistEvent.event_date <= now + timedelta(days=60),
            )
            .order_by(ArtistEvent.event_date.asc())
            .limit(10)
            .all()
        )

        for ev in upcoming:
            feed.append({
                "type": "upcoming_event",
                "priority": "low",
                "artist_name": ev.artist_name,
                "artist_image": ev.artist_image,
                "event_name": ev.event_name,
                "event_type": ev.event_type,
                "venue": ev.venue,
                "city": ev.city,
                "date": ev.event_date.isoformat() if ev.event_date else None,
                "date_label": ev.event_date.strftime("%d %b %Y") if ev.event_date else "",
                "price_min": ev.price_min,
                "price_max": ev.price_max,
                "event_url": ev.event_url,
                "promoter": ev.promoter,
                "source": ev.source,
                "message": f"{ev.artist_name} — {ev.event_name}, {ev.event_date.strftime('%d/%m') if ev.event_date else '?'} à {ev.city or '?'}",
            })
    except Exception as exc:
        db.rollback()
        logger.exception("Market intelligence data unavailable")
        raise HTTPException(503, "Market intelligence data unavailable") from exc

    # --- Market saturation by city (top cities with most events) ---
    try:
        from app.db.models.artist_event import ArtistEvent
        city_stats = (
            db.query(
                ArtistEvent.city,
                func.count(ArtistEvent.id).label("event_count"),
                func.avg(ArtistEvent.price_min).label("avg_price_min"),
                func.avg(ArtistEvent.price_max).label("avg_price_max"),
            )
            .filter(
                ArtistEvent.workspace_id == workspace_id,
                ArtistEvent.is_deleted == False,
                ArtistEvent.event_date >= now,
                ArtistEvent.city.isnot(None),
            )
            .group_by(ArtistEvent.city)
            .order_by(desc("event_count"))
            .limit(8)
            .all()
        )

        for c in city_stats:
            if c.event_count >= 3:
                feed.append({
                    "type": "market_saturation",
                    "priority": "info",
                    "city": c.city,
                    "event_count": c.event_count,
                    "avg_price_min": round(float(c.avg_price_min or 0)),
                    "avg_price_max": round(float(c.avg_price_max or 0)),
                    "message": f"{c.city} — {c.event_count} événements à venir, prix moyen {round(float(c.avg_price_min or 0))}–{round(float(c.avg_price_max or 0))}€",
                })
    except Exception as exc:
        db.rollback()
        logger.exception("Market intelligence data unavailable")
        raise HTTPException(503, "Market intelligence data unavailable") from exc

    # ── 3. Sort feed by priority ──
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    feed.sort(key=lambda x: (priority_order.get(x.get("priority", "info"), 5)))

    # ── 4. Trends (genre distribution, score distribution, fee tiers) ──
    genre_counts: Dict[str, int] = {}
    score_buckets = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    fee_tiers = {"< 5k": 0, "5-15k": 0, "15-40k": 0, "40-100k": 0, "> 100k": 0}

    all_artists = (
        db.query(
            DiscoveryArtist.genres,
            DiscoveryComputedMetrics.score,
            DiscoveryComputedMetrics.fee_estimate_max,
        )
        .join(DiscoveryComputedMetrics, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(DiscoveryArtist.workspace_id == workspace_id, DiscoveryArtist.is_deleted == False)
        .all()
    )

    for row in all_artists:
        # Genres
        for g in (row.genres or [])[:3]:
            genre_counts[g] = genre_counts.get(g, 0) + 1

        # Score buckets
        s = row.score or 0
        if s < 25:
            score_buckets["0-25"] += 1
        elif s < 50:
            score_buckets["25-50"] += 1
        elif s < 75:
            score_buckets["50-75"] += 1
        else:
            score_buckets["75-100"] += 1

        # Fee tiers
        f = row.fee_estimate_max or 0
        if f <= 0:
            pass
        elif f < 5000:
            fee_tiers["< 5k"] += 1
        elif f < 15000:
            fee_tiers["5-15k"] += 1
        elif f < 40000:
            fee_tiers["15-40k"] += 1
        elif f < 100000:
            fee_tiers["40-100k"] += 1
        else:
            fee_tiers["> 100k"] += 1

    # Top genres sorted
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:12]

    trends = {
        "genres": [{"name": g, "count": c} for g, c in top_genres],
        "score_distribution": score_buckets,
        "fee_tiers": fee_tiers,
    }

    result = {
        "feed": feed,
        "kpis": kpis,
        "trends": trends,
        "generated_at": now.isoformat(),
    }

    cache_set(cache_key, result, 180)
    return result


@router.get("/fee-estimate/{artist_id}")
def get_fee_estimate(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
) -> Dict[str, Any]:
    """Detailed fee estimate for a specific artist with market comparison."""

    try:
        from app.db.models.discovery import DiscoveryArtist, DiscoveryComputedMetrics
    except ImportError:
        return {"error": "Discovery module not available"}

    artist = (
        db.query(
            DiscoveryArtist.id,
            DiscoveryArtist.canonical_name,
            DiscoveryArtist.image_url,
            DiscoveryArtist.genres,
            DiscoveryComputedMetrics.score,
            DiscoveryComputedMetrics.fee_estimate_min,
            DiscoveryComputedMetrics.fee_estimate_max,
            DiscoveryComputedMetrics.monthly_listeners,
            DiscoveryComputedMetrics.spotify_followers,
            DiscoveryComputedMetrics.instagram_followers,
            DiscoveryComputedMetrics.tiktok_followers,
            DiscoveryComputedMetrics.velocity,
            DiscoveryComputedMetrics.confidence_index,
            DiscoveryComputedMetrics.recommendation,
        )
        .join(DiscoveryComputedMetrics, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(DiscoveryArtist.id == artist_id, DiscoveryArtist.workspace_id == workspace_id)
        .first()
    )

    if not artist:
        return {"error": "Artist not found"}

    fee_min = artist.fee_estimate_min or 0
    fee_max = artist.fee_estimate_max or 0
    score = artist.score or 0

    # Market comparison — average fee for artists in same score range
    score_range_low = max(0, score - 15)
    score_range_high = min(100, score + 15)

    peers = (
        db.query(
            func.avg(DiscoveryComputedMetrics.fee_estimate_min).label("avg_min"),
            func.avg(DiscoveryComputedMetrics.fee_estimate_max).label("avg_max"),
            func.count(DiscoveryComputedMetrics.id).label("peer_count"),
        )
        .join(DiscoveryArtist, DiscoveryArtist.id == DiscoveryComputedMetrics.artist_id)
        .filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.is_deleted == False,
            DiscoveryComputedMetrics.score.between(score_range_low, score_range_high),
            DiscoveryComputedMetrics.fee_estimate_min > 0,
        )
        .first()
    )

    # Determine if this artist is under/over-priced
    market_avg_max = float(peers.avg_max or 0) if peers else 0
    valuation = "fair"
    if fee_max > 0 and market_avg_max > 0:
        ratio = fee_max / market_avg_max
        if ratio < 0.7:
            valuation = "undervalued"
        elif ratio > 1.3:
            valuation = "premium"

    # Event price context
    event_prices = []
    try:
        from app.db.models.artist_event import ArtistEvent
        events = (
            db.query(ArtistEvent.event_name, ArtistEvent.price_min, ArtistEvent.price_max, ArtistEvent.city)
            .filter(
                ArtistEvent.workspace_id == workspace_id,
                ArtistEvent.artist_name.ilike(f"%{artist.canonical_name}%"),
                ArtistEvent.is_deleted == False,
            )
            .limit(5)
            .all()
        )
        event_prices = [
            {"event": e.event_name, "price_min": e.price_min, "price_max": e.price_max, "city": e.city}
            for e in events
        ]
    except Exception as exc:
        db.rollback()
        logger.exception("Market intelligence data unavailable")
        raise HTTPException(503, "Market intelligence data unavailable") from exc

    return {
        "artist_id": str(artist.id),
        "artist_name": artist.canonical_name,
        "artist_image": artist.image_url,
        "genres": artist.genres or [],
        "score": score,
        "fee_min": fee_min,
        "fee_max": fee_max,
        "confidence": artist.confidence_index or 0,
        "velocity": round(artist.velocity or 0, 2),
        "recommendation": artist.recommendation or "WATCHLIST",
        "market_comparison": {
            "peer_avg_min": int(peers.avg_min or 0) if peers else 0,
            "peer_avg_max": int(peers.avg_max or 0) if peers else 0,
            "peer_count": peers.peer_count if peers else 0,
            "valuation": valuation,
        },
        "social": {
            "monthly_listeners": artist.monthly_listeners or 0,
            "spotify_followers": artist.spotify_followers or 0,
            "instagram_followers": artist.instagram_followers or 0,
            "tiktok_followers": artist.tiktok_followers or 0,
        },
        "event_prices": event_prices,
    }
