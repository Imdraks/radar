"""
Competitive Intelligence Dashboard API
Veille concurrentielle, benchmark, alertes compétiteurs
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from collections import defaultdict

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import Opportunity, OpportunityStatus, OpportunityCategory
from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set

router = APIRouter(prefix="/competitive", tags=["competitive"])

CACHE_TTL = 600  # 10 minutes


# ============================================================================
# MODELS
# ============================================================================

class CompetitorCreate(BaseModel):
    """Créer un concurrent à surveiller"""
    name: str = Field(..., min_length=2, max_length=200)
    keywords: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    notes: Optional[str] = None


class CompetitorUpdate(BaseModel):
    """Mettre à jour un concurrent"""
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# In-memory storage for competitors (à remplacer par DB plus tard)
# Format: {user_id: {competitor_id: competitor_data}}
_competitors_store: Dict[int, Dict[int, Dict]] = {}
_competitor_counter = 0


def _get_user_competitors(user_id: int) -> Dict[int, Dict]:
    """Get competitors for a user"""
    if user_id not in _competitors_store:
        _competitors_store[user_id] = {}
    return _competitors_store[user_id]


# ============================================================================
# GESTION DES CONCURRENTS
# ============================================================================

@router.get("/competitors")
def list_competitors(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Liste des concurrents surveillés"""
    competitors = _get_user_competitors(current_user.id)
    return [
        {"id": k, **v}
        for k, v in competitors.items()
        if v.get("is_active", True)
    ]


