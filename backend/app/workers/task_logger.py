"""
Task Logger - Système de logging centralisé pour les tâches Celery

Fournit:
- Logs colorés dans la console avec timestamps
- Enregistrement en base de données
- Broadcast WebSocket vers le frontend
"""
import logging
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from contextlib import contextmanager
from functools import wraps

from celery import current_task
from celery.signals import (
    task_prerun, task_postrun, task_success, task_failure,
    task_retry, task_revoked, worker_ready
)

from app.db.session import SessionLocal


# ================================================================
# CONFIGURATION LOGGING CONSOLE
# ================================================================

class Colors:
    """ANSI color codes pour la console"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Couleurs
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    
    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    STEP = "STEP"


# Mapping niveau -> couleur
LEVEL_COLORS = {
    LogLevel.DEBUG: Colors.GRAY,
    LogLevel.INFO: Colors.CYAN,
    LogLevel.WARNING: Colors.YELLOW,
    LogLevel.ERROR: Colors.RED,
    LogLevel.SUCCESS: Colors.GREEN,
    LogLevel.STEP: Colors.MAGENTA,
}

# Mapping composant -> emoji
COMPONENT_EMOJI = {
    "celery": "🔄",
    "crawler": "🕷️",
    "extractor": "📄",
    "gpt": "🤖",
    "db": "💾",
    "scoring": "📊",
    "dedup": "🔍",
    "http": "🌐",
    "email": "📧",
    "rss": "📰",
    "search": "🔎",
    "collection": "📦",
    "dossier": "📋",
    "evidence": "🔗",
    "pipeline": "⚡",
}


def get_timestamp() -> str:
    """Timestamp formaté"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def format_log(
    level: LogLevel,
    component: str,
    message: str,
    task_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Formate un message de log avec couleurs et emojis"""
    ts = get_timestamp()
    color = LEVEL_COLORS.get(level, Colors.WHITE)
    emoji = COMPONENT_EMOJI.get(component.lower(), "📝")
    
    # Task ID court
    task_short = task_id[:8] if task_id else "--------"
    
    # Format principal
    log_line = (
        f"{Colors.GRAY}[{ts}]{Colors.RESET} "
        f"{color}{Colors.BOLD}[{level.value:7}]{Colors.RESET} "
        f"{emoji} {Colors.BOLD}{component.upper():12}{Colors.RESET} "
        f"{Colors.GRAY}({task_short}){Colors.RESET} "
        f"{message}"
    )
    
    # Contexte si présent
    if context:
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        log_line += f" {Colors.GRAY}» {context_str}{Colors.RESET}"
    
    return log_line


class TaskLogger:
    """Logger centralisé pour une tâche"""
    
    def __init__(self, component: str, task_id: Optional[str] = None, collection_id: Optional[str] = None):
        self.component = component
        self.task_id = task_id or (current_task.request.id if current_task else None)
        self.collection_id = collection_id
        self.start_time = time.time()
        self._step_count = 0
        self._logger = logging.getLogger(f"radar.{component}")
    
    def _log(self, level: LogLevel, message: str, context: Dict[str, Any] = None, save_to_db: bool = False):
        """Log interne"""
        formatted = format_log(level, self.component, message, self.task_id, context)
        
        # Toujours print (visible dans docker compose logs)
        print(formatted, flush=True)
        
        # Aussi via logger Python standard
        py_level = getattr(logging, level.value if level.value != "SUCCESS" else "INFO", logging.INFO)
        self._logger.log(py_level, message, extra={"context": context})
        
        # Sauvegarde en base si collection_id
        if save_to_db and self.collection_id:
            self._save_to_db(level, message, context)
    
    def _save_to_db(self, level: LogLevel, message: str, context: Dict[str, Any] = None):
        """Enregistre le log dans collection_logs"""
        try:
            from app.db.models.collections import CollectionLog
            db = SessionLocal()
            log_entry = CollectionLog(
                collection_id=self.collection_id,
                level=level.value,
                message=message,
                context=context
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as e:
            print(f"{Colors.RED}[DB LOG ERROR] {e}{Colors.RESET}", flush=True)
    
    def debug(self, message: str, **context):
        self._log(LogLevel.DEBUG, message, context if context else None)
    
    def info(self, message: str, save: bool = False, **context):
        self._log(LogLevel.INFO, message, context if context else None, save_to_db=save)
    
    def warning(self, message: str, save: bool = True, **context):
        self._log(LogLevel.WARNING, message, context if context else None, save_to_db=save)
    
    def error(self, message: str, save: bool = True, **context):
        self._log(LogLevel.ERROR, message, context if context else None, save_to_db=save)
    
    def exception(self, message: str, save: bool = True, **context):
        """Log une exception avec traceback"""
        import traceback
        tb = traceback.format_exc()
        self._log(LogLevel.ERROR, f"{message}\n{tb}", context if context else None, save_to_db=save)
    
    def success(self, message: str, save: bool = True, **context):
        self._log(LogLevel.SUCCESS, message, context if context else None, save_to_db=save)
    
    def step(self, message: str, save: bool = False, **context):
        """Log une étape numérotée"""
        self._step_count += 1
        step_msg = f"[Étape {self._step_count}] {message}"
        self._log(LogLevel.STEP, step_msg, context if context else None, save_to_db=save)
    
    @contextmanager
    def timer(self, operation: str):
        """Context manager pour mesurer le temps d'une opération"""
        start = time.time()
        self.debug(f"Début: {operation}")
        try:
            yield
        finally:
            elapsed = time.time() - start
            self.info(f"Fin: {operation}", duration_ms=int(elapsed * 1000))
    
    def elapsed(self) -> float:
        """Temps écoulé depuis le début"""
        return time.time() - self.start_time
    
    def elapsed_str(self) -> str:
        """Temps écoulé formaté"""
        elapsed = self.elapsed()
        if elapsed < 1:
            return f"{int(elapsed * 1000)}ms"
        elif elapsed < 60:
            return f"{elapsed:.1f}s"
        else:
            return f"{int(elapsed // 60)}m {int(elapsed % 60)}s"


