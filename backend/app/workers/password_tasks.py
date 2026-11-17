"""Recovery e-mail worker: the link secret is generated here, never in broker args."""
import asyncio
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.password_recovery import create_and_send_reset


@celery_app.task(name='app.workers.password_tasks.request_password_reset', ignore_result=True)
def request_password_reset(email):
    with SessionLocal() as db:
        asyncio.run(create_and_send_reset(db, email))
