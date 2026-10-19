"""
API Endpoints pour les nouvelles fonctionnalités
- Rapports hebdomadaires
- Alertes intelligentes
- Audit log
- Export
- Scoring ML
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import Opportunity, OpportunityStatus
from app.api.deps import get_current_user, require_admin, get_current_workspace_id

# Services
from app.services.weekly_report_service import WeeklyReportService
from app.services.smart_alerts import SmartAlertService, run_alert_checks, AlertType, AlertPriority
from app.services.audit_log import AuditService, AuditAction, audit_log_to_dict
from app.services.export_service import ExportService
from app.scoring.ml_scoring import MLScoringEngine

def suspend_predictions():
    raise HTTPException(status_code=503, detail="Prédictions commerciales suspendues : méthode non validée")


router = APIRouter(tags=["Advanced Features"])


# ==============================================================
# RAPPORTS HEBDOMADAIRES
# ==============================================================

@router.get("/reports/weekly")
def get_weekly_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Génère le rapport hebdomadaire.
    Retourne les statistiques et le HTML du rapport.
    """
    service = WeeklyReportService(db)
    stats = service.generate_weekly_stats()
    html = service.generate_html_report(stats)
    
    return {
        "period": {
            "start": stats.period_start.isoformat(),
            "end": stats.period_end.isoformat()
        },
        "stats": {
            "total_new": stats.total_new,
            "total_qualified": stats.total_qualified,
            "total_submitted": stats.total_submitted,
            "total_won": stats.total_won,
            "total_lost": stats.total_lost,
            "budget_won": float(stats.budget_won),
            "budget_pipeline": float(stats.budget_pipeline),
            "conversion_rate": stats.conversion_rate,
            "avg_score_new": stats.avg_score_new,
        },
        "by_category": stats.by_category,
        "by_source": stats.by_source,
        "top_opportunities": stats.top_opportunities,
        "urgent_deadlines": stats.urgent_deadlines,
        "vs_previous_week": stats.vs_previous_week,
        "html_report": html
    }


