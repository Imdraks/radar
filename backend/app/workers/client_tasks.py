"""Only invitation IDs enter the broker; never a plaintext password or reset token."""

import asyncio
from uuid import UUID
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.client_provisioning import deliver_invitation


@celery_app.task(
    name="app.workers.client_tasks.send_client_invitation", ignore_result=True
)
def send_client_invitation(invitation_id):
    with SessionLocal() as db:
        asyncio.run(deliver_invitation(db, UUID(invitation_id)))
