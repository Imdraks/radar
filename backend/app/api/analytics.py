"""
Advanced Analytics Dashboard API
Graphiques, tendances, KPIs avancés
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, APIRouter, Depends, Query
from sqlalchemy import func, and_, case, extract
from sqlalchemy.orm import Session
from collections import defaultdict

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import Opportunity, OpportunityStatus, OpportunityCategory
from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set

def suspend_predictions():
    raise HTTPException(status_code=503, detail="Prédictions commerciales suspendues : méthode non validée")


router = APIRouter(prefix="/analytics", tags=["analytics"])

CACHE_TTL = 300  # 5 minutes


# ============================================================================
# ÉVOLUTION TEMPORELLE
# ============================================================================

@router.get("/timeline")
def get_timeline_data(
    period: str = Query("30d", regex="^(7d|30d|90d|12m)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Évolution des opportunités dans le temps
    - Nouvelles opportunités par jour/semaine
    - Tendance globale
    """
    cache_key = f"analytics:timeline:{current_user.id}:{db.info.get('workspace_id')}:{period}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    
    # Parse period
    if period == "7d":
        start_date = now - timedelta(days=7)
        group_by = "day"
    elif period == "30d":
        start_date = now - timedelta(days=30)
        group_by = "day"
    elif period == "90d":
        start_date = now - timedelta(days=90)
        group_by = "week"
    else:  # 12m
        start_date = now - timedelta(days=365)
        group_by = "month"
    
    # Query opportunities
    opps = db.query(Opportunity).filter(
        Opportunity.created_at >= start_date
    ).all()
    
    # Group by period
    timeline = defaultdict(lambda: {"new": 0, "won": 0, "lost": 0, "total_value": 0})
    
    for opp in opps:
        if group_by == "day":
            key = opp.created_at.strftime("%Y-%m-%d")
        elif group_by == "week":
            key = opp.created_at.strftime("%Y-W%W")
        else:
            key = opp.created_at.strftime("%Y-%m")
        
        timeline[key]["new"] += 1
        if opp.budget_amount:
            timeline[key]["total_value"] += float(opp.budget_amount)
        
        if opp.status == OpportunityStatus.WON:
            timeline[key]["won"] += 1
        elif opp.status == OpportunityStatus.LOST:
            timeline[key]["lost"] += 1
    
    # Convert to sorted list
    data = [
        {"date": k, **v}
        for k, v in sorted(timeline.items())
    ]
    
    # Calculate trend (compare last half to first half)
    if len(data) >= 2:
        mid = len(data) // 2
        first_half = sum(d["new"] for d in data[:mid])
        second_half = sum(d["new"] for d in data[mid:])
        if first_half > 0:
            trend = round(((second_half - first_half) / first_half) * 100, 1)
        else:
            trend = 100 if second_half > 0 else 0
    else:
        trend = 0
    
    result = {
        "period": period,
        "data": data,
        "trend": trend,
        "trend_label": "↑" if trend > 0 else "↓" if trend < 0 else "→"
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# TAUX DE CONVERSION
# ============================================================================

@router.get("/conversion")
def get_conversion_metrics(
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Métriques de conversion
    - Taux de conversion global
    - Par catégorie
    - Par source
    """
    cache_key = f"analytics:conversion:{current_user.id}:{db.info.get('workspace_id')}:{period}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    
    # Date filter
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = None
    
    query = db.query(Opportunity)
    if start_date:
        query = query.filter(Opportunity.created_at >= start_date)
    
    opps = query.all()
    
    # Global conversion
    total = len(opps)
    won = len([o for o in opps if o.status == OpportunityStatus.WON])
    lost = len([o for o in opps if o.status == OpportunityStatus.LOST])
    pending = len([o for o in opps if o.status in [
        OpportunityStatus.NEW, 
        OpportunityStatus.CONTACTED,
        OpportunityStatus.IN_PROGRESS
    ]])
    
    global_rate = round((won / (won + lost) * 100), 1) if (won + lost) > 0 else 0
    
    # By category
    by_category = defaultdict(lambda: {"total": 0, "won": 0, "lost": 0})
    for opp in opps:
        cat = opp.category.value if opp.category else "unknown"
        by_category[cat]["total"] += 1
        if opp.status == OpportunityStatus.WON:
            by_category[cat]["won"] += 1
        elif opp.status == OpportunityStatus.LOST:
            by_category[cat]["lost"] += 1
    
    category_rates = []
    for cat, data in by_category.items():
        decided = data["won"] + data["lost"]
        rate = round((data["won"] / decided * 100), 1) if decided > 0 else None
        category_rates.append({
            "category": cat,
            "total": data["total"],
            "won": data["won"],
            "lost": data["lost"],
            "rate": rate
        })
    category_rates.sort(key=lambda x: x["rate"] or 0, reverse=True)
    
    # By source
    by_source = defaultdict(lambda: {"total": 0, "won": 0, "lost": 0})
    for opp in opps:
        source = opp.source_name or "unknown"
        by_source[source]["total"] += 1
        if opp.status == OpportunityStatus.WON:
            by_source[source]["won"] += 1
        elif opp.status == OpportunityStatus.LOST:
            by_source[source]["lost"] += 1
    
    source_rates = []
    for source, data in by_source.items():
        decided = data["won"] + data["lost"]
        rate = round((data["won"] / decided * 100), 1) if decided > 0 else None
        source_rates.append({
            "source": source,
            "total": data["total"],
            "won": data["won"],
            "lost": data["lost"],
            "rate": rate
        })
    source_rates.sort(key=lambda x: x["rate"] or 0, reverse=True)
    
    result = {
        "period": period,
        "global": {
            "total": total,
            "won": won,
            "lost": lost,
            "pending": pending,
            "conversion_rate": global_rate
        },
        "by_category": category_rates[:10],
        "by_source": source_rates[:10]
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# HEATMAP DEADLINES
# ============================================================================

@router.get("/deadline-heatmap")
def get_deadline_heatmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Heatmap des deadlines par mois
    - Nombre d'opportunités par mois
    - Valeur totale par mois
    """
    cache_key = f"analytics:heatmap:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    # Get opportunities with deadlines in the next 12 months
    now = datetime.utcnow()
    end_date = now + timedelta(days=365)
    
    opps = db.query(Opportunity).filter(
        and_(
            Opportunity.deadline_at.isnot(None),
            Opportunity.deadline_at >= now,
            Opportunity.deadline_at <= end_date,
            Opportunity.status.notin_([OpportunityStatus.WON, OpportunityStatus.LOST, OpportunityStatus.CANCELLED])
        )
    ).all()
    
    # Group by month
    heatmap = defaultdict(lambda: {"count": 0, "value": 0, "high_priority": 0})
    
    for opp in opps:
        month_key = opp.deadline_at.strftime("%Y-%m")
        heatmap[month_key]["count"] += 1
        if opp.budget_amount:
            heatmap[month_key]["value"] += float(opp.budget_amount)
        if opp.score and opp.score >= 70:
            heatmap[month_key]["high_priority"] += 1
    
    # Convert to list with month names
    months_fr = {
        "01": "Jan", "02": "Fév", "03": "Mar", "04": "Avr",
        "05": "Mai", "06": "Juin", "07": "Juil", "08": "Août",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Déc"
    }
    
    data = []
    for key in sorted(heatmap.keys()):
        year, month = key.split("-")
        data.append({
            "month": key,
            "label": f"{months_fr[month]} {year}",
            "count": heatmap[key]["count"],
            "value": round(heatmap[key]["value"], 2),
            "high_priority": heatmap[key]["high_priority"]
        })
    
    # Find hottest month
    hottest = max(data, key=lambda x: x["count"]) if data else None
    
    result = {
        "data": data,
        "hottest_month": hottest,
        "total_upcoming": sum(d["count"] for d in data),
        "total_value": sum(d["value"] for d in data)
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# COMPARAISON PÉRIODE
# ============================================================================

@router.get("/comparison")
def get_period_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Comparaison ce mois vs mois précédent
    - Nouvelles opportunités
    - Valeur totale
    - Taux de conversion
    """
    cache_key = f"analytics:comparison:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    
    # Current month
    current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Previous month
    prev_end = current_start - timedelta(seconds=1)
    prev_start = prev_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Query both periods
    current_opps = db.query(Opportunity).filter(
        Opportunity.created_at >= current_start
    ).all()
    
    prev_opps = db.query(Opportunity).filter(
        and_(
            Opportunity.created_at >= prev_start,
            Opportunity.created_at < current_start
        )
    ).all()
    
    def calc_metrics(opps):
        total = len(opps)
        won = len([o for o in opps if o.status == OpportunityStatus.WON])
        lost = len([o for o in opps if o.status == OpportunityStatus.LOST])
        value = sum(float(o.budget_amount) for o in opps if o.budget_amount)
        rate = round((won / (won + lost) * 100), 1) if (won + lost) > 0 else 0
        return {
            "count": total,
            "won": won,
            "lost": lost,
            "value": round(value, 2),
            "conversion_rate": rate
        }
    
    current = calc_metrics(current_opps)
    previous = calc_metrics(prev_opps)
    
    def calc_change(curr, prev):
        if prev == 0:
            return 100 if curr > 0 else 0
        return round(((curr - prev) / prev) * 100, 1)
    
    result = {
        "current_period": {
            "label": current_start.strftime("%B %Y"),
            **current
        },
        "previous_period": {
            "label": prev_start.strftime("%B %Y"),
            **previous
        },
        "changes": {
            "count": calc_change(current["count"], previous["count"]),
            "value": calc_change(current["value"], previous["value"]),
            "conversion_rate": round(current["conversion_rate"] - previous["conversion_rate"], 1)
        }
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# KPIs EN TEMPS RÉEL
# ============================================================================

@router.get("/kpis")
def get_realtime_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    KPIs principaux avec tendances
    """
    cache_key = f"analytics:kpis:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Today's new
    today_new = db.query(Opportunity).filter(
        Opportunity.created_at >= today_start
    ).count()
    
    # This week's new
    week_new = db.query(Opportunity).filter(
        Opportunity.created_at >= week_start
    ).count()
    
    # This month's value
    month_opps = db.query(Opportunity).filter(
        Opportunity.created_at >= month_start
    ).all()
    month_value = sum(float(o.budget_amount) for o in month_opps if o.budget_amount)
    
    # Pending high score
    high_score_pending = db.query(Opportunity).filter(
        and_(
            Opportunity.score >= 70,
            Opportunity.status.in_([
                OpportunityStatus.NEW,
                OpportunityStatus.CONTACTED,
                OpportunityStatus.IN_PROGRESS
            ])
        )
    ).count()
    
    # Urgent deadlines (next 7 days)
    urgent_deadline = db.query(Opportunity).filter(
        and_(
            Opportunity.deadline_at.isnot(None),
            Opportunity.deadline_at >= now,
            Opportunity.deadline_at <= now + timedelta(days=7),
            Opportunity.status.notin_([OpportunityStatus.WON, OpportunityStatus.LOST, OpportunityStatus.CANCELLED])
        )
    ).count()
    
    # Average score
    avg_score = db.query(func.avg(Opportunity.score)).filter(
        Opportunity.score.isnot(None)
    ).scalar() or 0
    
    # Compare with last week for trends
    last_week_start = week_start - timedelta(days=7)
    last_week_new = db.query(Opportunity).filter(
        and_(
            Opportunity.created_at >= last_week_start,
            Opportunity.created_at < week_start
        )
    ).count()
    
    week_trend = "↑" if week_new > last_week_new else "↓" if week_new < last_week_new else "→"
    
    result = {
        "today_new": today_new,
        "week_new": week_new,
        "week_trend": week_trend,
        "month_value": round(month_value, 2),
        "high_score_pending": high_score_pending,
        "urgent_deadlines": urgent_deadline,
        "avg_score": round(float(avg_score), 1),
        "updated_at": now.isoformat()
    }
    
    cache_set(cache_key, result, 60)  # 1 minute cache for real-time
    return result


# ============================================================================
# TOP PERFORMERS
# ============================================================================

@router.get("/top-performers")
def get_top_performers(
    period: str = Query("30d", regex="^(30d|90d|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Top sources, catégories et régions performantes
    """
    cache_key = f"analytics:top:{current_user.id}:{db.info.get('workspace_id')}:{period}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    
    if period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = None
    
    query = db.query(Opportunity).filter(
        Opportunity.status == OpportunityStatus.WON
    )
    if start_date:
        query = query.filter(Opportunity.created_at >= start_date)
    
    won_opps = query.all()
    
    # Top sources
    sources = defaultdict(lambda: {"count": 0, "value": 0})
    for opp in won_opps:
        source = opp.source_name or "unknown"
        sources[source]["count"] += 1
        if opp.budget_amount:
            sources[source]["value"] += float(opp.budget_amount)
    
    top_sources = sorted(
        [{"name": k, **v} for k, v in sources.items()],
        key=lambda x: x["value"],
        reverse=True
    )[:5]
    
    # Top categories
    categories = defaultdict(lambda: {"count": 0, "value": 0})
    for opp in won_opps:
        cat = opp.category.value if opp.category else "other"
        categories[cat]["count"] += 1
        if opp.budget_amount:
            categories[cat]["value"] += float(opp.budget_amount)
    
    top_categories = sorted(
        [{"name": k, **v} for k, v in categories.items()],
        key=lambda x: x["value"],
        reverse=True
    )[:5]
    
    # Top regions
    regions = defaultdict(lambda: {"count": 0, "value": 0})
    for opp in won_opps:
        region = opp.location_region or "unknown"
        regions[region]["count"] += 1
        if opp.budget_amount:
            regions[region]["value"] += float(opp.budget_amount)
    
    top_regions = sorted(
        [{"name": k, **v} for k, v in regions.items()],
        key=lambda x: x["value"],
        reverse=True
    )[:5]
    
    result = {
        "period": period,
        "total_won": len(won_opps),
        "total_value": round(sum(float(o.budget_amount) for o in won_opps if o.budget_amount), 2),
        "top_sources": top_sources,
        "top_categories": top_categories,
        "top_regions": top_regions
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# SIGNAUX FAIBLES & ALERTES
# ============================================================================

@router.get("/signals")
def get_weak_signals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Détection de signaux faibles :
    - Opportunités stagnantes (pas de mise à jour depuis 14+ jours)
    - Deadlines imminentes sans action
    - Chutes de score
    - Opportunités à fort budget non traitées
    - Tendances négatives
    """
    cache_key = f"analytics:signals:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    now = datetime.utcnow()
    signals = []

    active_statuses = [
        OpportunityStatus.NEW,
        OpportunityStatus.CONTACTED,
        OpportunityStatus.IN_PROGRESS,
    ]

    active_opps = db.query(Opportunity).filter(
        Opportunity.status.in_(active_statuses)
    ).all()

    # 1. Opportunités stagnantes (14+ jours sans update)
    stale_threshold = now - timedelta(days=14)
    stale_opps = [
        o for o in active_opps
        if o.updated_at and o.updated_at < stale_threshold
    ]
    for opp in stale_opps[:5]:
        days_stale = (now - opp.updated_at).days
        signals.append({
            "type": "stale",
            "priority": "high" if days_stale > 21 else "medium",
            "icon": "⏳",
            "title": f"Stagnante depuis {days_stale}j",
            "description": opp.title[:80],
            "opportunity_id": opp.id,
            "metadata": {"days_stale": days_stale, "status": opp.status.value},
        })

    # 2. Deadlines imminentes sans action (J-3 et encore NEW)
    deadline_soon = now + timedelta(days=3)
    urgent_no_action = [
        o for o in active_opps
        if o.deadline_at
        and o.deadline_at <= deadline_soon
        and o.deadline_at >= now
        and o.status == OpportunityStatus.NEW
    ]
    for opp in urgent_no_action[:5]:
        days_left = max(0, (opp.deadline_at - now).days)
        signals.append({
            "type": "deadline_risk",
            "priority": "critical" if days_left <= 1 else "high",
            "icon": "🚨",
            "title": f"Deadline J-{days_left} sans action",
            "description": opp.title[:80],
            "opportunity_id": opp.id,
            "metadata": {"days_left": days_left, "deadline": opp.deadline_at.isoformat()},
        })

    # 3. Opportunités à fort budget non traitées (score >= 60, budget > 10k, status NEW)
    high_value_untouched = [
        o for o in active_opps
        if o.status == OpportunityStatus.NEW
        and o.budget_amount
        and float(o.budget_amount) >= 10000
        and o.score
        and o.score >= 60
    ]
    for opp in sorted(high_value_untouched, key=lambda o: float(o.budget_amount or 0), reverse=True)[:5]:
        signals.append({
            "type": "high_value_untouched",
            "priority": "high",
            "icon": "💰",
            "title": f"Fort potentiel non traité ({int(opp.budget_amount)}€)",
            "description": opp.title[:80],
            "opportunity_id": opp.id,
            "metadata": {"budget": float(opp.budget_amount), "score": opp.score},
        })

    # 4. Volume en baisse (comparer les 7 derniers jours vs les 7 d'avant)
    recent_7d = db.query(Opportunity).filter(
        Opportunity.created_at >= now - timedelta(days=7)
    ).count()
    prev_7d = db.query(Opportunity).filter(
        and_(
            Opportunity.created_at >= now - timedelta(days=14),
            Opportunity.created_at < now - timedelta(days=7),
        )
    ).count()
    if prev_7d > 0 and recent_7d < prev_7d * 0.5:
        drop_pct = round((1 - recent_7d / prev_7d) * 100)
        signals.append({
            "type": "volume_drop",
            "priority": "medium",
            "icon": "📉",
            "title": f"Volume en baisse de {drop_pct}%",
            "description": f"{recent_7d} nouvelles vs {prev_7d} la semaine précédente",
            "opportunity_id": None,
            "metadata": {"recent": recent_7d, "previous": prev_7d, "drop_pct": drop_pct},
        })

    # 5. Taux de perte élevé récent
    last_30d_decided = db.query(Opportunity).filter(
        and_(
            Opportunity.updated_at >= now - timedelta(days=30),
            Opportunity.status.in_([OpportunityStatus.WON, OpportunityStatus.LOST]),
        )
    ).all()
    if len(last_30d_decided) >= 5:
        lost_count = len([o for o in last_30d_decided if o.status == OpportunityStatus.LOST])
        loss_rate = round(lost_count / len(last_30d_decided) * 100)
        if loss_rate > 70:
            signals.append({
                "type": "high_loss_rate",
                "priority": "high",
                "icon": "⚠️",
                "title": f"Taux de perte élevé : {loss_rate}%",
                "description": f"{lost_count} perdues sur {len(last_30d_decided)} décidées (30j)",
                "opportunity_id": None,
                "metadata": {"loss_rate": loss_rate, "lost": lost_count, "total": len(last_30d_decided)},
            })

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    signals.sort(key=lambda s: priority_order.get(s["priority"], 9))

    result = {
        "count": len(signals),
        "signals": signals,
        "summary": {
            "stale": len(stale_opps),
            "deadline_risk": len(urgent_no_action),
            "high_value_untouched": len(high_value_untouched),
        },
        "updated_at": now.isoformat(),
    }

    cache_set(cache_key, result, 120)  # 2 minutes cache
    return result


# ============================================================================
# INSIGHTS AUTOMATIQUES
# ============================================================================

@router.get("/insights")
def get_automated_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Génère des insights automatiques basés sur l'analyse des données :
    - Meilleure source de conversion
    - Catégorie la plus rentable
    - Jour/période optimale
    - Recommandations d'action
    """
    cache_key = f"analytics:insights:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    now = datetime.utcnow()
    insights = []

    # Get all opportunities for deep analysis
    all_opps = db.query(Opportunity).all()
    recent_opps = [o for o in all_opps if o.created_at and o.created_at >= now - timedelta(days=90)]

    if not recent_opps:
        return {"insights": [], "updated_at": now.isoformat()}

    # 1. Best converting source
    source_stats = defaultdict(lambda: {"won": 0, "total_decided": 0, "value": 0})
    for opp in recent_opps:
        source = opp.source_name or "unknown"
        if opp.status in [OpportunityStatus.WON, OpportunityStatus.LOST]:
            source_stats[source]["total_decided"] += 1
            if opp.status == OpportunityStatus.WON:
                source_stats[source]["won"] += 1
                if opp.budget_amount:
                    source_stats[source]["value"] += float(opp.budget_amount)

    best_source = None
    best_rate = 0
    for source, stats in source_stats.items():
        if stats["total_decided"] >= 3:
            rate = stats["won"] / stats["total_decided"]
            if rate > best_rate:
                best_rate = rate
                best_source = source

    if best_source and best_rate > 0:
        insights.append({
            "type": "best_source",
            "icon": "🎯",
            "title": "Source la plus performante",
            "description": f"**{best_source}** convertit à {round(best_rate * 100)}% — "
                          f"concentrez vos efforts de veille dessus.",
            "metric": f"{round(best_rate * 100)}%",
            "category": "conversion",
        })

    # 2. Most profitable category
    cat_revenue = defaultdict(lambda: {"value": 0, "count": 0})
    for opp in recent_opps:
        if opp.status == OpportunityStatus.WON and opp.budget_amount:
            cat = opp.category.value if opp.category else "other"
            cat_revenue[cat]["value"] += float(opp.budget_amount)
            cat_revenue[cat]["count"] += 1

    if cat_revenue:
        best_cat = max(cat_revenue.items(), key=lambda x: x[1]["value"])
        insights.append({
            "type": "best_category",
            "icon": "💎",
            "title": "Catégorie la plus rentable",
            "description": f"**{best_cat[0].capitalize()}** génère {round(best_cat[1]['value'])}€ "
                          f"sur {best_cat[1]['count']} projets gagnés.",
            "metric": f"{round(best_cat[1]['value'])}€",
            "category": "revenue",
        })

    # 3. Average time to win
    won_opps = [o for o in recent_opps if o.status == OpportunityStatus.WON and o.created_at and o.updated_at]
    if len(won_opps) >= 3:
        avg_days = sum((o.updated_at - o.created_at).days for o in won_opps) / len(won_opps)
        insights.append({
            "type": "avg_cycle",
            "icon": "⏱️",
            "title": "Cycle de vente moyen",
            "description": f"Il faut en moyenne **{round(avg_days)} jours** entre la détection et le gain. "
                          f"Basé sur {len(won_opps)} projets gagnés.",
            "metric": f"{round(avg_days)}j",
            "category": "performance",
        })

    # 4. Score vs outcome correlation
    won_scores = [o.score for o in recent_opps if o.status == OpportunityStatus.WON and o.score]
    lost_scores = [o.score for o in recent_opps if o.status == OpportunityStatus.LOST and o.score]
    if won_scores and lost_scores:
        avg_won = sum(won_scores) / len(won_scores)
        avg_lost = sum(lost_scores) / len(lost_scores)
        if avg_won > avg_lost:
            insights.append({
                "type": "score_correlation",
                "icon": "📊",
                "title": "Le scoring est fiable",
                "description": f"Score moyen des gagnées : **{round(avg_won)}** vs perdues : **{round(avg_lost)}**. "
                              f"Fiez-vous au scoring pour prioriser.",
                "metric": f"+{round(avg_won - avg_lost)}pts",
                "category": "scoring",
            })

    # 5. Pipeline health
    active_count = len([o for o in all_opps if o.status in [
        OpportunityStatus.NEW, OpportunityStatus.CONTACTED, OpportunityStatus.IN_PROGRESS
    ]])
    pipeline_value = sum(
        float(o.budget_amount) for o in all_opps
        if o.status in [OpportunityStatus.NEW, OpportunityStatus.CONTACTED, OpportunityStatus.IN_PROGRESS]
        and o.budget_amount
    )
    if active_count > 0:
        insights.append({
            "type": "pipeline_health",
            "icon": "🔄",
            "title": "Pipeline actif",
            "description": f"**{active_count} opportunités** en cours pour un total de "
                          f"**{round(pipeline_value)}€** en pipeline.",
            "metric": f"{active_count}",
            "category": "pipeline",
        })

    result = {
        "insights": insights,
        "updated_at": now.isoformat(),
    }

    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# PRÉDICTIONS PIPELINE 30/60/90 JOURS
# ============================================================================

@router.get("/predictions-summary", dependencies=[Depends(suspend_predictions)])
def get_predictions_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Prédictions du pipeline sur 30, 60 et 90 jours :
    - Nombre d'opportunités attendues par période
    - Valeur estimée
    - Projets à forte probabilité de gain
    """
    cache_key = f"analytics:predictions:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    now = datetime.utcnow()

    active_statuses = [
        OpportunityStatus.NEW,
        OpportunityStatus.CONTACTED,
        OpportunityStatus.IN_PROGRESS,
    ]

    active_opps = db.query(Opportunity).filter(
        Opportunity.status.in_(active_statuses)
    ).all()

    periods = [
        {"label": "30j", "days": 30},
        {"label": "60j", "days": 60},
        {"label": "90j", "days": 90},
    ]

    predictions = []

    for period in periods:
        cutoff = now + timedelta(days=period["days"])

        # Opportunités avec deadline dans cette période
        period_opps = [
            o for o in active_opps
            if o.deadline_at and o.deadline_at <= cutoff
        ]

        # Estimer probabilité de gain basée sur le score
        high_prob = []  # score >= 70
        med_prob = []   # score >= 40
        low_prob = []   # score < 40

        total_value = 0
        weighted_value = 0

        for opp in period_opps:
            score = opp.score or 0
            budget = float(opp.budget_amount) if opp.budget_amount else 0
            total_value += budget

            if score >= 70:
                high_prob.append(opp.id)
                weighted_value += budget * 0.75
            elif score >= 40:
                med_prob.append(opp.id)
                weighted_value += budget * 0.40
            else:
                low_prob.append(opp.id)
                weighted_value += budget * 0.15

        predictions.append({
            "period": period["label"],
            "days": period["days"],
            "total_opportunities": len(period_opps),
            "total_value": round(total_value, 2),
            "weighted_value": round(weighted_value, 2),
            "high_probability": len(high_prob),
            "medium_probability": len(med_prob),
            "low_probability": len(low_prob),
        })

    # Top 5 most likely to close (highest score among active with deadline)
    scored_opps = [
        o for o in active_opps
        if o.score and o.deadline_at and o.deadline_at >= now
    ]
    scored_opps.sort(key=lambda o: o.score, reverse=True)

    top_likely = []
    for opp in scored_opps[:5]:
        prob = min(95, max(10, opp.score * 1.1))  # Rough probability from score
        top_likely.append({
            "id": opp.id,
            "title": opp.title[:80],
            "score": opp.score,
            "probability": round(prob),
            "budget": float(opp.budget_amount) if opp.budget_amount else None,
            "deadline": opp.deadline_at.isoformat() if opp.deadline_at else None,
        })

    result = {
        "predictions": predictions,
        "top_likely_wins": top_likely,
        "total_pipeline": len(active_opps),
        "updated_at": now.isoformat(),
    }

    cache_set(cache_key, result, CACHE_TTL)
    return result
