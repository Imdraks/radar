"""Configuration is not a successful provider request. Expose scoped observations only."""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_workspace, get_current_user
from app.core.config import settings
from app.core.cache import cache_get
from app.core.subscription import Feature, effective_features
from app.db.models.discovery import (
    DiscoveryArtist,
    DiscoverySnapshot,
    DiscoveryEnrichmentJob,
)
from app.services.mfa_delivery import availability

router = APIRouter(prefix="/integrations")


@router.get("/status")
def status(
    db: Session = Depends(get_db),
    ws=Depends(get_current_workspace),
    user=Depends(get_current_user),
):
    features = effective_features(ws)
    providers = [
        {
            "id": "email",
            "name": "E-mails Radar",
            "configured": availability()["email"],
            "state": (
                "configured_unverified" if availability()["email"] else "not_configured"
            ),
            "scope": "plateforme",
        }
    ]
    if Feature.DISCOVERY in features:
        for id, name, configured in [
            (
                "spotify",
                "Spotify",
                bool(settings.spotify_client_id and settings.spotify_client_secret),
            ),
            ("youtube", "YouTube", bool(settings.youtube_api_key)),
            ("ticketmaster", "Ticketmaster", bool(settings.ticketmaster_api_key)),
        ]:
            providers.append(
                {
                    "id": id,
                    "name": name,
                    "configured": configured,
                    "state": (
                        "configured_unverified" if configured else "not_configured"
                    ),
                    "scope": "plateforme",
                }
            )
    for id, name, key in [
        ("drive", "Google Drive", "google_workspace_tokens"),
        ("calendar", "Google Calendar", "google_calendar_tokens"),
    ]:
        try:
            token = cache_get(f"{key}:{user.id}")
            state = (
                "not_connected"
                if not token
                else (
                    "authorization_present"
                    if token.get("expires_at", 0) > datetime.utcnow().timestamp()
                    else "authorization_expired"
                )
            )
        except Exception:
            state = "unknown"
        providers.append(
            {"id": id, "name": name, "state": state, "scope": "mon compte"}
        )
    observations = []
    jobs = []
    if Feature.DISCOVERY in features:
        snapshots = (
            db.query(DiscoverySnapshot)
            .join(DiscoveryArtist)
            .filter(
                DiscoveryArtist.workspace_id == ws.id,
                DiscoveryArtist.is_deleted == False,
            )
            .order_by(DiscoverySnapshot.fetched_at.desc())
            .limit(50)
            .all()
        )
        observations = [
            {
                "source": s.source,
                "status": s.status,
                "collected_at": s.fetched_at,
                "expires_at": s.ttl_expires_at,
                "stale": s.ttl_expires_at < datetime.utcnow(),
                "error_code": s.error_code,
            }
            for s in snapshots
        ]
        rows = (
            db.query(DiscoveryEnrichmentJob)
            .filter_by(workspace_id=ws.id)
            .order_by(DiscoveryEnrichmentJob.created_at.desc())
            .limit(20)
            .all()
        )
        jobs = [
            {
                "id": r.id,
                "status": r.status,
                "step": r.current_step,
                "updated_at": r.updated_at,
                "error_code": r.error_code,
            }
            for r in rows
        ]
    return {
        "checked_at": datetime.utcnow(),
        "providers": providers,
        "observations": observations,
        "jobs": jobs,
        "notice": "Configuration et autorisations locales : aucune disponibilité fournisseur n’est déduite. Les observations sont celles de cet espace uniquement.",
    }
