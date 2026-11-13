"""
WebSocket endpoint for real-time notifications
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from app.api.deps import get_current_user, resolve_workspace_id
from app.db import get_db
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections per user"""
    
    def __init__(self):
        # Map user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and store a new connection"""
        await websocket.accept(subprotocol="radar")
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a connection"""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a specific user"""
        async with self._lock:
            connections = self.active_connections.get(user_id, set()).copy()
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
    
    async def broadcast(self, workspace_id: int, message: dict):
        """Send a message to all connected users"""
        async with self._lock:
            all_connections = [
                ws for key, connections in self.active_connections.items()
                if key.startswith(f"{workspace_id}:") for ws in connections
            ]
        
        for websocket in all_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
    
    def get_connected_users(self) -> list:
        """Get list of connected user IDs"""
        return list(self.active_connections.keys())


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.
    
    Authenticate using the radar and bearer.<jwt> WebSocket subprotocols.
    
    Messages sent to client:
    - {"type": "connected", "message": "Connected to notifications"}
    - {"type": "notification", "notification_type": "...", "title": "...", "message": "..."}
    - {"type": "ping"}
    """
    try:
        protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        token = next((p.strip()[7:] for p in protocols if p.strip().startswith("bearer.")), "")
        user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
        selected = websocket.query_params.get("workspace_id")
        if selected is not None and (not selected.isdecimal() or len(selected) > 10):
            raise HTTPException(400, "Invalid workspace")
        workspace_id = resolve_workspace_id(db, user, int(selected) if selected else None)
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid or inactive account")
        return
    user_id = f"{workspace_id}:{user.id}"

    # Connect
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notifications",
            "user_id": str(user.id)
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (or use as heartbeat)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout for ping/pong
                )
                
                # Recheck account, token expiry and membership on every heartbeat.
                db.expire_all()
                try:
                    current = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
                    resolve_workspace_id(db, current, workspace_id)
                except HTTPException:
                    await websocket.close(code=4001, reason="Session expired or access revoked")
                    break
                # Handle ping from client
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                # Quiet clients are also revalidated; heartbeat cannot keep a revoked account alive.
                try:
                    db.expire_all()
                    current = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
                    resolve_workspace_id(db, current, workspace_id)
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await manager.disconnect(websocket, user_id)


# Helper functions for sending notifications from other parts of the app
async def send_notification_to_user(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    opportunity_id: str = None,
    priority: str = "medium",
    *, workspace_id: int,
):
    """Send a notification to a specific user"""
    await manager.send_to_user(f"{workspace_id}:{user_id}", {
        "type": "notification",
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "opportunity_id": opportunity_id,
        "priority": priority
    })


async def broadcast_notification(
    notification_type: str,
    title: str,
    message: str,
    opportunity_id: str = None,
    priority: str = "medium",
    *, workspace_id: int,
):
    """Broadcast a notification to all connected users"""
    await manager.broadcast(workspace_id, {
        "type": "notification",
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "opportunity_id": opportunity_id,
        "priority": priority
    })
