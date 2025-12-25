"""
Celery tasks for dossier building and web enrichment.
Pipeline 2 + Pipeline 3 implementation.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from celery import shared_task

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.opportunity import Opportunity
from app.db.models.dossier import Dossier, DossierState
from app.services.dossier_builder import DossierBuilderService
from app.services.web_enrichment import WebEnrichmentService

logger = logging.getLogger(__name__)


def get_db():
    """Get database session"""
    return SessionLocal()


# ============================================================================
# PIPELINE 2: DOSSIER BUILDER (GPT)
# ============================================================================

@celery_app.task(bind=True, max_retries=1, queue='dossier_builder_gpt')
def build_dossier_task(
    self,
    opportunity_id: str,
    force_rebuild: bool = False,
    auto_enrich: bool = True
):
    """
    Build a dossier for an opportunity using GPT.
    
    Args:
        opportunity_id: UUID of the opportunity
        force_rebuild: Force rebuild even if dossier exists
        auto_enrich: Automatically trigger web enrichment if fields are missing
    
    Returns:
        Dict with dossier info and whether enrichment is needed
    """
    db = get_db()
    
    try:
        logger.info(f"Building dossier for opportunity {opportunity_id}")
        
        service = DossierBuilderService(db)
        
        dossier, needs_enrichment = service.build_dossier(
            opportunity_id=UUID(opportunity_id),
            force_rebuild=force_rebuild
        )
        
        result = {
            "dossier_id": str(dossier.id),
            "opportunity_id": opportunity_id,
            "state": dossier.state.value,
            "confidence_plus": dossier.confidence_plus,
            "score_final": dossier.score_final,
            "missing_fields": dossier.missing_fields,
            "quality_flags": dossier.quality_flags,
            "needs_enrichment": needs_enrichment,
        }
        
        # Auto-trigger web enrichment if needed
        if needs_enrichment and auto_enrich:
            logger.info(f"Auto-triggering web enrichment for dossier {dossier.id}")
            web_enrich_task.delay(
                dossier_id=str(dossier.id),
                target_fields=dossier.missing_fields,
                auto_merge=True
            )
            result["enrichment_triggered"] = True
        
        db.close()
        return result
        
    except Exception as e:
        logger.error(f"Error building dossier for {opportunity_id}: {e}")
        db.close()
        
        # Retry if appropriate
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        raise


@celery_app.task(bind=True, max_retries=0, queue='dossier_builder_gpt')
def batch_build_dossiers_task(
    self,
    opportunity_ids: List[str],
    force_rebuild: bool = False,
    auto_enrich: bool = True
):
    """
    Build dossiers for multiple opportunities.
    
    Args:
        opportunity_ids: List of opportunity UUIDs
        force_rebuild: Force rebuild even if dossiers exist
        auto_enrich: Auto-trigger web enrichment if needed
    """
    results = {
        "total": len(opportunity_ids),
        "success": 0,
        "failed": 0,
        "enrichment_needed": 0,
        "details": []
    }
    
    for opp_id in opportunity_ids:
        try:
            # Queue individual tasks
            build_dossier_task.delay(
                opportunity_id=opp_id,
                force_rebuild=force_rebuild,
                auto_enrich=auto_enrich
            )
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "opportunity_id": opp_id,
                "error": str(e)[:200]
            })
    
    return results


@celery_app.task(bind=True, queue='dossier_builder_gpt')
def auto_build_top_dossiers_task(
    self,
    score_threshold: int = 70,
    limit: int = 20,
    force_rebuild: bool = False
):
    """
    Automatically build dossiers for top-scoring opportunities.
    
    Args:
        score_threshold: Minimum score to consider
        limit: Maximum number of dossiers to build
        force_rebuild: Force rebuild existing dossiers
    """
    db = get_db()
    
    try:
        # Find opportunities with high scores that don't have dossiers
        query = db.query(Opportunity).filter(
            Opportunity.score >= score_threshold
        )
        
        if not force_rebuild:
            # Exclude opportunities that already have ready dossiers
            existing_dossier_ids = db.query(Dossier.opportunity_id).filter(
                Dossier.state == DossierState.READY
            ).subquery()
            
            query = query.filter(
                ~Opportunity.id.in_(existing_dossier_ids)
            )
        
        opportunities = query.order_by(
            Opportunity.score.desc()
        ).limit(limit).all()
        
        db.close()
        
        if not opportunities:
            logger.info("No opportunities found for auto-dossier building")
            return {"total": 0, "queued": 0}
        
        # Queue dossier builds
        queued = 0
        for opp in opportunities:
            build_dossier_task.delay(
                opportunity_id=str(opp.id),
                force_rebuild=force_rebuild,
                auto_enrich=True
            )
            queued += 1
        
        logger.info(f"Queued {queued} dossier builds for top opportunities")
        
        return {
            "total": len(opportunities),
            "queued": queued,
            "threshold": score_threshold
        }
        
    except Exception as e:
        logger.error(f"Error in auto_build_top_dossiers: {e}")
        db.close()
        raise


# ============================================================================
# PIPELINE 3: WEB ENRICHMENT
# ============================================================================

@celery_app.task(bind=True, max_retries=2, queue='web_enrichment')
def web_enrich_task(
    self,
    dossier_id: str,
    target_fields: Optional[List[str]] = None,
    auto_merge: bool = True
):
    """
    Run web enrichment for a dossier.
    
    Args:
        dossier_id: UUID of the dossier
        target_fields: Specific fields to look for (or use dossier.missing_fields)
        auto_merge: Automatically merge results with GPT
    
    Returns:
        Dict with enrichment results
    """
    db = get_db()
    
    try:
        logger.info(f"Starting web enrichment for dossier {dossier_id}")
        
        dossier = db.query(Dossier).filter(
            Dossier.id == dossier_id
        ).first()
        
        if not dossier:
            raise ValueError(f"Dossier not found: {dossier_id}")
        
        service = WebEnrichmentService(db)
        
        # Run enrichment
        results = service.run_enrichment_sync(
            dossier=dossier,
            target_fields=target_fields
        )
        
        response = {
            "dossier_id": dossier_id,
            "results_count": len(results),
            "fields_found": list(set(r["field_key"] for r in results)),
            "results": results,
        }
        
        # Auto-merge with GPT if we found results
        if results and auto_merge:
            logger.info(f"Auto-merging enrichment results for dossier {dossier_id}")
            merge_enrichment_task.delay(
                dossier_id=dossier_id,
                enrichment_results=results
            )
            response["merge_triggered"] = True
        
        db.close()
        return response
        
    except Exception as e:
        logger.error(f"Error in web enrichment for {dossier_id}: {e}")
        db.close()
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120)
        raise


@celery_app.task(bind=True, max_retries=1, queue='dossier_builder_gpt')
def merge_enrichment_task(
    self,
    dossier_id: str,
    enrichment_results: List[dict]
):
    """
    Merge web enrichment results into a dossier using GPT.
    
    Args:
        dossier_id: UUID of the dossier
        enrichment_results: Results from web enrichment
    """
    db = get_db()
    
    try:
        logger.info(f"Merging enrichment results for dossier {dossier_id}")
        
        service = DossierBuilderService(db)
        
        dossier = service.merge_after_enrichment(
            dossier_id=UUID(dossier_id),
            enrichment_results=enrichment_results
        )
        
        result = {
            "dossier_id": dossier_id,
            "state": dossier.state.value,
            "confidence_plus": dossier.confidence_plus,
            "score_final": dossier.score_final,
            "remaining_missing": dossier.missing_fields,
            "quality_flags": dossier.quality_flags,
        }
        
        db.close()
        return result
        
    except Exception as e:
        logger.error(f"Error merging enrichment for {dossier_id}: {e}")
        db.close()
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        raise


# ============================================================================
# FULL PIPELINE: BUILD + ENRICH + MERGE
# ============================================================================

@celery_app.task(bind=True, queue='dossier_builder_gpt')
def full_dossier_pipeline_task(
    self,
    opportunity_id: str,
    force_rebuild: bool = False
):
    """
    Run the full dossier pipeline: build -> enrich (if needed) -> merge.
    This is a synchronous version that waits for each step.
    
    Args:
        opportunity_id: UUID of the opportunity
        force_rebuild: Force rebuild even if dossier exists
    """
    db = get_db()
    
    try:
        logger.info(f"Starting full dossier pipeline for opportunity {opportunity_id}")
        
        # Step 1: Build dossier
        builder_service = DossierBuilderService(db)
        dossier, needs_enrichment = builder_service.build_dossier(
            opportunity_id=UUID(opportunity_id),
            force_rebuild=force_rebuild
        )
        
        result = {
            "dossier_id": str(dossier.id),
            "opportunity_id": opportunity_id,
            "steps_completed": ["build"],
            "final_state": dossier.state.value,
        }
        
        # Step 2: Web enrichment if needed
        if needs_enrichment and dossier.missing_fields:
            logger.info(f"Pipeline: Starting web enrichment for missing fields: {dossier.missing_fields}")
            
            enrichment_service = WebEnrichmentService(db)
            enrichment_results = enrichment_service.run_enrichment_sync(
                dossier=dossier,
                target_fields=dossier.missing_fields
            )
            
            result["steps_completed"].append("enrich")
            result["enrichment_results"] = len(enrichment_results)
            
            # Step 3: Merge if we got results
            if enrichment_results:
                logger.info(f"Pipeline: Merging {len(enrichment_results)} enrichment results")
                
                dossier = builder_service.merge_after_enrichment(
                    dossier_id=dossier.id,
                    enrichment_results=enrichment_results
                )
                
                result["steps_completed"].append("merge")
        
        result["final_state"] = dossier.state.value
        result["confidence_plus"] = dossier.confidence_plus
        result["score_final"] = dossier.score_final
        result["remaining_missing"] = dossier.missing_fields
        result["quality_flags"] = dossier.quality_flags
        
        db.close()
        
        logger.info(f"Full pipeline completed for opportunity {opportunity_id}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in full dossier pipeline for {opportunity_id}: {e}")
        db.close()
        raise
