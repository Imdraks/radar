"""
Discovery V3 - Enrichment Pipeline Worker
Orchestrates the 4-step enrichment process: MATCH -> VIBERATE -> SPOTIFY -> COMPUTE
"""
import asyncio
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.discovery import (
    DiscoveryArtist,
    DiscoverySnapshot,
    DiscoveryComputedMetrics,
    DiscoveryEnrichmentJob,
    DataQuality,
    SnapshotStatus,
    JobStatus,
    JobStep,
)
from app.enrichment.service import ArtistEnrichmentService
from app.enrichment.config import EnrichmentConfig
from app.enrichment.providers.viberate import ViberateProvider
from app.enrichment.providers.spotify import SpotifyProvider
from app.core.config import settings
from app.db.models.discovery import DiscoveryCandidate

logger = logging.getLogger(__name__)

# TTL Configuration
TTL_VIBERATE_HOURS = 24
TTL_SPOTIFY_HOURS = 12
TTL_COMPUTE_HOURS = 24

# Rate limiting
RATE_LIMIT_VIBERATE = "1/2s"  # 1 request per 2 seconds
RATE_LIMIT_SPOTIFY = "100/m"  # 100 requests per minute


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


def normalize_artist_name(name: str) -> str:
    """Normalize artist name for deduplication."""
    name = name.lower().strip()
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_viberate_artist_slug(url: str) -> Optional[str]:
    """Extract artist slug from Viberate URL."""
    match = re.search(r'viberate\.com/artist/([^/?#]+)', url)
    return match.group(1) if match else None


def extract_spotify_artist_id(url_or_id: str) -> Optional[str]:
    """Extract Spotify artist ID from URL or validate ID."""
    # If it's already an ID (22 chars alphanumeric)
    if re.match(r'^[a-zA-Z0-9]{22}$', url_or_id):
        return url_or_id
    # Extract from URL
    match = re.search(r'artist/([a-zA-Z0-9]{22})', url_or_id)
    return match.group(1) if match else None