@router.post("/reports/weekly/send")
def send_weekly_report(
    recipients: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Génère et envoie le rapport hebdomadaire par email.
    Admin only.
    """
    service = WeeklyReportService(db)
    result = service.generate_and_send(recipients)
    return result


# ==============================================================
# ALERTES INTELLIGENTES
# ==============================================================

@router.get("/alerts/check")
def check_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Vérifie toutes les alertes actuelles.
    Retourne les alertes deadline, high score et opportunités stagnantes.
    """
    result = run_alert_checks(db)
    return result


@router.get("/alerts/deadlines")
def get_deadline_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère uniquement les alertes deadline.
    """
    service = SmartAlertService(db)
    alerts = service.check_deadline_alerts()
    
    return {
        "count": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    }


@router.get("/alerts/high-score")
def get_high_score_alerts(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère les nouvelles opportunités à score élevé (>=15).
    """
    service = SmartAlertService(db)
    alerts = service.check_high_score_alerts(since_hours=hours)
    
    return {
        "count": len(alerts),
        "since_hours": hours,
        "alerts": [a.to_dict() for a in alerts]
    }


@router.post("/alerts/send")
def send_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Envoie les alertes importantes via Discord/Slack.
    Admin only.
    """
    service = SmartAlertService(db)
    all_alerts = service.run_all_checks()
    
    # Collecter les alertes importantes
    important = []
    for alerts in all_alerts.values():
        important.extend([
            a for a in alerts
            if a.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]
        ])
    
    sent = service.send_alerts(important)
    
    return {
        "total_alerts": sum(len(a) for a in all_alerts.values()),
        "important_alerts": len(important),
        "sent": sent
    }


# ==============================================================
# AUDIT LOG
# ==============================================================

@router.get("/audit/opportunity/{opportunity_id}")
def get_opportunity_history(
    opportunity_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id),
):
    """
    Récupère l'historique complet d'une opportunité.
    """
    # Verify opportunity belongs to user's workspace
    from app.db.models.opportunity import Opportunity
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == workspace_id
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    service = AuditService(db)
    logs = service.get_entity_history("opportunity", str(opportunity_id), limit)
    
    return {
        "opportunity_id": opportunity_id,
        "count": len(logs),
        "history": [audit_log_to_dict(log) for log in logs]
    }


@router.get("/audit/user/{user_id}")
def get_user_activity(
    user_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Récupère l'activité d'un utilisateur.
    Admin only.
    """
    service = AuditService(db)
    logs = service.get_user_activity(user_id, limit)
    
    return {
        "user_id": user_id,
        "count": len(logs),
        "activity": [audit_log_to_dict(log) for log in logs]
    }


@router.get("/audit/recent")
def get_recent_activity(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère l'activité récente sur la plateforme.
    """
    service = AuditService(db)
    logs = service.get_recent_activity(hours=hours, limit=limit)
    
    return {
        "since_hours": hours,
        "count": len(logs),
        "activity": [audit_log_to_dict(log) for log in logs]
    }


@router.get("/audit/stats")
def get_audit_stats(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Statistiques des changements de status et utilisateurs actifs.
    Admin only.
    """
    service = AuditService(db)
    return service.get_status_changes_stats(days)


# ==============================================================
# EXPORT
# ==============================================================

class ExportRequest(BaseModel):
    opportunity_ids: Optional[List[int]] = None
    status: Optional[str] = None
    min_score: Optional[int] = None
    format: str = "xlsx"  # xlsx, csv, pdf


@router.post("/export/opportunities")
def export_opportunities(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exporte les opportunités au format choisi (xlsx, csv, pdf).
    Retourne le fichier encodé en base64.
    """
    # Construire la requête
    query = db.query(Opportunity)
    
    if request.opportunity_ids:
        query = query.filter(Opportunity.id.in_(request.opportunity_ids))
    
    if request.status:
        try:
            status = OpportunityStatus(request.status)
            query = query.filter(Opportunity.status == status)
        except ValueError:
            pass
    
    if request.min_score:
        query = query.filter(Opportunity.score >= request.min_score)
    
    opportunities = query.order_by(Opportunity.score.desc()).limit(1000).all()
    
    if not opportunities:
        raise HTTPException(status_code=404, detail="No opportunities to export")
    
    service = ExportService(db)
    
    if request.format == "xlsx":
        content = service.export_opportunities_excel(opportunities)
        return service.export_to_base64(content, "xlsx")
    
    elif request.format == "csv":
        content = service.export_opportunities_csv(opportunities)
        return {
            "content": content,
            "mime_type": "text/csv",
            "format": "csv"
        }
    
    elif request.format == "pdf":
        try:
            content = service.export_opportunities_pdf(opportunities)
            return service.export_to_base64(content, "pdf")
        except ImportError as e:
            raise HTTPException(
                status_code=501,
                detail="PDF export requires reportlab. Install with: pip install reportlab"
            )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


@router.get("/export/opportunities/download")
def download_opportunities(
    format: str = Query("xlsx", regex="^(xlsx|csv|pdf)$"),
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Télécharge directement les opportunités (réponse binaire).
    """
    query = db.query(Opportunity)
    
    if status:
        try:
            s = OpportunityStatus(status)
            query = query.filter(Opportunity.status == s)
        except ValueError:
            pass
    
    if min_score:
        query = query.filter(Opportunity.score >= min_score)
    
    opportunities = query.order_by(Opportunity.score.desc()).limit(1000).all()
    
    if not opportunities:
        raise HTTPException(status_code=404, detail="No opportunities to export")
    
    service = ExportService(db)
    filename = f"opportunities_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    if format == "xlsx":
        content = service.export_opportunities_excel(opportunities)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    
    elif format == "csv":
        content = service.export_opportunities_csv(opportunities)
        return Response(
            content=content.encode('utf-8-sig'),  # BOM for Excel
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
        )
    
    elif format == "pdf":
        content = service.export_opportunities_pdf(opportunities)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )


# ==============================================================
# ML SCORING
# ==============================================================

@router.get("/scoring/ml/{opportunity_id}", dependencies=[Depends(suspend_predictions)])
def get_ml_score(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyse une opportunité avec le scoring ML basé sur l'historique.
    """
    engine = MLScoringEngine(db)
    result = engine.score_opportunity(opportunity_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return {
        "opportunity_id": result.opportunity_id,
        "base_score": result.base_score,
        "ml_adjustment": result.ml_adjustment,
        "final_score": result.final_score,
        "win_probability": result.win_probability,
        "confidence": result.confidence,
        "patterns_matched": [
            {
                "name": p.name,
                "win_rate": round(p.win_rate * 100, 1),
                "impact": round(p.impact_score, 2),
                "confidence": round(p.confidence * 100, 1)
            }
            for p in result.patterns_matched
        ],
        "similar_won": result.similar_won,
        "similar_lost": result.similar_lost,
        "recommendations": result.recommendations
    }


@router.get("/scoring/ml/patterns", dependencies=[Depends(suspend_predictions)])
def get_ml_patterns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Affiche les patterns appris par le système ML.
    """
    engine = MLScoringEngine(db)
    return engine.get_patterns_summary()


@router.post("/scoring/ml/batch", dependencies=[Depends(suspend_predictions)])
def batch_ml_score(
    opportunity_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Score plusieurs opportunités avec le ML.
    """
    engine = MLScoringEngine(db)
    results = []
    
    for opp_id in opportunity_ids[:50]:  # Limite à 50
        result = engine.score_opportunity(opp_id)
        if result:
            results.append({
                "opportunity_id": result.opportunity_id,
                "base_score": result.base_score,
                "ml_adjustment": result.ml_adjustment,
                "final_score": result.final_score,
                "win_probability": result.win_probability,
                "confidence": result.confidence
            })
    
    return {
        "count": len(results),
        "results": results
    }


# ==============================================================
# RATE LIMIT INFO
# ==============================================================

@router.get("/rate-limit/status")
def get_rate_limit_status(
    current_user: User = Depends(get_current_user),
):
    """
    Affiche le status actuel du rate limiting pour l'utilisateur.
    """
    from app.core.rate_limiter import get_rate_limiter
    
    limiter = get_rate_limiter()
    key = f"user:{current_user.id}"
    stats = limiter.get_usage_stats(key)
    
    return {
        "user_id": current_user.id,
        "usage": {
            "minute": stats["minute"],
            "hour": stats["hour"],
            "day": stats["day"]
        },
        "limits": stats["limits"],
        "remaining": {
            "minute": max(0, stats["limits"]["minute"] - stats["minute"]),
            "hour": max(0, stats["limits"]["hour"] - stats["hour"]),
            "day": max(0, stats["limits"]["day"] - stats["day"])
        }
    }
