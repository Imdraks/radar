"""
Auto Radar Task - Automatisation toutes les 15 minutes
Extrait toutes les sources, filtre, score et notifie les opportunités excellentes
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.workers.celery_app import celery_app
from app.workers.task_logger import get_task_logger, Colors
from app.workers.progress_notifier import get_progress_notifier
from app.db.session import SessionLocal
from app.db.models.source import SourceConfig
from app.db.models.opportunity import Opportunity, OpportunityStatus, SourceType
from app.db.models.ingestion import IngestionRun, IngestionStatus
from app.db.models.user import User
from app.ingestion.factory import get_connector
from app.extraction.extractor import DataExtractor
from app.extraction.deduplicator import Deduplicator
from app.scoring.engine import ScoringEngine
from app.workers.notifications import send_notifications


# Modèle pour stocker les rapports de récolte
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from app.db.base import Base


class RadarHarvestReport(Base):
    """Rapport de récolte automatique"""
    __tablename__ = "radar_harvest_reports"
    
    id = Column(String(36), primary_key=True)
    harvest_time = Column(DateTime, default=datetime.utcnow)
    sources_scanned = Column(Integer, default=0)
    items_fetched = Column(Integer, default=0)
    items_new = Column(Integer, default=0)
    items_duplicate = Column(Integer, default=0)
    opportunities_created = Column(Integer, default=0)
    opportunities_excellent = Column(Integer, default=0)
    opportunities_good = Column(Integer, default=0)
    opportunities_average = Column(Integer, default=0)
    opportunities_poor = Column(Integer, default=0)
    notifications_sent = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)


def get_db() -> Session:
    """Get database session"""
    return SessionLocal()


def classify_opportunity(score: float) -> str:
    """Classifier une opportunité par son score"""
    if score >= 15:
        return "excellent"  # 🌟 Notification immédiate
    elif score >= 10:
        return "good"  # ✅ Bonne opportunité
    elif score >= 5:
        return "average"  # 📊 Moyenne
    else:
        return "poor"  # ⚠️ Faible intérêt


def should_notify(opportunity: Opportunity, score: float) -> bool:
    """Déterminer si une opportunité mérite une notification"""
    # Notifier si score >= 15 (excellent)
    if score >= 15:
        return True
    
    # Notifier si deadline proche (< 7 jours) et score >= 10
    if opportunity.deadline_at:
        days_until = (opportunity.deadline_at - datetime.utcnow()).days
        if days_until <= 7 and score >= 10:
            return True
    
    # Notifier si gros budget (> 50k€) et score >= 8
    if opportunity.budget_amount and opportunity.budget_amount >= 50000 and score >= 8:
        return True
    
    return False


async def fetch_source_async(source: SourceConfig, extractor: DataExtractor) -> Dict[str, Any]:
    """Récupérer les données d'une source de manière asynchrone"""
    try:
        connector = get_connector(source)
        if not connector:
            return {"source": source.name, "items": [], "error": "No connector", "raw_count": 0, "extracted_count": 0}
        
        # Fetch raw items
        raw_items = await connector.fetch()
        
        if not raw_items:
            return {
                "source": source.name,
                "items": [],
                "raw_count": 0,
                "extracted_count": 0,
                "error": None
            }
        
        # Extract structured data using extract_all (the correct method)
        extracted_items = []
        for item in raw_items:
            try:
                # extract_all is synchronous, not async
                extracted = extractor.extract_all(
                    raw_item=item,
                    source_type=source.source_type.value,
                    source_name=source.name
                )
                if extracted:
                    extracted["source_id"] = str(source.id)
                    extracted_items.append(extracted)
            except Exception as e:
                # Skip individual item errors, continue processing
                continue
        
        return {
            "source": source.name,
            "items": extracted_items,
            "raw_count": len(raw_items),
            "extracted_count": len(extracted_items),
            "error": None
        }
    except Exception as e:
        return {
            "source": source.name,
            "items": [],
            "raw_count": 0,
            "extracted_count": 0,
            "error": str(e)
        }