def _resolve_spotify_id_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve artist name → metadata + Spotify ID.
    Strategy: 
    1. Deezer API (free, reliable) for name/image/fans
    2. Google search to find Spotify artist ID
    3. Spotify page scraping for monthly listeners (if ID found)
    """
    result: Dict[str, Any] = {
        "spotify_artist_id": None,
        "canonical_name": name,
        "image_url": None,
        "monthly_listeners": 0,
        "deezer_id": None,
        "deezer_fans": 0,
        "genres": [],
    }

    # 1. Deezer API — reliable name resolution + fans + image
    try:
        from app.enrichment.providers.deezer import search_deezer_artist
        dz_data = search_deezer_artist(name)
        if dz_data:
            result["canonical_name"] = dz_data.get("name", name)
            result["image_url"] = dz_data.get("image_url")
            result["deezer_id"] = dz_data.get("deezer_id")
            result["deezer_fans"] = dz_data.get("deezer_fans", 0)
            logger.info(f"Deezer resolved '{name}' → {result['canonical_name']} (fans: {result['deezer_fans']})")
    except Exception as e:
        logger.warning(f"Deezer search failed for '{name}': {e}")

    # 2. Find Spotify ID via Google
    try:
        from app.enrichment.providers.spotify_scraper import search_spotify_id_by_name
        spotify_id = search_spotify_id_by_name(result["canonical_name"] or name)
        if spotify_id:
            result["spotify_artist_id"] = spotify_id
            logger.info(f"Found Spotify ID for '{name}': {spotify_id}")
    except Exception as e:
        logger.warning(f"Spotify ID search failed for '{name}': {e}")

    # 3. If we found a Spotify ID, scrape the page for monthly listeners
    if result["spotify_artist_id"]:
        try:
            from app.enrichment.providers.spotify_scraper import scrape_spotify_artist
            sp_data = scrape_spotify_artist(result["spotify_artist_id"])
            if sp_data:
                result["monthly_listeners"] = sp_data.get("monthly_listeners", 0)
                if sp_data.get("image_url") and not result["image_url"]:
                    result["image_url"] = sp_data["image_url"]
                logger.info(f"Spotify scrape: ml={result['monthly_listeners']}")
        except Exception as e:
            logger.warning(f"Spotify scrape failed: {e}")

    if not result["deezer_fans"] and not result["spotify_artist_id"]:
        logger.error(f"Could not resolve artist '{name}' via any source")
        return None

    return result


# ============================================================================
# MAIN PIPELINE TASK
# ============================================================================

@celery_app.task(bind=True, name="discovery.enrichment_pipeline", acks_late=True, reject_on_worker_lost=True, max_retries=3)
def run_enrichment_pipeline(self, job_id: str) -> Dict[str, Any]:
    """
    Main enrichment pipeline task.
    Executes 4 steps: MATCH -> VIBERATE -> SPOTIFY -> COMPUTE
    
    Args:
        job_id: UUID of the EnrichmentJob
    
    Returns:
        Dict with status and artist_id
    """
    db = get_db()
    try:
        job = db.query(DiscoveryEnrichmentJob).filter(
            DiscoveryEnrichmentJob.id == job_id
        ).first()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"status": "ERROR", "message": "Job not found"}
        
        if job.status in {"DONE", "PARTIAL"}:
            return {"status": job.status, "artist_id": str(job.artist_id), "job_id": job_id}

        # Update job with celery task id
        job.celery_task_id = self.request.id
        job.mark_running("MATCH")
        db.commit()
        
        logger.info(f"Starting enrichment pipeline for job {job_id}")
        
        try:
            # Step 1: MATCH (0-25%)
            artist_id = step_match(db, job)
            job.artist_id = artist_id
            job.update_progress("MATCH", 25)
            db.commit()
            
            # Step 2: VIBERATE (25-50%)
            job.update_progress("VIBERATE", 30)
            db.commit()
            viberate_ok = step_viberate(db, job)
            job.update_progress("VIBERATE", 50)
            db.commit()
            
            # Step 3: SPOTIFY (50-75%)
            job.update_progress("SPOTIFY", 55)
            db.commit()
            spotify_ok = step_spotify(db, job)
            job.update_progress("SPOTIFY", 75)
            db.commit()
            
            # Step 4: COMPUTE (75-100%)
            job.update_progress("COMPUTE", 80)
            db.commit()
            step_compute(db, job, viberate_ok, spotify_ok)
            
            # Generate discovery candidates immediately for feed display
            _generate_candidates_for_artist(db, job)
            
            # Trigger recommendation generation for this workspace
            from app.workers.discovery_scheduler import generate_recommendations_for_workspace
            generate_recommendations_for_workspace.delay(job.workspace_id)
            
            # Sync to artist_analyses for frontend display
            _sync_to_artist_analyses(db, job)
            
            # Mark completed
            partial = not (viberate_ok and spotify_ok)
            job.mark_completed(partial=partial)
            db.commit()
            
            logger.info(f"Enrichment pipeline completed for job {job_id}, artist {artist_id}")
            
            return {
                "status": "DONE" if not partial else "PARTIAL",
                "artist_id": str(artist_id),
                "job_id": str(job_id),
            }
            
        except Exception as e:
            logger.error(f"Pipeline error for job {job_id}: {e}")
            error_code = "PIPELINE_ERROR"
            error_message = str(e)
            
            # Categorize error
            if "429" in str(e) or "rate limit" in str(e).lower():
                error_code = "RATE_LIMITED"
                error_message = "Limite atteinte, réessayez plus tard"
            elif "timeout" in str(e).lower():
                error_code = "TIMEOUT"
                error_message = "Délai dépassé"
            elif "not found" in str(e).lower():
                error_code = "NOT_FOUND"
                error_message = "Artiste non trouvé"
            elif "parser" in str(e).lower():
                error_code = "PARSER_CHANGED"
                error_message = "Page modifiée"
            
            db.rollback()
            job = db.query(DiscoveryEnrichmentJob).filter(DiscoveryEnrichmentJob.id == job_id).one()
            if error_code in {"RATE_LIMITED", "TIMEOUT"} and self.request.retries < self.max_retries:
                job.status = "QUEUED"
                job.error_code = error_code
                job.error_message = error_message
                db.commit()
                raise self.retry(exc=e, countdown=min(300, 30 * 2 ** self.request.retries))
            job.mark_failed(error_code, error_message)
            db.commit()
            raise
            
    except Exception as e:
        logger.error(f"Fatal error in pipeline: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# STEP 1: MATCH (Identity Resolution)
# ============================================================================

def step_match(db: Session, job: DiscoveryEnrichmentJob) -> UUID:
    """
    Step 1: Identity resolution and deduplication.
    
    - If VIBERATE_URL: extract canonical name from URL
    - If SPOTIFY_URL: extract spotifyArtistId
    - If NAME: search internal index, return existing or create new
    
    Returns: artist_id (UUID)
    """
    logger.info(f"Step MATCH for job {job.id}")
    
    workspace_id = job.workspace_id
    input_type = job.input_type
    input_value = job.input_value
    
    canonical_name = None
    normalized_name = None
    viberate_url = None
    spotify_artist_id = None
    
    if input_type == "VIBERATE_URL":
        viberate_url = input_value
        # Extract artist name from URL slug
        slug = extract_viberate_artist_slug(input_value)
        if slug:
            canonical_name = slug.replace("-", " ").title()
            normalized_name = normalize_artist_name(canonical_name)
        else:
            raise ValueError(f"Invalid Viberate URL: {input_value}")
            
    elif input_type == "SPOTIFY_URL":
        spotify_artist_id = extract_spotify_artist_id(input_value)
        if not spotify_artist_id:
            raise ValueError(f"Invalid Spotify URL/ID: {input_value}")
        # Resolve name by scraping the Spotify artist page
        try:
            from app.enrichment.providers.spotify_scraper import scrape_spotify_artist
            sp_data = scrape_spotify_artist(spotify_artist_id)
            if sp_data and sp_data.get("name"):
                canonical_name = sp_data["name"]
            else:
                canonical_name = f"spotify:{spotify_artist_id}"
        except Exception as e:
            logger.warning(f"Could not resolve Spotify ID {spotify_artist_id}: {e}")
            canonical_name = f"spotify:{spotify_artist_id}"
        normalized_name = normalize_artist_name(canonical_name)
        logger.info(f"Spotify URL resolved to: {canonical_name} ({spotify_artist_id})")
        
    elif input_type == "NAME":
        canonical_name = input_value.strip()
        normalized_name = normalize_artist_name(canonical_name)
        # Resolve Spotify ID from name
        sp_info = _resolve_spotify_id_by_name(canonical_name)
        if sp_info:
            spotify_artist_id = sp_info["spotify_artist_id"]
            canonical_name = sp_info["canonical_name"]
            normalized_name = normalize_artist_name(canonical_name)
    else:
        raise ValueError(f"Unknown input type: {input_type}")
    
    # Check for existing artist in workspace (anti-doublon)
    existing = None
    
    if spotify_artist_id:
        existing = db.query(DiscoveryArtist).filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.spotify_artist_id == spotify_artist_id,
            DiscoveryArtist.is_deleted == False,
        ).first()
    
    if not existing and normalized_name:
        existing = db.query(DiscoveryArtist).filter(
            DiscoveryArtist.workspace_id == workspace_id,
            DiscoveryArtist.normalized_name == normalized_name,
            DiscoveryArtist.is_deleted == False,
        ).first()
    
    if existing:
        logger.info(f"Found existing artist: {existing.id}")
        # Update links if we have new info
        if viberate_url and not existing.viberate_url:
            existing.viberate_url = viberate_url
        if spotify_artist_id and not existing.spotify_artist_id:
            existing.spotify_artist_id = spotify_artist_id
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing.id
    
    # Create new artist
    artist = DiscoveryArtist(
        workspace_id=workspace_id,
        canonical_name=canonical_name,
        normalized_name=normalized_name,
        viberate_url=viberate_url,
        spotify_artist_id=spotify_artist_id,
        data_quality="LOW",
    )
    db.add(artist)
    db.commit()
    db.refresh(artist)
    
    logger.info(f"Created new artist: {artist.id}")
    return artist.id


# ============================================================================
# STEP 2: VIBERATE FETCH + PARSE
# ============================================================================

def step_viberate(db: Session, job: DiscoveryEnrichmentJob) -> bool:
    """
    Step 2: Fetch and parse Viberate data.
    
    Returns: True if successful, False if failed/partial
    """
    logger.info(f"Step VIBERATE for job {job.id}")
    
    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == job.artist_id
    ).first()
    
    if not artist:
        raise ValueError(f"Artist {job.artist_id} not found")
    
    # Check if we have a fresh snapshot
    existing_snapshot = db.query(DiscoverySnapshot).filter(
        DiscoverySnapshot.artist_id == artist.id,
        DiscoverySnapshot.source == "VIBERATE",
        DiscoverySnapshot.status == "OK",
        DiscoverySnapshot.ttl_expires_at > datetime.utcnow(),
    ).first()
    
    if existing_snapshot and not job.input_type == "VIBERATE_URL":
        logger.info(f"Using cached Viberate snapshot for {artist.id}")
        return True
    
    # Need Viberate URL
    if not artist.viberate_url:
        # Try to search Viberate by name
        logger.warning(f"No Viberate URL for artist {artist.id}, trying search")
        # For now, skip Viberate if no URL
        snapshot = DiscoverySnapshot(
            artist_id=artist.id,
            source="VIBERATE",
            status="PARTIAL",
            error_code="NO_URL",
            error_message="No Viberate URL available",
            ttl_expires_at=datetime.utcnow() + timedelta(hours=1),
            parser_version="v3.0",
        )
        db.add(snapshot)
        db.commit()
        return False
    
    try:
        # Initialize Viberate provider
        config = EnrichmentConfig()
        viberate = ViberateProvider(config, cache_client=None)
        
        # Fetch data (sync wrapper for async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            viberate_data = loop.run_until_complete(
                viberate.get(artist.spotify_artist_id or "", artist_name=artist.canonical_name, force_refresh=True)
            )
        finally:
            loop.close()
        
        if not viberate_data:
            raise ValueError("Empty response from Viberate")
        
        # Store snapshot
        snapshot = DiscoverySnapshot(
            artist_id=artist.id,
            source="VIBERATE",
            status="OK",
            raw_payload=viberate_data,
            ttl_expires_at=datetime.utcnow() + timedelta(hours=TTL_VIBERATE_HOURS),
            parser_version="v3.0",
        )
        db.add(snapshot)
        
        # Update artist with extracted data
        if viberate_data.get("name"):
            artist.canonical_name = viberate_data["name"]
            artist.normalized_name = normalize_artist_name(viberate_data["name"])
        if viberate_data.get("image_url"):
            artist.image_url = viberate_data["image_url"]
        if viberate_data.get("instagram_url"):
            artist.instagram_url = viberate_data["instagram_url"]
        if viberate_data.get("tiktok_url"):
            artist.tiktok_url = viberate_data["tiktok_url"]
        if viberate_data.get("youtube_url"):
            artist.youtube_url = viberate_data["youtube_url"]
        if viberate_data.get("spotify_id"):
            artist.spotify_artist_id = viberate_data["spotify_id"]
        
        artist.last_enriched_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Viberate fetch successful for {artist.id}")
        return True
        
    except Exception as e:
        logger.error(f"Viberate fetch error for {artist.id}: {e}")
        
        # Store failed snapshot
        snapshot = DiscoverySnapshot(
            artist_id=artist.id,
            source="VIBERATE",
            status="FAILED",
            error_code="FETCH_ERROR",
            error_message=str(e)[:500],
            ttl_expires_at=datetime.utcnow() + timedelta(hours=1),
            parser_version="v3.0",
        )
        db.add(snapshot)
        db.commit()
        return False


# ============================================================================
# STEP 3: SPOTIFY FETCH + PARSE
# ============================================================================

def step_spotify(db: Session, job: DiscoveryEnrichmentJob) -> bool:
    """
    Step 3: Fetch and parse Spotify data.
    Uses spotipy directly for richer data (artist + top tracks).
    
    Returns: True if successful, False if failed/partial
    """
    logger.info(f"Step SPOTIFY for job {job.id}")
    
    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == job.artist_id
    ).first()
    
    if not artist:
        raise ValueError(f"Artist {job.artist_id} not found")
    
    # Check for fresh snapshot
    existing_snapshot = db.query(DiscoverySnapshot).filter(
        DiscoverySnapshot.artist_id == artist.id,
        DiscoverySnapshot.source == "SPOTIFY",
        DiscoverySnapshot.status == "OK",
        DiscoverySnapshot.parser_version == "v5.0-public-http",
        DiscoverySnapshot.ttl_expires_at > datetime.utcnow(),
    ).first()
    
    if existing_snapshot and (existing_snapshot.raw_payload or {}).get("monthly_listeners") is not None:
        logger.info(f"Using cached Spotify snapshot for {artist.id}")
        return True
    
    spotify_data: Dict[str, Any] = {}
    
    # --- Source 1: Spotify web scraping (monthly listeners, name, image) ---
    if artist.spotify_artist_id:
        try:
            from app.enrichment.providers.spotify_scraper import scrape_spotify_artist
            sp_scraped = scrape_spotify_artist(artist.spotify_artist_id)
            if sp_scraped:
                spotify_data.update(sp_scraped)
                logger.info(f"Spotify scrape OK for {artist.id}: ml={sp_scraped.get('monthly_listeners')}")
        except Exception as e:
            logger.warning(f"Spotify scrape failed for {artist.id}: {e}")
    else:
        logger.warning(f"No Spotify ID for artist {artist.id}, skipping Spotify scrape")
    
    # --- Source 2: Deezer API (fans, top tracks, image) ---
    try:
        from app.enrichment.providers.deezer import search_deezer_artist
        dz_data = search_deezer_artist(artist.canonical_name)
        if dz_data:
            spotify_data["deezer_fans"] = dz_data.get("deezer_fans", 0)
            spotify_data["deezer_id"] = dz_data.get("deezer_id")
            spotify_data["top_tracks"] = dz_data.get("top_tracks", [])
            if not spotify_data.get("image_url"):
                spotify_data["image_url"] = dz_data.get("image_url")
            if not spotify_data.get("name"):
                spotify_data["name"] = dz_data.get("name")
            logger.info(f"Deezer OK for {artist.id}: fans={dz_data.get('deezer_fans')}")
    except Exception as e:
        logger.warning(f"Deezer fetch failed for {artist.id}: {e}")
    
    # If we got nothing from either source
    if spotify_data.get("monthly_listeners") is None and not spotify_data.get("deezer_fans"):
        snapshot = DiscoverySnapshot(
            artist_id=artist.id,
            source="SPOTIFY",
            status="PARTIAL",
            error_code="NO_DATA",
            error_message="No data from Spotify scraping or Deezer",
            raw_payload=spotify_data or None,
            ttl_expires_at=datetime.utcnow() + timedelta(hours=1),
            parser_version="v5.0-public-http",
        )
        db.add(snapshot)
        db.commit()
        return False
    
    # Deezer fans and Spotify listeners/followers are distinct measurements.
    # Keep missing values missing; do not manufacture cross-provider metrics.
    spotify_data.setdefault("genres", [])
    spotify_data.setdefault("top_tracks", [])

    # Store snapshot
    snapshot = DiscoverySnapshot(
        artist_id=artist.id,
        source="SPOTIFY",
        status="OK",
        raw_payload=spotify_data,
        ttl_expires_at=datetime.utcnow() + timedelta(hours=TTL_SPOTIFY_HOURS),
        parser_version="v5.0-public-http",
    )
    db.add(snapshot)
    
    # Update artist with scraped data
    if spotify_data.get("image_url") and not artist.image_url:
        artist.image_url = spotify_data["image_url"]
    if spotify_data.get("name") and artist.canonical_name.startswith("spotify:"):
        artist.canonical_name = spotify_data["name"]
        artist.normalized_name = normalize_artist_name(spotify_data["name"])
    
    db.commit()
    
    ml = spotify_data.get("monthly_listeners", 0)
    fans = spotify_data.get("deezer_fans", 0)
    logger.info(f"Spotify step OK for {artist.id}: ml={ml}, deezer_fans={fans}")
    return True


def _estimate_monthly_listeners(popularity: int, followers: int) -> int:
    """
    Estimate monthly listeners from Spotify popularity score and follower count.
    Spotify doesn't expose monthly_listeners via API, so we approximate.
    popularity 0-100 maps roughly: 0→0, 30→5K, 50→50K, 70→500K, 90→5M
    """
    if popularity >= 90:
        base = 5_000_000
    elif popularity >= 80:
        base = 1_000_000
    elif popularity >= 70:
        base = 500_000
    elif popularity >= 60:
        base = 100_000
    elif popularity >= 50:
        base = 50_000
    elif popularity >= 40:
        base = 20_000
    elif popularity >= 30:
        base = 5_000
    elif popularity >= 20:
        base = 1_000
    else:
        base = 500
    
    # Adjust with follower ratio
    if followers > 0:
        ratio = min(followers / max(base, 1), 3.0)
        base = int(base * max(ratio, 0.5))
    
    return base


# ============================================================================
# STEP 4: COMPUTE METRICS
# ============================================================================

def step_compute(db: Session, job: DiscoveryEnrichmentJob, viberate_ok: bool, spotify_ok: bool) -> None:
    """
    Step 4: Compute metrics from snapshots.
    Creates/updates ArtistComputedMetrics.
    """
    logger.info(f"Step COMPUTE for job {job.id}")
    
    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == job.artist_id
    ).first()
    
    if not artist:
        raise ValueError(f"Artist {job.artist_id} not found")
    
    # Get latest snapshots
    viberate_snapshot = db.query(DiscoverySnapshot).filter(
        DiscoverySnapshot.artist_id == artist.id,
        DiscoverySnapshot.source == "VIBERATE",
        DiscoverySnapshot.status.in_(["OK", "PARTIAL"]),
    ).order_by(DiscoverySnapshot.fetched_at.desc()).first()
    
    spotify_snapshot = db.query(DiscoverySnapshot).filter(
        DiscoverySnapshot.artist_id == artist.id,
        DiscoverySnapshot.source == "SPOTIFY",
        DiscoverySnapshot.status.in_(["OK", "PARTIAL"]),
    ).order_by(DiscoverySnapshot.fetched_at.desc()).first()
    
    # Extract data
    vib_data = (viberate_snapshot.raw_payload if viberate_snapshot else None) or {}
    spot_data = (spotify_snapshot.raw_payload if spotify_snapshot else None) or {}
    
    # Calculate metrics — merge Viberate + Spotify/Deezer data
    # Monthly listeners: prefer Spotify scraped (exact), then Viberate, then estimated
    monthly_listeners = spot_data.get("monthly_listeners", 0) or 0
    if not monthly_listeners:
        raw_ml = vib_data.get("monthly_listeners", 0)
        if isinstance(raw_ml, dict):
            monthly_listeners = raw_ml.get("value", 0) or 0
        else:
            monthly_listeners = raw_ml or 0
    
    # Followers: prefer Spotify/Deezer data
    spotify_followers = spot_data.get("followers_total", 0) or 0
    deezer_fans = spot_data.get("deezer_fans", 0) or 0
    
    # Social stats: prefer Viberate scrape, fallback to 0
    instagram_followers = vib_data.get("instagram_followers", 0) or 0
    tiktok_followers = vib_data.get("tiktok_followers", 0) or 0
    youtube_subscribers = vib_data.get("youtube_subscribers", 0) or 0
    
    # If Viberate had nested social_stats format
    if not instagram_followers and isinstance(vib_data.get("social_stats"), dict):
        ss = vib_data["social_stats"]
        instagram_followers = ss.get("instagram_followers", 0) or 0
        tiktok_followers = ss.get("tiktok_followers", 0) or 0
        youtube_subscribers = ss.get("youtube_subscribers", 0) or 0
        spotify_followers = spotify_followers or (ss.get("spotify_followers", 0) or 0)
    
    # Use deezer_fans as spotify_followers proxy if we have nothing
    if not spotify_followers and deezer_fans:
        spotify_followers = deezer_fans
    
    total_social = instagram_followers + tiktok_followers + youtube_subscribers + spotify_followers
    
    # Calculate score using existing engine logic
    score, timing, recommendation, drivers, penalties = calculate_discovery_score(
        monthly_listeners=monthly_listeners,
        spotify_followers=spotify_followers,
        total_social=total_social,
        historical_listeners=vib_data.get("listeners_history", []),
    )
    
    # Calculate velocity/acceleration
    velocity, acceleration = calculate_growth_metrics(
        vib_data.get("listeners_history", [])
    )
    
    # Detect signals
    signals = detect_signals(velocity, acceleration, vib_data)
    
    # Detect patterns
    patterns = detect_patterns(vib_data.get("listeners_history", []), velocity, acceleration)
    
    # Estimate fees
    fee_min, fee_max = estimate_fees(monthly_listeners, total_social, velocity)
    
    # Determine data quality
    data_quality = "HIGH" if viberate_ok and spotify_ok else ("MEDIUM" if viberate_ok or spotify_ok else "LOW")
    
    # Create or update computed metrics
    existing = db.query(DiscoveryComputedMetrics).filter(
        DiscoveryComputedMetrics.artist_id == artist.id
    ).order_by(DiscoveryComputedMetrics.computed_at.desc()).first()
    
    metrics = DiscoveryComputedMetrics(
        artist_id=artist.id,
        score=score,
        timing_bucket=timing,
        recommendation=recommendation,
        drivers=drivers,
        penalties=penalties,
        monthly_listeners_series=vib_data.get("listeners_history", []),
        velocity=velocity,
        acceleration=acceleration,
        signals=signals,
        patterns=patterns,
        fee_estimate_min=fee_min,
        fee_estimate_max=fee_max,
        data_quality=data_quality,
        last_updated_by_source={
            "viberate": viberate_snapshot.fetched_at.isoformat() if viberate_snapshot else None,
            "spotify": spotify_snapshot.fetched_at.isoformat() if spotify_snapshot else None,
        },
        algo_version="v3.0",
        monthly_listeners=monthly_listeners,
        spotify_followers=spotify_followers,
        instagram_followers=instagram_followers,
        tiktok_followers=tiktok_followers,
        youtube_subscribers=youtube_subscribers,
        total_social_followers=total_social,
    )
    
    db.add(metrics)
    
    # Update artist quality
    artist.data_quality = data_quality
    artist.last_enriched_at = datetime.utcnow()

    # --- Create ArtistSnapshot for prediction service (EWMA) ---
    from app.db.models.artist_snapshot import ArtistSnapshot as SnapModel
    snap = SnapModel(
        artist_name=artist.canonical_name,
        artist_name_normalized=SnapModel.normalize_name(artist.canonical_name),
        workspace_id=artist.workspace_id,
        snapshot_date=datetime.utcnow(),
        spotify_monthly_listeners=monthly_listeners or None,
        spotify_followers=spotify_followers or None,
        tiktok_followers=tiktok_followers or None,
        youtube_subscribers=youtube_subscribers or None,
        instagram_followers=instagram_followers or None,
        source_quality_score=80.0 if data_quality == "HIGH" else 50.0,
        sources_used="deezer,spotify,musicbrainz",
    )
    db.add(snap)
    logger.info(f"Created snapshot for {artist.canonical_name} (ml={monthly_listeners})")
    
    db.commit()
    
    logger.info(f"Computed metrics for artist {artist.id}: score={score}, timing={timing}")


def _generate_candidates_for_artist(db: Session, job: DiscoveryEnrichmentJob) -> None:
    """
    Generate DiscoveryCandidate entries immediately after computing metrics,
    so the artist appears in the feed right away.
    """
    from app.workers.discovery_scheduler import calculate_recommended_rank, calculate_trending_rank
    
    artist = db.query(DiscoveryArtist).filter(DiscoveryArtist.id == job.artist_id).first()
    if not artist:
        return
    
    metrics = db.query(DiscoveryComputedMetrics).filter(
        DiscoveryComputedMetrics.artist_id == artist.id
    ).order_by(DiscoveryComputedMetrics.computed_at.desc()).first()
    
    if not metrics:
        return
    
    ttl_expires = datetime.utcnow() + timedelta(hours=24)
    now = datetime.utcnow()
    
    # Delete old candidates for this artist in this workspace
    db.query(DiscoveryCandidate).filter(
        DiscoveryCandidate.artist_id == artist.id,
        DiscoveryCandidate.workspace_id == artist.workspace_id,
    ).delete()
    
    # RECOMMENDED candidate
    rec_rank = calculate_recommended_rank(
        score=metrics.score,
        timing=metrics.timing_bucket,
        monthly_listeners=metrics.monthly_listeners or 0,
        data_quality=metrics.data_quality or "LOW",
    )
    reasons = (metrics.drivers or [])[:2]
    db.add(DiscoveryCandidate(
        workspace_id=artist.workspace_id,
        artist_id=artist.id,
        candidate_type="RECOMMENDED",
        rank_score=rec_rank,
        reasons=reasons,
        computed_at=now,
        ttl_expires_at=ttl_expires,
    ))
    
    # TRENDING candidate
    trend_rank = calculate_trending_rank(
        velocity=metrics.velocity or 0,
        acceleration=metrics.acceleration or 0,
        score=metrics.score,
    )
    trend_reasons = []
    if metrics.velocity and metrics.velocity > 0.2:
        trend_reasons.append({"label": "Croissance rapide", "value": f"+{int(metrics.velocity*100)}%/mois", "impact": 15})
    if metrics.acceleration and metrics.acceleration > 0.1:
        trend_reasons.append({"label": "Accélération", "value": f"+{int(metrics.acceleration*100)}%", "impact": 10})
    
    db.add(DiscoveryCandidate(
        workspace_id=artist.workspace_id,
        artist_id=artist.id,
        candidate_type="TRENDING",
        rank_score=trend_rank,
        reasons=trend_reasons[:2],
        computed_at=now,
        ttl_expires_at=ttl_expires,
    ))
    
    db.commit()
    logger.info(f"Generated candidates for artist {artist.id} (rec={rec_rank:.1f}, trend={trend_rank:.1f})")


def _sync_to_artist_analyses(db: Session, job: DiscoveryEnrichmentJob) -> None:
    """
    Sync discovery results to artist_analyses table for frontend display.
    Uses EWMA prediction service + GPT-4o-mini for qualitative intelligence.
    Falls back to rule-based if LLM unavailable.
    """
    from app.db.models.artist_analysis import ArtistAnalysis
    from app.intelligence.artist_intelligence import (
        compute_statistical_predictions,
        compute_llm_intelligence,
    )

    artist = db.query(DiscoveryArtist).filter(
        DiscoveryArtist.id == job.artist_id
    ).first()
    if not artist:
        return

    metrics = db.query(DiscoveryComputedMetrics).filter(
        DiscoveryComputedMetrics.artist_id == artist.id
    ).order_by(DiscoveryComputedMetrics.computed_at.desc()).first()
    if not metrics:
        return

    # Get spotify snapshot for extra data
    spot_snap = db.query(DiscoverySnapshot).filter(
        DiscoverySnapshot.artist_id == artist.id,
        DiscoverySnapshot.source == "SPOTIFY",
    ).order_by(DiscoverySnapshot.fetched_at.desc()).first()
    spot_data = (spot_snap.raw_payload if spot_snap else None) or {}

    ml = metrics.monthly_listeners or 0
    velocity = metrics.velocity or 0
    fee_min = metrics.fee_estimate_min or 0
    fee_max = metrics.fee_estimate_max or 0
    score = metrics.score or 0

    # Determine market tier
    if ml >= 5_000_000:
        tier = "superstar"
    elif ml >= 1_000_000:
        tier = "major"
    elif ml >= 200_000:
        tier = "established"
    elif ml >= 50_000:
        tier = "rising"
    elif ml >= 10_000:
        tier = "emerging"
    else:
        tier = "underground"

    # --- 1. Statistical predictions (EWMA or velocity fallback) ---
    preds = compute_statistical_predictions(
        db=db,
        artist_name=artist.canonical_name,
        workspace_id=artist.workspace_id,
        ml=ml,
        velocity=velocity,
        tier=tier,
        spotify_followers=metrics.spotify_followers or 0,
        instagram_followers=metrics.instagram_followers or 0,
        tiktok_followers=metrics.tiktok_followers or 0,
        youtube_subscribers=metrics.youtube_subscribers or 0,
    )
    logger.info(f"Predictions for {artist.canonical_name}: method={preds['prediction_method']}, "
                f"30d={preds['predicted_listeners_30d']}, trend={preds['growth_trend']}")

    # --- 2. LLM-powered intelligence (GPT or rule-based fallback) ---
    genres = spot_data.get("genres", [])
    intel = compute_llm_intelligence(
        artist_name=artist.canonical_name,
        tier=tier,
        ml=ml,
        spotify_followers=metrics.spotify_followers or 0,
        instagram_followers=metrics.instagram_followers or 0,
        tiktok_followers=metrics.tiktok_followers or 0,
        youtube_subscribers=metrics.youtube_subscribers or 0,
        genres=genres,
        country=artist.country,
        velocity=velocity,
        growth_trend=preds["growth_trend"],
        predicted_30d=preds["predicted_listeners_30d"],
        predicted_90d=preds["predicted_listeners_90d"],
        fee_min=fee_min,
        fee_max=fee_max,
        score=score,
        drivers=metrics.drivers or [],
        penalties=metrics.penalties or [],
        signals=metrics.signals or [],
    )
    logger.info(f"Intelligence for {artist.canonical_name}: method={intel.get('intelligence_method')}")

    # --- Build update dict ---
    update_fields = dict(
        spotify_monthly_listeners=ml,
        instagram_followers=metrics.instagram_followers or 0,
        tiktok_followers=metrics.tiktok_followers or 0,
        youtube_subscribers=metrics.youtube_subscribers or 0,
        total_followers=metrics.total_social_followers or 0,
        fee_min=fee_min,
        fee_max=fee_max,
        market_tier=tier,
        popularity_score=score,
        ai_score=score,
        image_url=artist.image_url,
        confidence_score=preds["confidence_score"],
        # Predictions (from EWMA/velocity)
        growth_trend=preds["growth_trend"],
        growth_rate_monthly=preds["growth_rate_monthly"],
        predicted_listeners_30d=preds["predicted_listeners_30d"],
        predicted_listeners_90d=preds["predicted_listeners_90d"],
        predicted_listeners_180d=preds["predicted_listeners_180d"],
        # Intelligence (from LLM/rule-based)
        best_platforms=intel["best_platforms"],
        viral_potential=intel["viral_potential"],
        optimal_fee=intel["optimal_fee"],
        negotiation_power=intel["negotiation_power"],
        best_booking_window=intel["best_booking_window"],
        event_type_fit=intel["event_type_fit"],
        territory_strength=intel["territory_strength"],
        seasonal_demand=intel["seasonal_demand"],
        ai_summary=intel["ai_summary"],
        ai_tier=tier,
        strengths=intel["strengths"],
        weaknesses=intel["weaknesses"],
        opportunities=intel["opportunities"],
        threats=intel["threats"],
        ai_recommendations=intel["ai_recommendations"],
        content_recommendations=intel.get("content_recommendations", []),
        created_at=datetime.utcnow(),
    )

    # Check if already exists (update instead of duplicate)
    existing = db.query(ArtistAnalysis).filter(
        ArtistAnalysis.workspace_id == artist.workspace_id,
        ArtistAnalysis.artist_name == artist.canonical_name,
    ).first()

    if existing:
        for k, v in update_fields.items():
            setattr(existing, k, v)
        logger.info(f"Updated artist_analyses for {artist.canonical_name}")
    else:
        analysis = ArtistAnalysis(
            workspace_id=artist.workspace_id,
            artist_name=artist.canonical_name,
            genre=", ".join(genres) if genres else None,
            market_trend=preds["growth_trend"],
            sources_scanned="spotify,deezer,musicbrainz",
            **update_fields,
        )
        db.add(analysis)
        logger.info(f"Created artist_analyses for {artist.canonical_name}")

    db.commit()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_discovery_score(
    monthly_listeners: int,
    spotify_followers: int,
    total_social: int,
    historical_listeners: List[Dict],
) -> Tuple[int, str, str, List[Dict], List[Dict]]:
    """
    Calculate discovery score (0-100), timing, recommendation, drivers, and penalties.
    """
    drivers = []
    penalties = []
    score = 30  # Base score
    
    # Listener size scoring
    if monthly_listeners >= 100000:
        score -= 10
        penalties.append({"label": "Déjà établi", "value": f"{monthly_listeners:,} listeners", "impact": -10})
    elif monthly_listeners >= 50000:
        score += 10
        drivers.append({"label": "Audience solide", "value": f"{monthly_listeners:,} listeners", "impact": 10})
    elif monthly_listeners >= 10000:
        score += 15
        drivers.append({"label": "Sweet spot émergent", "value": f"{monthly_listeners:,} listeners", "impact": 15})
    elif monthly_listeners >= 1000:
        score += 5
        drivers.append({"label": "Artiste early-stage", "value": f"{monthly_listeners:,} listeners", "impact": 5})
    
    # Growth from history
    if historical_listeners and len(historical_listeners) >= 2:
        first_val = historical_listeners[0].get("value", 0) if isinstance(historical_listeners[0], dict) else historical_listeners[0]
        last_val = historical_listeners[-1].get("value", 0) if isinstance(historical_listeners[-1], dict) else historical_listeners[-1]
        
        if first_val > 0:
            growth_rate = (last_val - first_val) / first_val
            if growth_rate >= 0.5:
                score += 25
                drivers.append({"label": "Croissance explosive", "value": f"+{int(growth_rate*100)}%", "impact": 25})
            elif growth_rate >= 0.25:
                score += 15
                drivers.append({"label": "Croissance rapide", "value": f"+{int(growth_rate*100)}%", "impact": 15})
            elif growth_rate >= 0.10:
                score += 10
                drivers.append({"label": "Croissance stable", "value": f"+{int(growth_rate*100)}%", "impact": 10})
            elif growth_rate < 0:
                score -= 10
                penalties.append({"label": "Déclin", "value": f"{int(growth_rate*100)}%", "impact": -10})
    
    # Social presence
    if total_social >= 100000:
        score += 10
        drivers.append({"label": "Forte présence sociale", "value": f"{total_social:,}", "impact": 10})
    elif total_social >= 50000:
        score += 5
        drivers.append({"label": "Bonne présence sociale", "value": f"{total_social:,}", "impact": 5})
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Determine timing
    if score >= 80:
        timing = "IMMINENT"
    elif score >= 65:
        timing = "1_3M"
    elif score >= 50:
        timing = "3_6M"
    elif score >= 35:
        timing = "6_12M"
    else:
        timing = "LONG"
    
    # Determine recommendation
    if score >= 70:
        recommendation = "BOOK"
    elif score >= 45:
        recommendation = "WATCHLIST"
    else:
        recommendation = "IGNORE"
    
    return score, timing, recommendation, drivers[:3], penalties[:2]


def calculate_growth_metrics(historical: List) -> Tuple[float, float]:
    """Calculate velocity and acceleration from historical data."""
    if not historical or len(historical) < 2:
        return 0.0, 0.0
    
    values = []
    for item in historical:
        if isinstance(item, dict):
            values.append(item.get("value", 0))
        else:
            values.append(item)
    
    if len(values) < 2:
        return 0.0, 0.0
    
    # Calculate growth rates
    growth_rates = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            rate = (values[i] - values[i-1]) / values[i-1]
            growth_rates.append(rate)
    
    if not growth_rates:
        return 0.0, 0.0
    
    velocity = sum(growth_rates) / len(growth_rates)
    
    # Acceleration
    if len(growth_rates) >= 2:
        recent = sum(growth_rates[-2:]) / 2
        older = sum(growth_rates[:-2]) / max(1, len(growth_rates) - 2) if len(growth_rates) > 2 else growth_rates[0]
        acceleration = recent - older
    else:
        acceleration = 0.0
    
    return velocity, acceleration


def detect_signals(velocity: float, acceleration: float, data: Dict) -> List[Dict]:
    """Detect discovery signals."""
    signals = []
    
    if velocity >= 0.5:
        signals.append({
            "type": "viral_growth",
            "strength": min(1.0, velocity),
            "source": "listeners_history",
        })
    
    if acceleration > 0.2:
        signals.append({
            "type": "social_surge",
            "strength": min(1.0, acceleration * 2),
            "source": "growth_acceleration",
        })
    
    # Playlist detection (if available in data)
    if data.get("playlist_adds", 0) > 5:
        signals.append({
            "type": "playlist_boost",
            "strength": 0.8,
            "source": "playlist_tracking",
        })
    
    return signals


def detect_patterns(historical: List, velocity: float, acceleration: float) -> List[Dict]:
    """Detect growth patterns."""
    patterns = []
    
    if not historical or len(historical) < 4:
        return patterns
    
    values = [h.get("value", 0) if isinstance(h, dict) else h for h in historical]
    
    # Hockey stick pattern
    mid = len(values) // 2
    first_half = values[:mid]
    second_half = values[mid:]
    
    if first_half and second_half:
        first_growth = (first_half[-1] - first_half[0]) / max(first_half[0], 1)
        second_growth = (second_half[-1] - second_half[0]) / max(second_half[0], 1)
        
        if second_growth > first_growth * 3 and second_growth > 0.3:
            patterns.append({
                "type": "hockey_stick",
                "confidence": 0.85,
            })
    
    # Accelerating pattern
    if acceleration > 0.1:
        patterns.append({
            "type": "accelerating",
            "confidence": min(0.9, 0.5 + acceleration),
        })
    
    # Steady climb
    if velocity > 0.1 and acceleration >= 0:
        consecutive_growth = all(values[i] >= values[i-1] for i in range(1, len(values)))
        if consecutive_growth:
            patterns.append({
                "type": "steady_climb",
                "confidence": 0.8,
            })
    
    return patterns


def estimate_fees(monthly_listeners: int, total_social: int, velocity: float) -> Tuple[Optional[int], Optional[int]]:
    """Indicative range only when observations support an estimate."""
    if not monthly_listeners and not total_social:
        return None, None
    if monthly_listeners < 5000:
        base_min, base_max = 300, 800
    elif monthly_listeners < 20000:
        base_min, base_max = 800, 2000
    elif monthly_listeners < 50000:
        base_min, base_max = 2000, 4000
    elif monthly_listeners < 100000:
        base_min, base_max = 4000, 8000
    elif monthly_listeners < 250000:
        base_min, base_max = 8000, 15000
    elif monthly_listeners < 500000:
        base_min, base_max = 15000, 30000
    else:
        base_min, base_max = 25000, 50000
    
    # Velocity multiplier
    if velocity >= 0.5:
        base_min = int(base_min * 1.3)
        base_max = int(base_max * 1.5)
    
    return base_min, base_max


# ============================================================================
# UTILITY TASKS
# ============================================================================

@celery_app.task(name="discovery.refresh_artist")
def refresh_artist(artist_id: str, workspace_id: int, requested_by: int = None) -> Dict[str, Any]:
    """
    Manually refresh an artist's data.
    Creates a new enrichment job starting at VIBERATE step.
    """
    db = get_db()
    try:
        artist = db.query(DiscoveryArtist).filter(
            DiscoveryArtist.id == artist_id,
            DiscoveryArtist.workspace_id == workspace_id
        ).first()
        
        if not artist:
            return {"status": "ERROR", "message": "Artist not found"}
        
        # Create refresh job
        job = DiscoveryEnrichmentJob(
            workspace_id=workspace_id,
            requested_by=requested_by,
            input_type="VIBERATE_URL" if artist.viberate_url else "SPOTIFY_URL",
            input_value=artist.viberate_url or f"https://open.spotify.com/artist/{artist.spotify_artist_id}",
            artist_id=artist.id,
            status="QUEUED",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Queue the pipeline
        run_enrichment_pipeline.delay(str(job.id))
        
        return {
            "status": "JOB_CREATED",
            "job_id": str(job.id),
            "artist_id": str(artist.id),
        }
        
    finally:
        db.close()
