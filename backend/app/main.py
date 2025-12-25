"""
FastAPI Application - Opportunities Radar
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.api import (
    auth_router,
    opportunities_router,
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

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


# API routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(opportunities_router, prefix="/api/v1")
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

# WebSocket routes (no prefix - handled directly at /ws/)
app.include_router(websocket_router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    
    # Create database tables if they don't exist
    from app.db.base import Base
    from app.db.session import engine
    from app.db import models  # Import all models
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")
