"""Worker-side creation and delivery of one-use password reset links."""
from datetime import datetime, timedelta
import logging
from urllib.parse import urlsplit
from fastapi import HTTPException
from sqlalchemy import func
from app.core.config import settings
from app.core import mfa
from app.db.models.user import User
from app.db.models.mfa import MFAChallenge
from app.db.models.activity_log import ActivityLog
from app.services.mfa_delivery import availability
from app.services.password_email import send_reset_link
logger = logging.getLogger(__name__)


def validate_configuration():
    origin = urlsplit(settings.frontend_url)
    if not availability()['email'] or origin.scheme not in {'http', 'https'} or not origin.netloc or origin.username or origin.password or origin.query or origin.fragment or (origin.scheme != 'https' and (origin.hostname not in {'localhost', '127.0.0.1'} or settings.app_env == 'production')):
        raise HTTPException(503, 'La réinitialisation par e-mail est temporairement indisponible. Contactez l’administrateur.')


async def create_and_send_reset(db, email):
    validate_configuration()
    user = db.query(User).filter(func.lower(User.email) == email.lower()).with_for_update().populate_existing().one_or_none()
    if not user or not user.is_active or not (user.is_whitelisted or user.is_superuser):
        return {'processed': True}
    now = datetime.utcnow()
    recent = db.query(MFAChallenge).filter(MFAChallenge.user_id == user.id, MFAChallenge.purpose == 'password_reset', MFAChallenge.created_at > now - timedelta(hours=1)).all()
    if len(recent) >= 5 or any(row.created_at > now - timedelta(seconds=60) for row in recent):
        return {'processed': True}
    token, row = mfa.create_challenge(db, user, 'password_reset')
    row.expires_at = now + timedelta(minutes=15)
    row.last_sent_at, row.send_count = now, 1
    # The configured origin is used; Host / forwarded headers never build this link.
    url = settings.frontend_url.rstrip('/') + '/reset-password#token=' + token
    try:
        await send_reset_link(user.email, url)
    except Exception:
        row.used_at = now
        db.commit()  # Delivery failure consumes its cooldown, never exposes account existence.
        logger.warning('password_reset_delivery_failed')
        return {'processed': True}
    db.query(MFAChallenge).filter(MFAChallenge.user_id == user.id, MFAChallenge.purpose == 'password_reset', MFAChallenge.id != row.id, MFAChallenge.used_at.is_(None)).update({'used_at': now}, synchronize_session=False)
    db.add(ActivityLog(user_id=user.id, user_tracking_id=user.tracking_id or f"USR-{str(user.id)[:6]}", action='password.reset_requested', resource_type='user', resource_id=str(user.id), details={'sessions_revoked': False}))
    db.commit()
    return {'processed': True}

