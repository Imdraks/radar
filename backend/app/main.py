"""
FastAPI Application - Radar
Lead intelligence and opportunity tracking platform
"""
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

from app.db import tenant_scope  # Register request-session ORM isolation
from app.core.config import settings
from app.api.deps import require_feature, require_workspace_write, get_current_workspace, get_current_platform_admin
from app.core.subscription import Feature


def suspended_module():
    from fastapi import HTTPException
    raise HTTPException(status_code=503, detail="Module suspendu en attente de validation")

# ============================================================================
# API ROUTERS - V1 (Legacy Opportunity-based)
# ============================================================================
from app.api import (
    auth_router,
    opportunities_router,  # Legacy v1 - uses Integer IDs
    sources_router,
    ingestion_router,
    scoring_router,
    users_router,
    dashboard_router,
)
from app.api.predictions import router as predictions_router, reports_router
from app.api.artist_history import router as artist_history_router
from app.api.artist_predictions import router as artist_predictions_router
from app.api.enrichment import router as enrichment_router
from app.api.sso import router as sso_router
from app.api.ai_intelligence import router as ai_intelligence_router
from app.api.collection import router as collection_router
from app.api.websocket import router as websocket_router
from app.api.collect import router as collect_router
from app.api.dossiers import router as dossiers_router
from app.api.progress import router as progress_router
from app.api.radar import router as radar_router
from app.api.activity import router as activity_router
from app.api.health import router as health_router

# ============================================================================
# API ROUTERS - V2 (New LeadItem-based with UUIDs)
# ============================================================================
from app.api.collections_api import router as collections_v2_router
from app.api.leads import router as leads_v2_router  # Renamed from opportunities_api
from app.api.dossiers_api import router as dossiers_v2_router

# ============================================================================
# RADAR FEATURES - Advanced functionality
# ============================================================================
from app.api.profiles import router as profiles_router
from app.api.shortlists import router as shortlists_router
from app.api.clusters import router as clusters_router
from app.api.deadlines import router as deadlines_router
from app.api.source_health import router as source_health_router
from app.api.contact_finder import router as contact_finder_router
from app.api.advanced_features import router as advanced_features_router
from app.api.analytics import router as analytics_router
from app.api.competitive import router as competitive_router
from app.api.market_intelligence import router as market_intelligence_router
from app.api.analytics_v2 import router as analytics_v2_router
from app.api.map_calendar import router as map_router, calendar_router
from app.api.tags_comments import router as tags_router, comments_router, favorites_router
from app.api.google_calendar import router as google_calendar_router

# ============================================================================
# AGENCY COCKPIT V2 - New Agency Management System
# ============================================================================
from app.api.agency import router as agency_router
from app.api.agency_projects import router as agency_projects_router
from app.api.agency_tasks import router as agency_tasks_router
from app.api.project_detail import router as project_detail_router

# ============================================================================
# V3 - Workspace, Inbox, Google Drive Integration
# ============================================================================
from app.api.workspace import router as workspace_router
from app.api.inbox import router as inbox_router
from app.api.google_drive import router as google_drive_router
# ============================================================================
# SUBSCRIPTION - Plans, Packs & Features
# ============================================================================
from app.api.subscription import router as subscription_router

# ============================================================================
# BILLING - Quotes (Devis) & Invoices (Factures) - Radar Business
# ============================================================================
from app.api.billing import router as billing_router

# ============================================================================
# BANKING - Connexions bancaires - Radar Business
# ============================================================================
from app.api.banking import router as banking_router
from app.api.revolut import router as revolut_router

# ============================================================================
# UNIFIED ASSETS API - Single source of truth for all assets
# ============================================================================
from app.api.assets import router as unified_assets_router

# ============================================================================
# DISCOVERY V3 - Artist discovery and comparison
# ============================================================================
from app.api.discovery import router as discovery_router
from app.api.comparison import router as comparison_router

# ============================================================================
# SPOTIFY SEARCH - Dedicated Spotify search engine with enrichment
# ============================================================================
from app.api.spotify_search import router as spotify_search_router

# ============================================================================
# ARTISTS V2 - "Google des artistes" search-first system
# ============================================================================
from app.api.artists import router as artists_v2_router
from app.api.events import router as events_router
from app.api.contact import router as public_contact_router
# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import security middlewares
from app.core.security_middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    InputValidationMiddleware,
    RequestIdMiddleware,
    AuditLogMiddleware,
    BotProtectionMiddleware,
)

# Import advanced security (backdoor, reverse shell, injection protection)
from app.core.advanced_security import (
    AdvancedSecurityMiddleware,
    FileUploadSecurityMiddleware,
    HoneypotMiddleware,
)

