"""
Spotify Search Pipeline Worker
Executes search and enrichment in background
Steps: SEARCH -> ENRICH -> COMPLETE
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from celery import shared_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.spotify_search import (
    SpotifySearchJob,
    SpotifySearchResult,
    SpotifyJobStatus,
    SpotifyJobStep,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


def get_spotify_client():
    """Get initialized Spotify client."""
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            logger.warning("Spotify credentials not configured")
            return None
        
        auth_manager = SpotifyClientCredentials(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret
        )
        return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=10)
    except Exception as e:
        logger.error(f"Failed to init Spotify client: {e}")
        return None


def estimate_monthly_listeners(followers: int, popularity: int) -> int:
    """Estimate monthly listeners from followers and popularity."""
    if popularity >= 80:
        multiplier = 3.5
    elif popularity >= 70:
        multiplier = 3.0
    elif popularity >= 60:
        multiplier = 2.5
    elif popularity >= 50:
        multiplier = 2.0
    elif popularity >= 40:
        multiplier = 1.5
    else:
        multiplier = 1.2
    return int(followers * multiplier)


# ============================================================================
# MAIN PIPELINE TASK
# ============================================================================

@celery_app.task(bind=True, name="spotify.search_pipeline")
def run_spotify_search_pipeline(self, job_id: str) -> Dict[str, Any]:
    """
    Main Spotify search pipeline task.
    Executes: SEARCH -> ENRICH -> COMPLETE
    
    Args:
        job_id: UUID of the SpotifySearchJob
    
    Returns:
        Dict with status and results count
    """
    db = get_db()
    try:
        job = db.query(SpotifySearchJob).filter(
            SpotifySearchJob.id == job_id
        ).first()
        
        if not job:
            logger.error(f"Spotify search job {job_id} not found")
            return {"status": "ERROR", "message": "Job not found"}
        
        # Update job with celery task id
        job.celery_task_id = self.request.id
        job.mark_running("SEARCH")
        db.commit()
        
        logger.info(f"Starting Spotify search pipeline for job {job_id}: '{job.query}'")
        
        try:
            # Step 1: SEARCH (0-40%)
            artists = step_search(db, job)
            job.update_progress("SEARCH", 40)
            db.commit()
            
            if not artists:
                job.mark_completed(partial=True, results_count=0)
                db.commit()
                logger.warning(f"No results for query: {job.query}")
                return {"status": "PARTIAL", "results_count": 0}
            
            # Step 2: ENRICH (40-90%)
            job.update_progress("ENRICH", 45)
            db.commit()
            enriched_artists = step_enrich(db, job, artists)
            job.update_progress("ENRICH", 90)
            db.commit()
            
            # Step 3: COMPLETE (90-100%)
            job.update_progress("COMPLETE", 95)
            db.commit()
            results_count = step_complete(db, job, enriched_artists)
            
            # Mark done
            partial = results_count < len(artists)
            job.mark_completed(partial=partial, results_count=results_count)
            db.commit()
            
            logger.info(f"Spotify search completed for job {job_id}: {results_count} results")
            
            return {
                "status": "DONE" if not partial else "PARTIAL",
                "results_count": results_count,
                "job_id": str(job_id),
            }
            
        except Exception as e:
            logger.error(f"Pipeline error for job {job_id}: {e}")
            job.mark_failed("PIPELINE_ERROR", str(e))
            db.commit()
            return {"status": "ERROR", "message": str(e)}
            
    except Exception as e:
        logger.error(f"Critical error in Spotify search pipeline: {e}")
        return {"status": "ERROR", "message": str(e)}
    finally:
        db.close()


# ============================================================================
# STEP 1: SEARCH
# ============================================================================

def step_search(db: Session, job: SpotifySearchJob) -> List[Dict[str, Any]]:
    """
    Search Spotify API for artists matching query.
    """
    logger.info(f"[SEARCH] Searching Spotify for: {job.query}")
    
    client = get_spotify_client()
    if not client:
        logger.error("Spotify client not available")
        return []
    
    try:
        results = client.search(
            q=f'artist:{job.query}',
            type='artist',
            limit=job.limit or 10
        )
        
        artists = []
        for item in results.get('artists', {}).get('items', []):
            artists.append({
                'spotify_id': item['id'],
                'name': item['name'],
                'followers': item.get('followers', {}).get('total', 0),
                'popularity': item.get('popularity', 0),
                'genres': item.get('genres', []),
                'image_url': item['images'][0]['url'] if item.get('images') else None,
                'spotify_url': item.get('external_urls', {}).get('spotify'),
            })
        
        logger.info(f"[SEARCH] Found {len(artists)} artists for '{job.query}'")
        return artists
        
    except Exception as e:
        logger.error(f"[SEARCH] Error searching Spotify: {e}")
        return []


# ============================================================================
# STEP 2: ENRICH
# ============================================================================

def step_enrich(db: Session, job: SpotifySearchJob, artists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Collect published Spotify listeners and optional complementary artist data.
    """
    logger.info(f"[ENRICH] Enriching {len(artists)} artists")
    
    enriched = []
    enrichment_service = None
    
    # Try to init enrichment service
    try:
        from app.enrichment.config import EnrichmentConfig
        from app.enrichment.service import ArtistEnrichmentService
        
        if settings.viberate_enabled:
            enrichment_config = EnrichmentConfig(
                viberate_enabled=settings.viberate_enabled,
                viberate_request_delay=settings.viberate_request_delay
            )
            enrichment_service = ArtistEnrichmentService(
                config=enrichment_config,
                spotify_client_id=settings.spotify_client_id,
                spotify_client_secret=settings.spotify_client_secret
            )
            logger.info("[ENRICH] Viberate enrichment available")
    except Exception as e:
        logger.debug(f"[ENRICH] Viberate not available: {e}")
    
    for i, artist in enumerate(artists):
        try:
            from app.enrichment.providers.spotify_scraper import scrape_spotify_artist
            observed = scrape_spotify_artist(artist['spotify_id'])
            monthly_listeners = observed.get('monthly_listeners') if observed else None
            source = "spotify_public" if monthly_listeners is not None else "unavailable"
            label = None
            management = None
            social_stats = None
            
            # Try Viberate enrichment
            if enrichment_service:
                try:
                    enriched_data = asyncio.run(
                        enrichment_service.enrich(artist['spotify_id'], force_refresh=False)
                    )
                    
                    if enriched_data.labels and enriched_data.labels.principal:
                        label = enriched_data.labels.principal
                    
                    if enriched_data.management and enriched_data.management.value:
                        management = enriched_data.management.value
                    
                    if enriched_data.social_stats:
                        social_stats = {
                            'spotify_followers': enriched_data.social_stats.spotify_followers,
                            'youtube_subscribers': enriched_data.social_stats.youtube_subscribers,
                            'instagram_followers': enriched_data.social_stats.instagram_followers,
                            'tiktok_followers': enriched_data.social_stats.tiktok_followers,
                        }
                    
                    logger.info(f"[ENRICH] {artist['name']}: {monthly_listeners} listeners ({source})")
                    
                except Exception as e:
                    logger.debug(f"[ENRICH] Viberate failed for {artist['name']}: {e}")
            
            artist['monthly_listeners'] = monthly_listeners
            artist['monthly_listeners_source'] = source
            artist['label'] = label
            artist['management'] = management
            artist['social_stats'] = social_stats
            
            enriched.append(artist)
            
            # Update progress
            progress = 45 + int((i + 1) / len(artists) * 45)
            job.update_progress("ENRICH", progress)
            db.commit()
            
        except Exception as e:
            logger.error(f"[ENRICH] Error enriching {artist['name']}: {e}")
            # An enrichment failure must not manufacture listener observations.
            artist['monthly_listeners'] = None
            artist['monthly_listeners_source'] = "unavailable"
            enriched.append(artist)
    
    return enriched


# ============================================================================
# STEP 3: COMPLETE
# ============================================================================

def step_complete(db: Session, job: SpotifySearchJob, artists: List[Dict[str, Any]]) -> int:
    """
    Save enriched results to database.
    """
    logger.info(f"[COMPLETE] Saving {len(artists)} results")
    
    count = 0
    for rank, artist in enumerate(artists):
        try:
            result = SpotifySearchResult(
                job_id=job.id,
                spotify_id=artist['spotify_id'],
                name=artist['name'],
                image_url=artist.get('image_url'),
                spotify_url=artist.get('spotify_url'),
                followers=artist.get('followers', 0),
                popularity=artist.get('popularity', 0),
                monthly_listeners=artist.get('monthly_listeners'),
                monthly_listeners_source=artist.get('monthly_listeners_source', 'unavailable'),
                genres=artist.get('genres', []),
                label=artist.get('label'),
                management=artist.get('management'),
                social_stats=artist.get('social_stats'),
                rank=rank,
            )
            db.add(result)
            count += 1
        except Exception as e:
            logger.error(f"[COMPLETE] Error saving {artist['name']}: {e}")
    
    db.commit()
    logger.info(f"[COMPLETE] Saved {count} results for job {job.id}")
    
    return count
