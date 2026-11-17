"""
Redis caching utilities for performance optimization
"""
import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
import redis
from app.core.config import settings

# Initialize Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

redis_client = redis.Redis(connection_pool=redis_pool)


def get_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments"""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cache_result(prefix: str, ttl: int = 300):
    """
    Decorator to cache function results in Redis
    
    Args:
        prefix: Cache key prefix (e.g., "dashboard", "opportunities")
        ttl: Time to live in seconds (default 5 minutes)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"cache:{prefix}:{get_cache_key(*args[1:], **kwargs)}"  # Skip 'self' or 'db'
            
            try:
                # Try to get from cache
                cached = redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # Redis error, continue without cache
            
            # Execute function
            result = func(*args, **kwargs)
            
            try:
                # Store in cache
                redis_client.setex(key, ttl, json.dumps(result, default=str))
            except Exception:
                pass  # Redis error, continue without caching
            
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str):
    """Invalidate all cache keys with given prefix"""
    try:
        batch = []
        for key in redis_client.scan_iter(match=f"cache:{prefix}:*", count=200):
            batch.append(key)
            if len(batch) == 200:
                redis_client.delete(*batch)
                batch.clear()
        if batch:
            redis_client.delete(*batch)
    except Exception:
        pass


def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    try:
        cached = redis_client.get(f"cache:{key}")
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


def cache_set(key: str, value: Any, ttl: int = 300):
    """Set value in cache"""
    try:
        redis_client.setex(f"cache:{key}", ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete(key: str):
    """Delete value from cache"""
    try:
        redis_client.delete(f"cache:{key}")
    except Exception:
        pass
