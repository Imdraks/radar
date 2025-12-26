"""
API endpoints for Auto Radar - Automated harvesting
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.db.models.user import User


router = APIRouter()


class HarvestReport(BaseModel):
    id: str
    harvest_time: Optional[datetime]
    sources_scanned: int
    items_fetched: int
    items_new: int
    items_duplicate: int
    opportunities_created: int
    opportunities_excellent: int
    opportunities_good: int
    opportunities_average: int
    opportunities_poor: int
    notifications_sent: int
    duration_seconds: float
    status: str
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class HarvestTriggerResponse(BaseModel):
    message: str
    task_id: str


@router.get("/reports", response_model=List[HarvestReport])
async def get_harvest_reports(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les derniers rapports de récolte automatique
    """
    from app.workers.auto_radar_task import RadarHarvestReport
    
    reports = db.query(RadarHarvestReport)\
        .order_by(RadarHarvestReport.harvest_time.desc())\
        .limit(limit)\
        .all()
    
    return reports


@router.post("/trigger", response_model=HarvestTriggerResponse)
async def trigger_harvest(
    current_user: User = Depends(get_current_user)
):
    """
    Déclencher manuellement une récolte Radar
    """
    from app.workers.auto_radar_task import auto_radar_harvest
    
    # Lancer la tâche en arrière-plan
    task = auto_radar_harvest.delay()
    
    return HarvestTriggerResponse(
        message="Récolte automatique lancée",
        task_id=task.id
    )


@router.get("/status/{task_id}")
async def get_harvest_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer le statut d'une tâche de récolte
    """
    from celery.result import AsyncResult
    from app.workers.celery_app import celery_app
    
    result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }
    
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    
    return response


@router.get("/stats")
async def get_radar_stats(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Statistiques des récoltes sur les X derniers jours
    """
    from app.workers.auto_radar_task import RadarHarvestReport
    from datetime import timedelta
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Agrégations
    stats = db.query(
        func.count(RadarHarvestReport.id).label("total_harvests"),
        func.sum(RadarHarvestReport.sources_scanned).label("total_sources_scanned"),
        func.sum(RadarHarvestReport.items_fetched).label("total_items_fetched"),
        func.sum(RadarHarvestReport.opportunities_created).label("total_opportunities_created"),
        func.sum(RadarHarvestReport.opportunities_excellent).label("total_excellent"),
        func.sum(RadarHarvestReport.opportunities_good).label("total_good"),
        func.sum(RadarHarvestReport.notifications_sent).label("total_notifications"),
        func.avg(RadarHarvestReport.duration_seconds).label("avg_duration"),
    ).filter(
        RadarHarvestReport.harvest_time >= since,
        RadarHarvestReport.status == "success"
    ).first()
    
    # Dernière récolte
    last_harvest = db.query(RadarHarvestReport)\
        .order_by(RadarHarvestReport.harvest_time.desc())\
        .first()
    
    return {
        "period_days": days,
        "total_harvests": stats.total_harvests or 0,
        "total_sources_scanned": stats.total_sources_scanned or 0,
        "total_items_fetched": stats.total_items_fetched or 0,
        "total_opportunities_created": stats.total_opportunities_created or 0,
        "total_excellent": stats.total_excellent or 0,
        "total_good": stats.total_good or 0,
        "total_notifications": stats.total_notifications or 0,
        "avg_duration_seconds": round(stats.avg_duration or 0, 2),
        "last_harvest": {
            "time": last_harvest.harvest_time.isoformat() if last_harvest and last_harvest.harvest_time else None,
            "status": last_harvest.status if last_harvest else None,
            "opportunities_created": last_harvest.opportunities_created if last_harvest else 0,
        } if last_harvest else None
    }
