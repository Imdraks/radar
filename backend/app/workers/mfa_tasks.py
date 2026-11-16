"""Remove expired proofs after a short retention period; never touch active factors."""
from datetime import datetime, timedelta
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.mfa import MFAChallenge


def purge_challenges(db):
    count = db.query(MFAChallenge).filter(MFAChallenge.expires_at < datetime.utcnow() - timedelta(hours=24)).delete(synchronize_session=False)
    db.commit()
    return count


@celery_app.task(name='app.workers.mfa_tasks.purge_expired')
def purge_expired():
    with SessionLocal() as db:
        return {'deleted': purge_challenges(db)}