# Performance monitoring middleware
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        # Log slow requests (>1s)
        if process_time > 1.0:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
        return response


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="API pour la veille et qualification d'opportunités événementielles",
    version="1.0.0",
    docs_url="/docs" if settings.app_env == "development" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.app_env == "development" else None,  # Disable redoc in production
)

# CORS configuration - dynamic based on environment
cors_origins = [
    settings.frontend_url,
    settings.backend_url,
    "https://radarapp.fr",
    "http://radarapp.fr",
    "https://www.radarapp.fr",
    "http://37.59.106.73",
]
# Add localhost in development mode
if settings.app_env == "development":
    cors_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

# ============================================================================
# SECURITY MIDDLEWARES - Order matters! (first added = last executed)
# ============================================================================

# Add GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# Add timing middleware for performance monitoring
app.add_middleware(TimingMiddleware)

# Security headers (XSS, Clickjacking protection)
app.add_middleware(SecurityHeadersMiddleware)

# Request ID for tracing
app.add_middleware(RequestIdMiddleware)

# Rate limiting (brute force protection)
app.add_middleware(RateLimitMiddleware)

# Input validation (SQL injection, XSS detection)
app.add_middleware(InputValidationMiddleware)

# Audit logging for sensitive actions
app.add_middleware(AuditLogMiddleware)

# Block malicious bots and scanners
app.add_middleware(BotProtectionMiddleware)

# ============================================================================
# ADVANCED SECURITY (Backdoors, Reverse Shells, etc.)
# ============================================================================

# Honeypot endpoints (detect attackers looking for common vulnerabilities)
app.add_middleware(HoneypotMiddleware)

# Advanced attack detection (command injection, path traversal, reverse shells)
app.add_middleware(AdvancedSecurityMiddleware)

# File upload security
app.add_middleware(FileUploadSecurityMiddleware)

# CORS (must be after security middlewares)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Accept", "Accept-Language", "Content-Language", "Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)


# Exception handler - Don't expose internal errors in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full error internally
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.exception(f"[{request_id}] Unhandled error: {exc}")
    
    # Return generic error to client (don't expose internals)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Une erreur interne est survenue",
            "request_id": request_id
        },
    )


# Health check endpoints (no prefix for /health and /health/detailed)
app.include_router(health_router, tags=["Health"])


# ============================================================================
# API ROUTE REGISTRATION
# ============================================================================

