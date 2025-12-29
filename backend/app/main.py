"""
FastAPI Application - Radar
Lead intelligence and opportunity tracking platform
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

from app.core.config import settings

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

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    docs_url="/docs",
    redoc_url="/redoc",
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

# Add GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# Add timing middleware for performance monitoring
app.add_middleware(TimingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
    max_age=600,  # Cache preflight for 10 minutes
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check endpoints (no prefix for /health and /health/detailed)
app.include_router(health_router, tags=["Health"])


# ============================================================================
# API ROUTE REGISTRATION
# ============================================================================

# V1 Routes - Legacy (Integer IDs, Opportunity model)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(opportunities_router, prefix="/api/v1")  # Legacy /opportunities
app.include_router(sources_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(scoring_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(artist_history_router, prefix="/api/v1/artist-history", tags=["Artist History"])
app.include_router(enrichment_router, prefix="/api/v1", tags=["Artist Enrichment"])
app.include_router(sso_router, prefix="/api/v1", tags=["SSO Authentication"])
app.include_router(ai_intelligence_router, prefix="/api/v1", tags=["AI Intelligence"])
app.include_router(collection_router, prefix="/api/v1", tags=["Collection"])
app.include_router(collect_router, prefix="/api/v1", tags=["Unified Collection"])
app.include_router(dossiers_router, prefix="/api/v1/dossiers", tags=["Dossiers"])

# Auto Radar - Automatic harvesting
app.include_router(radar_router, prefix="/api/v1/radar", tags=["Auto Radar"])

# Activity Logs - Superadmin only
app.include_router(activity_router, prefix="/api/v1/admin", tags=["Activity Logs"])

# V2 Routes - New architecture (UUIDs, LeadItem model)
app.include_router(collections_v2_router, prefix="/api/v2", tags=["Collections V2"])
app.include_router(leads_v2_router, prefix="/api/v2", tags=["Leads V2"])  # /api/v2/leads
app.include_router(dossiers_v2_router, prefix="/api/v2", tags=["Dossiers V2"])

# Radar Features - Advanced functionality
app.include_router(profiles_router, prefix="/api/v1", tags=["Profiles"])
app.include_router(shortlists_router, prefix="/api/v1", tags=["Shortlists"])
app.include_router(clusters_router, prefix="/api/v1", tags=["Clusters"])
app.include_router(deadlines_router, prefix="/api/v1", tags=["Deadlines"])
app.include_router(source_health_router, prefix="/api/v1", tags=["Source Health"])
app.include_router(contact_finder_router, prefix="/api/v1", tags=["Contact Finder"])

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
