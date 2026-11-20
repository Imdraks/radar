"""An ID-only job acknowledges the first human opening, never form submission."""

import asyncio
from uuid import UUID
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.contact_acknowledgement import deliver_open_acknowledgement


@celery_app.task(
    name="app.workers.contact_tasks.acknowledge_opened_request", ignore_result=True
)
def acknowledge_opened_request(request_id):
    with SessionLocal() as db:
        asyncio.run(deliver_open_acknowledgement(db, UUID(request_id)))