@celery_app.task(bind=True, name="app.workers.auto_radar_task.auto_radar_harvest")
def auto_radar_harvest(self):
    """
    Tâche automatique de récolte Radar
    Exécutée toutes les 15 minutes
    
    1. Scanne toutes les sources actives
    2. Extrait et déduplique les items
    3. Score et classe les opportunités
    4. Notifie pour les excellentes
    5. Génère un rapport
    """
    import uuid
    
    task_id = self.request.id or str(uuid.uuid4())[:8]
    logger = get_task_logger("AUTO_RADAR", task_id[:8])
    start_time = datetime.utcnow()
    
    logger.info("🚀 Démarrage de la récolte automatique Radar")
    
    db = get_db()
    report_id = str(uuid.uuid4())
    
    # Stats
    stats = {
        "sources_scanned": 0,
        "items_fetched": 0,
        "items_new": 0,
        "items_duplicate": 0,
        "opportunities_created": 0,
        "excellent": 0,
        "good": 0,
        "average": 0,
        "poor": 0,
        "notifications_sent": 0,
        "errors": []
    }
    
    try:
        # 1. Récupérer toutes les sources actives
        logger.step("Récupération des sources actives")
        sources = db.query(SourceConfig).filter(SourceConfig.is_active == True).all()
        stats["sources_scanned"] = len(sources)
        logger.info(f"📡 {len(sources)} sources actives trouvées")
        
        if not sources:
            logger.warning("Aucune source active configurée")
            return {"status": "no_sources", "stats": stats}
        
        # 2. Initialiser les outils
        logger.step("Initialisation des outils d'extraction")
        extractor = DataExtractor()
        deduplicator = Deduplicator(db)
        scoring_engine = ScoringEngine(db)
        
        # 3. Récupérer les données de toutes les sources
        logger.step("Extraction des données de toutes les sources")
        
        all_items = []
        source_results = []
        
        for i, source in enumerate(sources):
            logger.info(f"  [{i+1}/{len(sources)}] Scanning: {source.name}")
            
            try:
                # Run async fetch
                result = asyncio.get_event_loop().run_until_complete(
                    fetch_source_async(source, extractor)
                )
                
                source_results.append({
                    "name": source.name,
                    "type": source.source_type.value,
                    "fetched": result.get("raw_count", 0),
                    "extracted": result.get("extracted_count", 0),
                    "error": result.get("error")
                })
                
                if result["items"]:
                    all_items.extend(result["items"])
                    stats["items_fetched"] += len(result["items"])
                    logger.success(f"    ✓ {len(result['items'])} items extraits")
                else:
                    if result.get("error"):
                        logger.warning(f"    ⚠ Erreur: {result['error'][:50]}")
                    else:
                        logger.info(f"    ○ Aucun nouvel item")
                        
            except Exception as e:
                logger.error(f"    ✗ Erreur source {source.name}: {str(e)[:50]}")
                stats["errors"].append(f"{source.name}: {str(e)}")
        
        logger.info(f"📦 Total: {stats['items_fetched']} items récupérés")
        
        # 4. Déduplication et création des opportunités
        logger.step("Déduplication et scoring des opportunités")
        
        excellent_opportunities = []
        
        for item in all_items:
            try:
                # Extract key fields for deduplication
                title = item.get("title", "Sans titre")
                url = item.get("url_primary") or item.get("url")
                external_id = item.get("external_id")
                organization = item.get("organization")
                deadline = item.get("deadline_at")
                
                # Check duplicate using check_duplicate method
                is_dup, existing_opp, similarity = deduplicator.check_duplicate(
                    external_id=external_id or "",
                    url=url,
                    title=title,
                    organization=organization,
                    deadline=deadline
                )
                
                if is_dup:
                    stats["items_duplicate"] += 1
                    continue
                
                stats["items_new"] += 1
                
                # Generate external_id if not present
                if not external_id:
                    external_id = deduplicator.compute_hash(
                        title=title,
                        organization=organization,
                        deadline=deadline,
                        source_name=item.get("source_name")
                    )
                
                # Create opportunity
                opportunity = Opportunity(
                    id=str(uuid.uuid4()),
                    title=title[:500],
                    description=item.get("description", "")[:10000] if item.get("description") else None,
                    snippet=item.get("snippet", "")[:500] if item.get("snippet") else None,
                    url_primary=url,
                    published_at=item.get("published_at"),
                    deadline_at=deadline,
                    location_city=item.get("location_city") or item.get("city"),
                    location_region=item.get("location_region") or item.get("region"),
                    location_country=item.get("location_country") or item.get("country", "FR"),
                    budget_amount=item.get("budget_amount"),
                    budget_currency=item.get("budget_currency", "EUR"),
                    budget_hint=item.get("budget_hint"),
                    contact_email=item.get("contact_email"),
                    contact_phone=item.get("contact_phone"),
                    organization=organization,
                    source_type=SourceType(item.get("source_type", "rss")),
                    source_name=item.get("source_name"),
                    source_config_id=item.get("source_id"),
                    external_id=external_id,
                    status=OpportunityStatus.NEW,
                    category=item.get("category"),
                )
                
                # Mark potential duplicates
                if existing_opp and similarity:
                    deduplicator.mark_possible_duplicate(opportunity, existing_opp, similarity)
                
                # Score the opportunity using calculate_score
                total_score, score_breakdown = scoring_engine.calculate_score(opportunity)
                opportunity.score = total_score
                opportunity.score_breakdown = score_breakdown
                
                # Classify
                classification = classify_opportunity(opportunity.score)
                stats[classification] += 1
                stats["opportunities_created"] += 1
                
                # Check if should notify
                if should_notify(opportunity, opportunity.score):
                    excellent_opportunities.append(opportunity)
                
                db.add(opportunity)
                
            except Exception as e:
                logger.error(f"Erreur création opportunité: {str(e)[:50]}")
                stats["errors"].append(str(e))
        
        db.commit()
        
        logger.info(f"✨ {stats['opportunities_created']} nouvelles opportunités créées")
        logger.info(f"   🌟 Excellentes: {stats['excellent']}")
        logger.info(f"   ✅ Bonnes: {stats['good']}")
        logger.info(f"   📊 Moyennes: {stats['average']}")
        logger.info(f"   ⚠️ Faibles: {stats['poor']}")
        
        # 5. Notifications
        logger.step("Envoi des notifications")
        
        if excellent_opportunities:
            logger.info(f"🔔 {len(excellent_opportunities)} opportunités à notifier")
            
            try:
                # Envoyer les notifications (Discord, Slack, Email)
                send_notifications(excellent_opportunities)
                stats["notifications_sent"] = len(excellent_opportunities)
                logger.success(f"✓ {len(excellent_opportunities)} notifications envoyées")
            except Exception as e:
                logger.error(f"Erreur notifications: {str(e)}")
                stats["errors"].append(f"Notifications: {str(e)}")
        else:
            logger.info("Aucune opportunité excellente à notifier")
        
        # Créer le rapport
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        report = RadarHarvestReport(
            id=report_id,
            harvest_time=start_time,
            sources_scanned=stats["sources_scanned"],
            items_fetched=stats["items_fetched"],
            items_new=stats["items_new"],
            items_duplicate=stats["items_duplicate"],
            opportunities_created=stats["opportunities_created"],
            opportunities_excellent=stats["excellent"],
            opportunities_good=stats["good"],
            opportunities_average=stats["average"],
            opportunities_poor=stats["poor"],
            notifications_sent=stats["notifications_sent"],
            duration_seconds=duration,
            status="success",
            details={
                "sources": source_results,
                "errors": stats["errors"]
            }
        )
        db.add(report)
        db.commit()
        
        logger.success(f"🎉 Récolte terminée en {duration:.1f}s")
        logger.info(f"Rapport ID: {report_id}, Créées: {stats['opportunities_created']}, Excellentes: {stats['excellent']}")
        
        return {
            "status": "success",
            "report_id": report_id,
            "stats": stats,
            "duration_seconds": duration
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {str(e)}")
        
        # Sauvegarder le rapport d'erreur
        try:
            duration = (datetime.utcnow() - start_time).total_seconds()
            report = RadarHarvestReport(
                id=report_id,
                harvest_time=start_time,
                status="error",
                error_message=str(e),
                duration_seconds=duration,
                details={"stats": stats}
            )
            db.add(report)
            db.commit()
        except:
            pass
        
        return {"status": "error", "error": str(e), "stats": stats}
    
    finally:
        db.close()


@celery_app.task(name="app.workers.auto_radar_task.get_harvest_reports")
def get_harvest_reports(limit: int = 10):
    """Récupérer les derniers rapports de récolte"""
    db = get_db()
    try:
        reports = db.query(RadarHarvestReport)\
            .order_by(RadarHarvestReport.harvest_time.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                "id": r.id,
                "harvest_time": r.harvest_time.isoformat() if r.harvest_time else None,
                "sources_scanned": r.sources_scanned,
                "items_fetched": r.items_fetched,
                "opportunities_created": r.opportunities_created,
                "excellent": r.opportunities_excellent,
                "good": r.opportunities_good,
                "notifications_sent": r.notifications_sent,
                "duration_seconds": r.duration_seconds,
                "status": r.status
            }
            for r in reports
        ]
    finally:
        db.close()