@router.post("/competitors")
def add_competitor(
    data: CompetitorCreate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ajouter un concurrent à surveiller"""
    global _competitor_counter
    _competitor_counter += 1
    
    competitors = _get_user_competitors(current_user.id)
    
    competitor = {
        "name": data.name,
        "keywords": data.keywords or [data.name.lower()],
        "website": data.website,
        "notes": data.notes,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "mentions_count": 0
    }
    
    competitors[_competitor_counter] = competitor
    
    return {"id": _competitor_counter, **competitor}


@router.put("/competitors/{competitor_id}")
def update_competitor(
    competitor_id: int,
    data: CompetitorUpdate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mettre à jour un concurrent"""
    competitors = _get_user_competitors(current_user.id)
    
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor = competitors[competitor_id]
    
    if data.name is not None:
        competitor["name"] = data.name
    if data.keywords is not None:
        competitor["keywords"] = data.keywords
    if data.website is not None:
        competitor["website"] = data.website
    if data.notes is not None:
        competitor["notes"] = data.notes
    if data.is_active is not None:
        competitor["is_active"] = data.is_active
    
    competitor["updated_at"] = datetime.utcnow().isoformat()
    
    return {"id": competitor_id, **competitor}


@router.delete("/competitors/{competitor_id}")
def delete_competitor(
    competitor_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Supprimer un concurrent"""
    competitors = _get_user_competitors(current_user.id)
    
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    del competitors[competitor_id]
    
    return {"status": "deleted"}


# ============================================================================
# DÉTECTION DES MENTIONS
# ============================================================================

@router.get("/mentions")
def get_competitor_mentions(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Détecte les mentions de concurrents dans les opportunités
    """
    competitors = _get_user_competitors(current_user.id)
    active_competitors = {k: v for k, v in competitors.items() if v.get("is_active", True)}
    
    if not active_competitors:
        return {
            "period": period,
            "mentions": [],
            "total": 0,
            "message": "Ajoutez des concurrents à surveiller"
        }
    
    now = datetime.utcnow()
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=90)
    
    # Get recent opportunities
    opps = db.query(Opportunity).filter(
        Opportunity.created_at >= start_date
    ).all()
    
    mentions = []
    
    for opp in opps:
        # Build searchable text
        search_text = " ".join(filter(None, [
            opp.title,
            opp.description,
            opp.organization,
            opp.raw_text
        ])).lower()
        
        for comp_id, comp in active_competitors.items():
            for keyword in comp.get("keywords", []):
                if keyword.lower() in search_text:
                    mentions.append({
                        "competitor_id": comp_id,
                        "competitor_name": comp["name"],
                        "keyword_matched": keyword,
                        "opportunity": {
                            "id": opp.id,
                            "title": opp.title[:100],
                            "organization": opp.organization,
                            "status": opp.status.value if opp.status else None,
                            "budget": float(opp.budget_amount) if opp.budget_amount else None,
                            "created_at": opp.created_at.isoformat()
                        }
                    })
                    break  # One mention per opp per competitor
    
    # Group by competitor
    by_competitor = defaultdict(list)
    for mention in mentions:
        by_competitor[mention["competitor_name"]].append(mention)
    
    summary = [
        {"name": name, "count": len(items), "recent": items[:3]}
        for name, items in sorted(by_competitor.items(), key=lambda x: len(x[1]), reverse=True)
    ]
    
    return {
        "period": period,
        "mentions": mentions[:50],  # Limit to 50
        "by_competitor": summary,
        "total": len(mentions)
    }


# ============================================================================
# ANALYSE DES GAGNANTS
# ============================================================================

@router.get("/winners-analysis")
def get_winners_analysis(
    period: str = Query("90d", pattern="^(30d|90d|12m)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Analyse qui gagne les opportunités (organisations récurrentes)
    """
    cache_key = f"competitive:winners:{current_user.id}:{period}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    if period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=365)
    
    # Get WON opportunities
    won_opps = db.query(Opportunity).filter(
        and_(
            Opportunity.status == OpportunityStatus.WON,
            Opportunity.created_at >= start_date
        )
    ).all()
    
    # Analyse by organization
    by_org = defaultdict(lambda: {"count": 0, "value": 0, "categories": set()})
    
    for opp in won_opps:
        org = opp.organization or "Unknown"
        by_org[org]["count"] += 1
        if opp.budget_amount:
            by_org[org]["value"] += float(opp.budget_amount)
        if opp.category:
            by_org[org]["categories"].add(opp.category.value)
    
    # Convert to list and sort
    winners = []
    for org, data in by_org.items():
        winners.append({
            "organization": org,
            "wins": data["count"],
            "total_value": round(data["value"], 2),
            "categories": list(data["categories"]),
            "avg_value": round(data["value"] / data["count"], 2) if data["count"] > 0 else 0
        })
    
    winners.sort(key=lambda x: x["wins"], reverse=True)
    
    # Identify potential competitors (orgs that win a lot)
    potential_competitors = [w for w in winners if w["wins"] >= 3]
    
    result = {
        "period": period,
        "total_won": len(won_opps),
        "unique_winners": len(winners),
        "top_winners": winners[:20],
        "potential_competitors": potential_competitors[:10],
        "insights": _generate_winner_insights(winners, won_opps)
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


def _generate_winner_insights(winners: List[Dict], opps: List) -> List[str]:
    """Generate insights about winners"""
    insights = []
    
    if winners:
        top = winners[0]
        insights.append(f"🏆 {top['organization']} domine avec {top['wins']} victoires")
        
        # Concentration
        top_3_wins = sum(w["wins"] for w in winners[:3])
        total_wins = len(opps)
        if total_wins > 0:
            concentration = round(top_3_wins / total_wins * 100, 1)
            if concentration > 50:
                insights.append(f"⚠️ Marché concentré: Top 3 = {concentration}% des gains")
        
        # High value winners
        high_value = [w for w in winners if w["avg_value"] > 50000]
        if high_value:
            insights.append(f"💰 {len(high_value)} organisations gagnent des gros budgets (>50k€)")
    
    return insights


# ============================================================================
# BENCHMARK PRICING
# ============================================================================

@router.get("/pricing-benchmark")
def get_pricing_benchmark(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Benchmark des prix par catégorie
    """
    cache_key = f"competitive:pricing:{current_user.id}:{category or 'all'}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    query = db.query(Opportunity).filter(
        Opportunity.budget_amount.isnot(None),
        Opportunity.budget_amount > 0
    )
    
    if category:
        try:
            cat_enum = OpportunityCategory(category)
            query = query.filter(Opportunity.category == cat_enum)
        except ValueError:
            pass
    
    opps = query.all()
    
    if not opps:
        return {"message": "Pas assez de données", "data": []}
    
    # Group by category
    by_category = defaultdict(list)
    for opp in opps:
        cat = opp.category.value if opp.category else "other"
        by_category[cat].append(float(opp.budget_amount))
    
    benchmarks = []
    for cat, budgets in by_category.items():
        budgets.sort()
        n = len(budgets)
        benchmarks.append({
            "category": cat,
            "count": n,
            "min": budgets[0],
            "max": budgets[-1],
            "avg": round(sum(budgets) / n, 2),
            "median": budgets[n // 2],
            "p25": budgets[n // 4] if n >= 4 else budgets[0],
            "p75": budgets[3 * n // 4] if n >= 4 else budgets[-1]
        })
    
    benchmarks.sort(key=lambda x: x["avg"], reverse=True)
    
    # Global stats
    all_budgets = [float(o.budget_amount) for o in opps]
    all_budgets.sort()
    n_all = len(all_budgets)
    
    result = {
        "global": {
            "count": n_all,
            "min": all_budgets[0],
            "max": all_budgets[-1],
            "avg": round(sum(all_budgets) / n_all, 2),
            "median": all_budgets[n_all // 2]
        },
        "by_category": benchmarks,
        "insights": _generate_pricing_insights(benchmarks)
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


def _generate_pricing_insights(benchmarks: List[Dict]) -> List[str]:
    """Generate pricing insights"""
    insights = []
    
    if benchmarks:
        highest = benchmarks[0]
        insights.append(f"💰 {highest['category']} a les budgets les plus élevés (moy: {highest['avg']:,.0f}€)")
        
        # Find high variance categories
        for b in benchmarks:
            if b["count"] >= 5 and b["max"] > b["min"] * 10:
                insights.append(f"📊 {b['category']}: forte variance ({b['min']:,.0f}€ - {b['max']:,.0f}€)")
    
    return insights


# ============================================================================
# ALERTES COMPÉTITIVES
# ============================================================================

@router.get("/alerts")
def get_competitive_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Alertes de veille compétitive
    """
    competitors = _get_user_competitors(current_user.id)
    active_competitors = {k: v for k, v in competitors.items() if v.get("is_active", True)}
    
    alerts = []
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    if not active_competitors:
        return {
            "alerts": [],
            "message": "Configurez des concurrents pour recevoir des alertes"
        }
    
    # Check for new mentions in last 24h
    recent_opps = db.query(Opportunity).filter(
        Opportunity.created_at >= yesterday
    ).all()
    
    for opp in recent_opps:
        search_text = " ".join(filter(None, [
            opp.title,
            opp.description,
            opp.organization
        ])).lower()
        
        for comp_id, comp in active_competitors.items():
            for keyword in comp.get("keywords", []):
                if keyword.lower() in search_text:
                    alerts.append({
                        "type": "competitor_mention",
                        "priority": "high",
                        "competitor": comp["name"],
                        "message": f"🚨 {comp['name']} mentionné dans une nouvelle opportunité",
                        "opportunity_id": opp.id,
                        "opportunity_title": opp.title[:80],
                        "created_at": opp.created_at.isoformat()
                    })
                    break
    
    # Check for high-value opportunities in competitor's domain
    high_value_opps = db.query(Opportunity).filter(
        and_(
            Opportunity.created_at >= yesterday,
            Opportunity.budget_amount >= 50000
        )
    ).all()
    
    for opp in high_value_opps:
        if opp.id not in [a["opportunity_id"] for a in alerts if "opportunity_id" in a]:
            alerts.append({
                "type": "high_value",
                "priority": "medium",
                "message": f"💰 Nouvelle opportunité à fort budget: {float(opp.budget_amount):,.0f}€",
                "opportunity_id": opp.id,
                "opportunity_title": opp.title[:80],
                "created_at": opp.created_at.isoformat()
            })
    
    # Sort by priority and time
    priority_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["created_at"]), reverse=True)
    
    return {
        "alerts": alerts[:20],
        "total": len(alerts),
        "last_check": now.isoformat()
    }


# ============================================================================
# MARKET SHARE ESTIMATION
# ============================================================================

@router.get("/market-share")
def get_market_share_estimate(
    period: str = Query("90d", pattern="^(30d|90d|12m)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Estimation de parts de marché basée sur les opportunités gagnées
    """
    cache_key = f"competitive:market:{current_user.id}:{period}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    if period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=365)
    
    # All decided opportunities
    decided = db.query(Opportunity).filter(
        and_(
            Opportunity.created_at >= start_date,
            Opportunity.status.in_([OpportunityStatus.WON, OpportunityStatus.LOST])
        )
    ).all()
    
    won = [o for o in decided if o.status == OpportunityStatus.WON]
    
    total_count = len(decided)
    won_count = len(won)
    
    total_value = sum(float(o.budget_amount) for o in decided if o.budget_amount)
    won_value = sum(float(o.budget_amount) for o in won if o.budget_amount)
    
    # By category
    by_category = defaultdict(lambda: {"total": 0, "won": 0, "value_total": 0, "value_won": 0})
    for opp in decided:
        cat = opp.category.value if opp.category else "other"
        by_category[cat]["total"] += 1
        if opp.budget_amount:
            by_category[cat]["value_total"] += float(opp.budget_amount)
        if opp.status == OpportunityStatus.WON:
            by_category[cat]["won"] += 1
            if opp.budget_amount:
                by_category[cat]["value_won"] += float(opp.budget_amount)
    
    category_shares = []
    for cat, data in by_category.items():
        count_share = round(data["won"] / data["total"] * 100, 1) if data["total"] > 0 else 0
        value_share = round(data["value_won"] / data["value_total"] * 100, 1) if data["value_total"] > 0 else 0
        category_shares.append({
            "category": cat,
            "count_share": count_share,
            "value_share": value_share,
            "won": data["won"],
            "total": data["total"]
        })
    
    category_shares.sort(key=lambda x: x["value_share"], reverse=True)
    
    result = {
        "period": period,
        "overall": {
            "count_share": round(won_count / total_count * 100, 1) if total_count > 0 else 0,
            "value_share": round(won_value / total_value * 100, 1) if total_value > 0 else 0,
            "won_count": won_count,
            "total_count": total_count,
            "won_value": round(won_value, 2),
            "total_value": round(total_value, 2)
        },
        "by_category": category_shares,
        "insights": [
            f"🎯 Taux de conversion global: {round(won_count / total_count * 100, 1)}%" if total_count > 0 else "Pas assez de données",
            f"💰 Part de valeur captée: {round(won_value / total_value * 100, 1)}%" if total_value > 0 else ""
        ]
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result
