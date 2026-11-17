"""
API Endpoints for Artist Enrichment
Uses Viberate web scraping for social stats
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user
from app.db.models.user import User
from app.core.config import settings
from app.enrichment.config import EnrichmentConfig
from app.enrichment.service import ArtistEnrichmentService
from app.enrichment.models import (
    EnrichedArtistData,
    EnrichmentRequest,
    BatchEnrichmentRequest,
    EnrichmentStatus
)

router = APIRouter(prefix="/enrichment", tags=["enrichment"])
logger = logging.getLogger(__name__)

# Initialize service (singleton) - using Viberate scraping
enrichment_config = EnrichmentConfig(
    viberate_enabled=getattr(settings, 'viberate_enabled', True),
    viberate_request_delay=getattr(settings, 'viberate_request_delay', 1.5)
)

enrichment_service = ArtistEnrichmentService(
    config=enrichment_config,
    spotify_client_id=settings.spotify_client_id,
    spotify_client_secret=settings.spotify_client_secret
)


@router.post("/artists/enrich", response_model=EnrichedArtistData)
async def enrich_artist(
    request: EnrichmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enrich artist data from all sources
    
    **MVP Endpoint**
    
    Input:
    - spotify_artist_id OR spotify_url
    - force_refresh (optional)
    
    Output:
    - Complete enriched data with monthly listeners, labels, management, etc.
    """
    if not request.spotify_artist_id and not request.spotify_url:
        raise HTTPException(400, "Provide spotify_artist_id or spotify_url")
    
    input_str = request.spotify_artist_id or request.spotify_url
    
    try:
        result = await enrichment_service.enrich(input_str, request.force_refresh)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        raise HTTPException(500, "Enrichment failed")


@router.get("/artists/{artist_id}", response_model=EnrichedArtistData)
async def get_enriched_artist(
    artist_id: str,
    refresh: bool = Query(False, description="Force refresh from sources"),
    current_user: User = Depends(get_current_user)
):
    """
    Get enriched artist data (with optional refresh)
    
    **Legacy unavailable endpoint - GET variant**
    """
    try:
        result = await enrichment_service.enrich(artist_id, force_refresh=refresh)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error getting artist {artist_id}: {e}")
        raise HTTPException(500, "Failed to get artist data")


@router.post("/artists/{artist_id}/refresh", response_model=EnrichedArtistData)
async def refresh_artist(
    artist_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Force refresh artist data (bypasses cache)
    
    **Legacy unavailable endpoint - Explicit refresh**
    """
    try:
        result = await enrichment_service.enrich(artist_id, force_refresh=True)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error refreshing artist {artist_id}: {e}")
        raise HTTPException(500, "Refresh failed")


@router.post("/artists/batch/enrich", response_model=List[EnrichedArtistData])
async def enrich_artists_batch(
    request: BatchEnrichmentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Enrich multiple artists in batch
    
    **Legacy unavailable endpoint - Batch processing**
    
    For large batches, consider using background jobs:
    - Returns immediately with job ID
    - Poll status endpoint
    - Retrieve results when ready
    """
    if len(request.artist_ids) > 50:
        raise HTTPException(400, "Maximum 50 artists per batch")
    
    try:
        results = await enrichment_service.enrich_batch(
            request.artist_ids,
            request.force_refresh
        )
        return results
    except Exception as e:
        logger.error(f"Batch enrichment error: {e}")
        raise HTTPException(500, "Batch enrichment failed")


@router.get("/metrics")
async def get_enrichment_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Get enrichment service metrics
    
    **Legacy unavailable endpoint - Monitoring**
    
    Returns:
    - Success/failure rates per provider
    - Cache hit rates
    - Average latency
    - Circuit breaker states
    """
    return enrichment_service.get_metrics()


# =====  BACKGROUND JOB ENDPOINTS (for production batch) =====

@router.post("/jobs/batch/start", include_in_schema=False)
async def start_batch_job(
    request: BatchEnrichmentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start background batch enrichment job
    
    **Legacy unavailable endpoint - Async batch**
    
    Returns job_id immediately, process in background
    """
    # TODO: Implement with Celery/Redis
    # job_id = str(uuid.uuid4())
    # background_tasks.add_task(process_batch_enrichment, job_id, request)
    raise HTTPException(501, "Background jobs not implemented - use /artists/batch/enrich")


@router.get("/jobs/{job_id}/status", include_in_schema=False)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of batch enrichment job
    
    **Legacy unavailable endpoint - Job tracking**
    """
    # TODO: Query job status from Redis/DB
    raise HTTPException(501, "Background jobs not implemented")


@router.get("/jobs/{job_id}/results", include_in_schema=False)
async def get_job_results(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get results of completed batch job
    
    **Legacy unavailable endpoint - Results retrieval**
    """
    # TODO: Retrieve results from storage
    raise HTTPException(501, "Background jobs not implemented")
