"""Public liveness and restricted dependency readiness checks."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis
from app.api.deps import get_current_platform_admin
from app.core.config import settings
from app.db import get_db

router = APIRouter()


@router.get('/health')
def health_check():
    return {'status':'healthy', 'timestamp':datetime.utcnow().isoformat()}


@router.get('/health/detailed', dependencies=[Depends(get_current_platform_admin)])
def detailed_health_check(db: Session = Depends(get_db)):
    checks = {'database':False, 'redis':False, 'timestamp':datetime.utcnow().isoformat()}
    try:
        db.execute(text('SELECT 1'))
        checks['database'] = True
    except Exception:
        db.rollback()
    try:
        with redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1) as cache:
            checks['redis'] = bool(cache.ping())
    except redis.RedisError:
        pass
    checks['status'] = 'healthy' if checks['database'] and checks['redis'] else 'degraded'
    return checks
