"""
Progress Notifier - Redis Pub/Sub pour la progression en temps réel

Ce module permet au worker Celery d'envoyer des mises à jour de progression
qui seront reçues par le backend FastAPI et transmises au frontend via WebSocket.

Canal Redis: task_progress
Format du message:
{
    "task_id": "celery-task-id-xxx",
    "type": "progress" | "step" | "completed" | "failed",
    "data": {
        "progress": 0-100,
        "message": "Description de l'étape",
        "current_step": 1,
        "total_steps": 5,
        "items_processed": 10,
        "items_total": 50,
        ...
    }
}
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Canal Redis pour les notifications de progression
PROGRESS_CHANNEL = "task_progress"


class ProgressNotifier:
    """
    Notifier de progression utilisant Redis Pub/Sub.
    
    Usage dans une tâche Celery:
        from app.workers.progress_notifier import progress_notifier
        
        @shared_task(bind=True)
        def my_task(self, collection_id):
            notifier = progress_notifier(self.request.id)
            notifier.start(total_steps=5, message="Démarrage...")
            
            # Step 1
            notifier.step(1, "Chargement des sources")
            ...
            
            # Progress update
            notifier.progress(50, items_processed=10, items_total=20)
            
            # Complete
            notifier.complete(result={"items_new": 10})
    """
    
    def __init__(self, task_id: str, collection_id: Optional[str] = None):
        self.task_id = task_id
        self.collection_id = collection_id
        self._redis: Optional[redis.Redis] = None
        self._total_steps = 1
        self._current_step = 0
        self._start_time = datetime.utcnow()
    
    @property
    def redis_client(self) -> redis.Redis:
        """Lazy initialization du client Redis"""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url)
        return self._redis
    
    def _publish(self, msg_type: str, data: Dict[str, Any]):
        """Publie un message sur le canal Redis"""
        message = {
            "task_id": self.task_id,
            "collection_id": self.collection_id,
            "type": msg_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        try:
            self.redis_client.publish(PROGRESS_CHANNEL, json.dumps(message))
            logger.debug(f"Published progress: {msg_type} - {data.get('message', '')}")
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")
    
    def start(self, total_steps: int = 1, message: str = "Démarrage..."):
        """Signal le début de la tâche"""
        self._total_steps = total_steps
        self._current_step = 0
        self._start_time = datetime.utcnow()
        self._publish("start", {
            "message": message,
            "progress": 0,
            "total_steps": total_steps,
            "current_step": 0,
        })
    
    def step(self, step_number: int, message: str, **extra):
        """Signal le début d'une nouvelle étape"""
        self._current_step = step_number
        # Calculer la progression basée sur les étapes
        progress = int((step_number - 1) / self._total_steps * 100) if self._total_steps > 0 else 0
        self._publish("step", {
            "message": message,
            "progress": progress,
            "current_step": step_number,
            "total_steps": self._total_steps,
            **extra
        })
    
    def progress(self, percent: int, message: Optional[str] = None, **extra):
        """Met à jour le pourcentage de progression"""
        data = {
            "progress": min(100, max(0, percent)),
            "current_step": self._current_step,
            "total_steps": self._total_steps,
            **extra
        }
        if message:
            data["message"] = message
        self._publish("progress", data)
    
    def log(self, message: str, level: str = "info", **extra):
        """Envoie un message de log"""
        self._publish("log", {
            "message": message,
            "level": level,
            **extra
        })
    
    def source_start(self, source_name: str, source_index: int, total_sources: int):
        """Signal le début du traitement d'une source"""
        # Progress entre 5% et 85% pour les sources
        progress = 5 + int((source_index / total_sources) * 80)
        self._publish("source", {
            "message": f"Source {source_index}/{total_sources}: {source_name}",
            "progress": progress,
            "source_name": source_name,
            "source_index": source_index,
            "total_sources": total_sources,
            "status": "processing"
        })
    
    def source_complete(self, source_name: str, items_count: int, source_index: int, total_sources: int):
        """Signal la fin du traitement d'une source"""
        progress = 5 + int(((source_index + 1) / total_sources) * 80)
        self._publish("source", {
            "message": f"✓ {source_name}: {items_count} items",
            "progress": progress,
            "source_name": source_name,
            "source_index": source_index,
            "total_sources": total_sources,
            "items_count": items_count,
            "status": "completed"
        })
    
    def source_error(self, source_name: str, error: str, source_index: int, total_sources: int):
        """Signal une erreur sur une source"""
        progress = 5 + int(((source_index + 1) / total_sources) * 80)
        self._publish("source", {
            "message": f"✗ {source_name}: {error}",
            "progress": progress,
            "source_name": source_name,
            "source_index": source_index,
            "total_sources": total_sources,
            "error": error,
            "status": "error"
        })
    
    def complete(self, message: str = "Terminé", result: Optional[Dict[str, Any]] = None):
        """Signal la fin réussie de la tâche"""
        elapsed = (datetime.utcnow() - self._start_time).total_seconds()
        self._publish("completed", {
            "message": message,
            "progress": 100,
            "elapsed_seconds": elapsed,
            "result": result or {}
        })
    
    def fail(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Signal l'échec de la tâche"""
        elapsed = (datetime.utcnow() - self._start_time).total_seconds()
        self._publish("failed", {
            "message": f"Erreur: {error}",
            "progress": 0,
            "elapsed_seconds": elapsed,
            "error": error,
            "details": details or {}
        })


def get_progress_notifier(task_id: str, collection_id: Optional[str] = None) -> ProgressNotifier:
    """Factory pour créer un ProgressNotifier"""
    return ProgressNotifier(task_id, collection_id)