def get_task_logger(component: str, collection_id: str = None) -> TaskLogger:
    """Factory pour créer un TaskLogger"""
    task_id = current_task.request.id if current_task else None
    return TaskLogger(component, task_id, collection_id)


# ================================================================
# SIGNAUX CELERY - Tracking automatique des tâches
# ================================================================

@worker_ready.connect
def on_worker_ready(**kwargs):
    """Log quand le worker démarre"""
    print(f"\n{Colors.BG_GREEN}{Colors.WHITE}{Colors.BOLD} 🚀 CELERY WORKER READY {Colors.RESET}\n", flush=True)
    print(f"{Colors.GREEN}Worker démarré et prêt à recevoir des tâches{Colors.RESET}", flush=True)
    print(f"{Colors.GRAY}Queues: celery, dossier_builder_gpt, web_enrichment, ingestion_standard{Colors.RESET}\n", flush=True)


@task_prerun.connect
def on_task_prerun(task_id, task, args, kwargs, **rest):
    """Log avant l'exécution d'une tâche"""
    task_name = task.name.split('.')[-1]  # Juste le nom court
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}", flush=True)
    print(format_log(LogLevel.INFO, "celery", f"▶️  TASK START: {task_name}", task_id), flush=True)
    # Payloads can contain customer data, credentials and URLs. Log metadata only.


@task_postrun.connect  
def on_task_postrun(task_id, task, args, kwargs, retval, state, **rest):
    """Log après l'exécution d'une tâche"""
    task_name = task.name.split('.')[-1]
    color = Colors.GREEN if state == "SUCCESS" else Colors.YELLOW
    print(format_log(LogLevel.INFO, "celery", f"⏹️  TASK END: {task_name}", task_id, {"state": state}), flush=True)
    print(f"{color}{'='*60}{Colors.RESET}\n", flush=True)


@task_success.connect
def on_task_success(sender, result, **kwargs):
    """Log succès d'une tâche"""
    task_id = sender.request.id
    task_name = sender.name.split('.')[-1]
    print(format_log(LogLevel.SUCCESS, "celery", f"✅ {task_name} terminé avec succès", task_id), flush=True)
    # Never print task result bodies into shared worker logs.


@task_failure.connect
def on_task_failure(task_id, exception, traceback, einfo, **kwargs):
    """Log échec d'une tâche"""
    print(f"\n{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} ❌ TASK FAILED {Colors.RESET}", flush=True)
    print(format_log(LogLevel.ERROR, "celery", f"Exception category: {type(exception).__name__}", task_id), flush=True)
    # Error payloads may embed credentials/SQL bind values; correlate using task_id.


@task_retry.connect
def on_task_retry(request, reason, einfo, **kwargs):
    """Log retry d'une tâche"""
    print(format_log(LogLevel.WARNING, "celery", f"🔄 RETRY category: {type(reason).__name__}", request.id), flush=True)


# ================================================================
# DÉCORATEUR POUR TÂCHES AVEC LOGGING AUTOMATIQUE
# ================================================================

def logged_task(component: str):
    """
    Décorateur pour ajouter le logging automatique à une tâche.
    
    Usage:
        @celery_app.task(bind=True)
        @logged_task("crawler")
        def my_task(self, log, ...):
            log.step("Doing something")
            log.info("Details", count=42)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            log = TaskLogger(component, self.request.id)
            try:
                return func(self, log, *args, **kwargs)
            except Exception as e:
                log.error(f"Task failed: {e}")
                raise
        return wrapper
    return decorator
