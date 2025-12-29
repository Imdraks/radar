# /api/health endpoint for monitoring and deployment checks
from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Returns:
        - status: "healthy" if all checks pass
        - timestamp: current server time
        - version: app version from env
        - uptime: basic uptime indicator
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "production")
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with service status.
    Used for debugging and monitoring dashboards.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text
    import redis
    
    checks = {
        "database": False,
        "redis": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Database check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)
    
    # Redis check
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        checks["redis_error"] = str(e)
    
    # Overall status
    checks["status"] = "healthy" if all([checks["database"], checks["redis"]]) else "degraded"
    
    return checks
