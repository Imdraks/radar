"""Authenticated, explicitly selected task progress. Redis ownership expires after 24h."""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

from app.api.deps import get_current_user, resolve_workspace_id, security
from app.db import get_db
from app.core.config import settings
from app.workers.progress_notifier import PROGRESS_CHANNEL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/progress", tags=["Progress"])


def progress_identity(
    token: Optional[str] = Query(None),
    workspace_id: Optional[int] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    # EventSource cannot set Authorization; query tokens are accepted only on this router.
    if credentials is None and token:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(credentials, db)
    return user.id, resolve_workspace_id(db, user, workspace_id)


def redis_connection():
    return aioredis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=2)


async def authorize_tasks(redis_client, task_ids, identity):
    if not 1 <= len(task_ids) <= 20 or any(not task or len(task) > 100 for task in task_ids):
        raise HTTPException(422, "Select between 1 and 20 valid task IDs")
    for task_id in task_ids:
        owner = await redis_client.get(f"task_progress_owner:{task_id}")
        if not owner or json.loads(owner) != list(identity):
            raise HTTPException(404, "Task not found")


async def event_generator(redis_client, pubsub, task_ids):
    pending = set(task_ids)
    try:
        yield {"event": "connected", "data": json.dumps({"task_ids": task_ids})}
        deadline = asyncio.get_running_loop().time() + 120
        while pending and asyncio.get_running_loop().time() < deadline:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                await asyncio.sleep(0.05)
                continue
            data = json.loads(message["data"])
            if data.get("task_id") in pending:
                yield {"event": data.get("type", "progress"), "data": json.dumps(data)}
                if data.get("type") in ("completed", "failed"):
                    pending.discard(data["task_id"])
    except Exception:
        logger.exception("Task progress stream unavailable")
        yield {"event": "error", "data": json.dumps({"message": "Progress service unavailable"})}
    finally:
        await pubsub.aclose()
        await redis_client.aclose()


@router.get("/stream")
async def stream_progress(
    task_ids: str = Query(...),
    identity=Depends(progress_identity),
):
    tasks = list(dict.fromkeys(task_ids.split(",")))
    redis_client = redis_connection()
    pubsub = None
    try:
        await authorize_tasks(redis_client, tasks, identity)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(PROGRESS_CHANNEL)
    except Exception as exc:
        if pubsub is not None:
            await pubsub.aclose()
        await redis_client.aclose()
        if isinstance(exc, HTTPException):
            raise
        logger.exception("Cannot open task progress stream")
        raise HTTPException(503, "Progress service unavailable") from exc
    return EventSourceResponse(event_generator(redis_client, pubsub, tasks), headers={"Cache-Control": "no-store"})


@router.get("/task/{task_id}")
async def get_task_progress(task_id: str, identity=Depends(progress_identity)):
    redis_client = redis_connection()
    try:
        await authorize_tasks(redis_client, [task_id], identity)
        stored = await redis_client.get(f"task_progress:{task_id}")
        return json.loads(stored) if stored else {"task_id": task_id, "type": "unknown", "message": "No progress data available"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Cannot read task progress")
        raise HTTPException(503, "Progress service unavailable") from exc
    finally:
        await redis_client.aclose()
