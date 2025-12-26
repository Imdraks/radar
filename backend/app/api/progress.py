"""
Progress Streaming Endpoint - SSE pour les mises à jour en temps réel

Ce module fournit un endpoint SSE (Server-Sent Events) qui écoute 
le canal Redis et transmet les mises à jour au frontend.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, Set

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.security import verify_token
from app.workers.progress_notifier import PROGRESS_CHANNEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/progress", tags=["Progress"])


# Store active subscribers per task_id
active_subscribers: dict[str, Set[asyncio.Queue]] = {}


async def subscribe_to_task_progress(
    task_ids: list[str],
    timeout: float = 120.0
) -> AsyncGenerator[dict, None]:
    """
    Générateur async qui écoute Redis et yield les messages de progression.
    
    Args:
        task_ids: Liste des task_ids à surveiller
        timeout: Timeout en secondes pour la connexion SSE
    """
    redis_client = aioredis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    
    try:
        await pubsub.subscribe(PROGRESS_CHANNEL)
        logger.info(f"Subscribed to {PROGRESS_CHANNEL} for tasks: {task_ids}")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.info(f"SSE timeout after {elapsed}s")
                break
            
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0
                )
                
                if message and message.get("type") == "message":
                    data = json.loads(message["data"])
                    
                    # Filtrer par task_ids si spécifiés
                    if not task_ids or data.get("task_id") in task_ids:
                        yield data
                        
                        # Arrêter si la tâche est terminée
                        if data.get("type") in ("completed", "failed"):
                            logger.info(f"Task {data.get('task_id')} finished, closing stream")
                            break
                            
            except asyncio.TimeoutError:
                # Send heartbeat
                yield {"type": "heartbeat", "timestamp": asyncio.get_event_loop().time()}
                
    except Exception as e:
        logger.error(f"Redis subscription error: {e}")
        yield {"type": "error", "message": str(e)}
    finally:
        await pubsub.unsubscribe(PROGRESS_CHANNEL)
        await redis_client.close()
        logger.info("Closed Redis subscription")


async def event_generator(
    task_ids: list[str],
    token: str
) -> AsyncGenerator[dict, None]:
    """Génère les événements SSE"""
    # Verify token
    user_id = verify_token(token, "access")
    if not user_id:
        yield {
            "event": "error",
            "data": json.dumps({"error": "Invalid or expired token"})
        }
        return
    
    # Send initial connection event
    yield {
        "event": "connected",
        "data": json.dumps({
            "message": "Connected to progress stream",
            "task_ids": task_ids
        })
    }
    
    # Stream progress updates
    async for update in subscribe_to_task_progress(task_ids):
        event_type = update.get("type", "progress")
        yield {
            "event": event_type,
            "data": json.dumps(update)
        }


@router.get("/stream")
async def stream_progress(
    request: Request,
    token: str = Query(..., description="JWT token for authentication"),
    task_ids: Optional[str] = Query(None, description="Comma-separated task IDs to monitor")
):
    """
    Server-Sent Events endpoint pour la progression des tâches.
    
    Usage frontend:
    ```javascript
    const eventSource = new EventSource(
        `/api/progress/stream?token=${token}&task_ids=${taskId}`
    );
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Progress:', data);
    };
    
    eventSource.addEventListener('completed', (event) => {
        const data = JSON.parse(event.data);
        console.log('Task completed:', data);
        eventSource.close();
    });
    ```
    """
    task_id_list = task_ids.split(",") if task_ids else []
    
    return EventSourceResponse(
        event_generator(task_id_list, token),
        media_type="text/event-stream"
    )


@router.get("/task/{task_id}")
async def get_task_progress(
    task_id: str,
    token: str = Query(..., description="JWT token for authentication")
):
    """
    Get current stored progress for a task from Redis.
    
    Cette route retourne la dernière progression connue d'une tâche
    stockée dans Redis (utile pour récupérer l'état après une déconnexion).
    """
    user_id = verify_token(token, "access")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        
        # Try to get stored progress
        stored_progress = await redis_client.get(f"task_progress:{task_id}")
        await redis_client.close()
        
        if stored_progress:
            return json.loads(stored_progress)
        
        return {
            "task_id": task_id,
            "type": "unknown",
            "message": "No progress data available",
            "progress": 0
        }
        
    except Exception as e:
        logger.error(f"Error getting task progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))