# V1 Routes - Legacy (Integer IDs, Opportunity model)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(opportunities_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.LEADS)), Depends(require_workspace_write)], prefix="/api/v1")  # Legacy /opportunities
# Static /sources/health must precede dynamic /sources/{source_id}.
app.include_router(source_health_router, dependencies=[Depends(get_current_platform_admin)], prefix="/api/v1", tags=["Source Health"])
app.include_router(sources_router, dependencies=[Depends(get_current_platform_admin)], prefix="/api/v1")
app.include_router(ingestion_router, dependencies=[Depends(get_current_platform_admin)], prefix="/api/v1")
app.include_router(scoring_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.SCORING)), Depends(require_workspace_write)], prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(dashboard_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1")
app.include_router(predictions_router, dependencies=[Depends(suspended_module)], prefix="/api/v1")
app.include_router(reports_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.INVOICES)), Depends(get_current_workspace)], prefix="/api/v1")
app.include_router(artist_history_router, dependencies=[Depends(require_feature(Feature.ARTISTS)), Depends(require_workspace_write)], prefix="/api/v1/artist-history", tags=["Artist History"])
app.include_router(artist_predictions_router, dependencies=[Depends(require_feature(Feature.ARTISTS)), Depends(require_workspace_write)], prefix="/api/v1/artist-predictions", tags=["Artist Predictions"])
app.include_router(enrichment_router, dependencies=[Depends(require_feature(Feature.ARTISTS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Artist Enrichment"])
app.include_router(sso_router, prefix="/api/v1", tags=["SSO Authentication"])
app.include_router(ai_intelligence_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.ARTISTS)), Depends(get_current_workspace)], prefix="/api/v1", tags=["AI Intelligence"])
app.include_router(collection_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1", tags=["Collection"])
app.include_router(collect_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1", tags=["Unified Collection"])
app.include_router(dossiers_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1/dossiers", tags=["Dossiers"])

# Auto Radar - Automatic harvesting
app.include_router(radar_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1/radar", tags=["Auto Radar"])

# Activity Logs - Superadmin only
app.include_router(activity_router, prefix="/api/v1/admin", tags=["Activity Logs"])

# V2 Routes - New architecture (UUIDs, LeadItem model)
app.include_router(collections_v2_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v2", tags=["Collections V2"])
app.include_router(leads_v2_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.LEADS)), Depends(require_workspace_write)], prefix="/api/v2", tags=["Leads V2"])  # /api/v2/leads
app.include_router(dossiers_v2_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v2", tags=["Dossiers V2"])

# Radar Features - Advanced functionality
app.include_router(profiles_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.PROFILES)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Profiles"])
app.include_router(shortlists_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1", tags=["Shortlists"])
app.include_router(clusters_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Clusters"])
app.include_router(deadlines_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Deadlines"])
app.include_router(contact_finder_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1", tags=["Contact Finder"])
app.include_router(advanced_features_router, dependencies=[Depends(require_workspace_write), Depends(require_feature(Feature.LEADS)), Depends(get_current_workspace)], prefix="/api/v1", tags=["Advanced Features"])
app.include_router(analytics_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.INVOICES)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Analytics Dashboard"])
app.include_router(competitive_router, dependencies=[Depends(suspended_module)], prefix="/api/v1", tags=["Competitive Intelligence"])
app.include_router(market_intelligence_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.INVOICES)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Market Intelligence"])
app.include_router(analytics_v2_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.ANALYTICS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Analytics V2"])
app.include_router(map_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.EVENTS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Map"])
app.include_router(calendar_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Calendar"])
app.include_router(google_calendar_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Google Calendar"])
app.include_router(tags_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Tags"])
app.include_router(comments_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Comments"])
app.include_router(favorites_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Favorites"])

# ============================================================================
# AGENCY COCKPIT V2 - Commercial + Production + Assets + Calendar
# ============================================================================
app.include_router(agency_router, dependencies=[Depends(get_current_workspace), Depends(require_workspace_write)], prefix="/api/v1", tags=["Agency Cockpit"])
app.include_router(agency_projects_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.PROJECTS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Agency Projects"])
app.include_router(agency_tasks_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.PROJECTS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Agency Tasks & Assets"])
app.include_router(project_detail_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.PROJECTS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Project Detail Page"])

# ============================================================================
# V3 - Workspace, Inbox, Google Drive (Daily Hub)
# ============================================================================
app.include_router(workspace_router, prefix="/api/v1", tags=["Workspaces"])
app.include_router(inbox_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Inbox"])
app.include_router(google_drive_router, dependencies=[Depends(require_workspace_write), Depends(get_current_workspace)], prefix="/api/v1", tags=["Google Drive"])

# ============================================================================
# SUBSCRIPTION - Plans, Packs & Features
# ============================================================================
app.include_router(subscription_router, prefix="/api/v1", tags=["Subscription"])

# ============================================================================
# BILLING - Quotes (Devis) & Invoices (Factures) - Radar Business
# ============================================================================
app.include_router(billing_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.INVOICES)), Depends(require_workspace_write)], prefix="/api/v1/billing", tags=["Billing"])

# ============================================================================
# BANKING - Connexions bancaires - Radar Business
# ============================================================================
app.include_router(banking_router, dependencies=[Depends(suspended_module)], prefix="/api/v1", tags=["Banking"])
app.include_router(revolut_router, dependencies=[Depends(suspended_module)], prefix="/api/v1", tags=["Revolut"])

# ============================================================================
# UNIFIED ASSETS API - Single source of truth
# ============================================================================
app.include_router(unified_assets_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.ASSETS)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Assets"])

# ============================================================================
# DISCOVERY V3 - Artist discovery feed, search, comparison
# ============================================================================
app.include_router(discovery_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.DISCOVERY)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Discovery V3"])
app.include_router(comparison_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.COMPARISON)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Comparison V3"])

# ============================================================================
# SPOTIFY SEARCH - Dedicated Spotify search engine
# ============================================================================
app.include_router(spotify_search_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.SPOTIFY_SEARCH)), Depends(require_workspace_write)], prefix="/api/v1", tags=["Spotify Search"])

# ============================================================================
# ARTISTS V2 - "Google des artistes" search-first endpoints
# ============================================================================
app.include_router(artists_v2_router, dependencies=[Depends(get_current_workspace), Depends(require_feature(Feature.ARTISTS)), Depends(require_workspace_write)], prefix="/api/v1/artists", tags=["Artists V2"])

# ============================================================================
# PUBLIC CONTACT FORM - No auth required
# ============================================================================
app.include_router(events_router, prefix="/api/v1", tags=["Events"])
app.include_router(public_contact_router, prefix="/api/v1", tags=["Public Contact"])

# Progress streaming (SSE)
app.include_router(progress_router, prefix="/api/v1", tags=["Progress"])

# WebSocket routes (no prefix - handled directly at /ws/)
app.include_router(websocket_router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    # Database tables are managed by Alembic migrations
    # No need for create_all() - it causes conflicts with existing indexes
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")
