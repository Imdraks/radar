"""
Celery application configuration
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "opportunities_radar",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks",
        "app.workers.collection_tasks",
        "app.workers.ai_collection",
        "app.workers.dossier_tasks",
        "app.workers.auto_radar_task",
        "app.workers.radar_features_tasks",
        "app.workers.agency_automations",
        "app.workers.discovery_pipeline",
        "app.workers.discovery_scheduler",
        "app.workers.spotify_search_pipeline",
        "app.workers.event_sync_tasks",
        "app.workers.mfa_tasks",
        "app.workers.password_tasks",
        "app.workers.client_tasks",
        "app.workers.contact_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Queue routing
    task_routes={
        'app.workers.dossier_tasks.build_dossier_task': {'queue': 'dossier_builder_gpt'},
        'app.workers.dossier_tasks.merge_enrichment_task': {'queue': 'dossier_builder_gpt'},
        'app.workers.dossier_tasks.web_enrich_task': {'queue': 'web_enrichment'},
        'app.workers.tasks.run_ingestion_task': {'queue': 'ingestion_standard'},
    },
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "purge-expired-mfa-challenges": {
        "task": "app.workers.mfa_tasks.purge_expired",
        "schedule": crontab(minute='15', hour='4'),
    },
    # 🎯 AUTO RADAR - Récolte automatique toutes les 15 minutes
    "auto-radar-harvest": {
        "task": "app.workers.auto_radar_task.auto_radar_harvest",
        "schedule": crontab(minute="*/15"),
    },
    # Email ingestion every 5 minutes
    "ingest-emails": {
        "task": "app.workers.tasks.run_email_ingestion",
        "schedule": crontab(minute=f"*/{settings.imap_poll_interval_minutes}"),
    },
    # Web ingestion every 6 hours
    "ingest-web-sources": {
        "task": "app.workers.tasks.run_web_ingestion",
        "schedule": crontab(
            minute="0",
            hour=f"*/{settings.ingestion_web_interval_hours}"
        ),
    },
    # Check for notifications every 15 minutes
    "check-notifications": {
        "task": "app.workers.tasks.check_and_send_notifications",
        "schedule": crontab(minute="*/15"),
    },
    # Auto-build dossiers for top opportunities daily at 2am
    "auto-build-dossiers": {
        "task": "app.workers.dossier_tasks.auto_build_top_dossiers_task",
        "schedule": crontab(minute="0", hour="2"),
        "kwargs": {"score_threshold": 70, "limit": 20},
    },
    # ============================================================================
    # RADAR FEATURES - Nouvelles fonctionnalités
    # ============================================================================
    # 🌅 Daily Shortlist - Génération quotidienne à 08h00
    "daily-shortlist-generation": {
        "task": "app.workers.radar_features_tasks.daily_shortlist_job",
        "schedule": crontab(minute="0", hour="8"),
    },
    # 🔄 Cluster Rebuild - Reconstruction nocturne à 03h00
    "cluster-rebuild-nightly": {
        "task": "app.workers.radar_features_tasks.cluster_rebuild_job",
        "schedule": crontab(minute="0", hour="3"),
    },
    # ⏰ Deadline Guard - Vérification quotidienne à 07h00
    "deadline-guard-check": {
        "task": "app.workers.radar_features_tasks.deadline_guard_job",
        "schedule": crontab(minute="0", hour="7"),
    },
    # 🏥 Source Health Rollup - Calcul quotidien à 01h00
    "source-health-rollup": {
        "task": "app.workers.radar_features_tasks.source_health_rollup_job",
        "schedule": crontab(minute="0", hour="1"),
    },
    # ========================================================================
    # AGENCY AUTOMATIONS V3 - Relances et alertes automatiques
    # ========================================================================
    # 🔔 Auto Followup Deals - Relances automatiques à 08h00
    "agency-auto-followup-deals": {
        "task": "app.workers.agency_automations.auto_followup_deals",
        "schedule": crontab(minute="0", hour="8"),
    },
    # 🚨 Deadline Alerts - Alertes deadlines à 07h00
    "agency-deadline-alerts": {
        "task": "app.workers.agency_automations.deadline_alerts",
        "schedule": crontab(minute="0", hour="7"),
    },
    # 🛑 Blocked Project Alerts - Alertes projets bloqués à 09h00
    "agency-blocked-project-alerts": {
        "task": "app.workers.agency_automations.blocked_project_alerts",
        "schedule": crontab(minute="0", hour="9"),
    },
    # 🧹 Cleanup Old Auto Tasks - Nettoyage hebdo dimanche 02h00
    "agency-cleanup-old-auto-tasks": {
        "task": "app.workers.agency_automations.cleanup_old_auto_tasks",
        "schedule": crontab(minute="0", hour="2", day_of_week="sunday"),
    },
    # ========================================================================
    # 🎫 EVENT SYNC - Ticketmaster real events
    # ========================================================================
    # Sync Ticketmaster events every 6 hours
    "sync-ticketmaster-events": {
        "task": "app.workers.event_sync_tasks.sync_artist_events",
        "schedule": crontab(minute="0", hour="*/6"),
    },
    # Cleanup past events weekly on Sunday at 04h00
    "cleanup-past-events": {
        "task": "app.workers.event_sync_tasks.cleanup_past_events",
        "schedule": crontab(minute="0", hour="4", day_of_week="sunday"),
    },
    # ========================================================================
    # DISCOVERY V3 - Feed candidate generation
    # ========================================================================
    # Generate discovery candidates every 30 minutes
    "generate-discovery-candidates": {
        "task": "discovery.generate_candidates",
        "schedule": crontab(minute="*/30"),
    },
    # Cleanup expired candidates every 6 hours
    "cleanup-expired-candidates": {
        "task": "discovery.cleanup_expired",
        "schedule": crontab(hour="*/6"),
    },
    # Generate recommendations from artist searches every 2 hours
    "generate-discovery-recommendations": {
        "task": "discovery.generate_recommendations",
        "schedule": crontab(minute="15", hour="*/2"),
    },
}
