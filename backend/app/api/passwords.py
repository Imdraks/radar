"""Password recovery and authenticated change. No automatic session after recovery."""
from datetime import datetime
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, SecretStr, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models.user import User
from app.db.models.mfa import MFAChallenge
from app.db.models.activity_log import ActivityLog
from app.api.deps import get_current_user
from app.core import mfa
from app.core.passwords import POLICY, validate_new_password, invalidate_credentials
from app.core.security import get_password_hash, verify_password
from app.core.login_sessions import require_session, claims, COOKIE, COOKIE_PATH

router = APIRouter(prefix='/auth', tags=['Account security'])
logger = logging.getLogger(__name__)
ACCEPTED = {'accepted': True, 'message': 'Si un compte éligible correspond à cette adresse, une demande de réinitialisation sera traitée. Consultez vos e-mails et indésirables. Si aucun message ne vous parvient, réessayez plus tard.'}


class ForgotInput(BaseModel):
    email: EmailStr


class PasswordInput(BaseModel):
    new_password: SecretStr
    confirm_password: SecretStr


class ResetInput(PasswordInput):
    token: str = Field(min_length=32, max_length=128)


class ChangeInput(PasswordInput):
    current_password: SecretStr
    management_token: str | None = Field(default=None, min_length=32, max_length=128)


def validate(data, user):
    password = data.new_password.get_secret_value()
    if password != data.confirm_password.get_secret_value():
        raise HTTPException(422, 'Les deux nouveaux mots de passe ne correspondent pas.')
    try:
        validate_new_password(password)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    if user.hashed_password and verify_password(password, user.hashed_password):
        raise HTTPException(422, 'Choisissez un mot de passe différent du précédent.')
    return password


def audit(db, user, action):
    db.add(ActivityLog(user_id=user.id, user_tracking_id=user.tracking_id or f"USR-{str(user.id)[:6]}",
        action=action, resource_type='user', resource_id=str(user.id), details={'sessions_revoked': action != 'password.reset_requested'}))


def clear_trust(response):
    response.delete_cookie(COOKIE, path=COOKIE_PATH, secure=True, httponly=True, samesite='lax')


@router.get('/password-policy')
def policy():
    return POLICY


@router.get('/password/status')
def password_status(user: User = Depends(get_current_user)):
    return {'has_password': bool(user.hashed_password)}


@router.post('/forgot-password', status_code=202)
def forgot(data: ForgotInput):
    from app.services.password_recovery import validate_configuration
    from app.workers.password_tasks import request_password_reset
    validate_configuration()
    # Same enqueue path for every address. Provider latency cannot disclose a
    # registered account, and no raw recovery token is put in the broker.
    try:
        request_password_reset.delay(str(data.email).lower())
    except Exception:
        logger.warning('password_reset_enqueue_failed')
        raise HTTPException(503, 'La demande ne peut pas être traitée actuellement. Réessayez plus tard.') from None
    return ACCEPTED


@router.post('/reset-password')
def reset(data: ResetInput, response: Response, db: Session = Depends(get_db)):
    invalid = HTTPException(400, 'Ce lien est invalide, a expiré ou a déjà été utilisé. Demandez un nouveau lien.')
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    row = db.query(MFAChallenge).filter_by(token_hash=token_hash, purpose='password_reset').first()
    if not row:
        raise invalid
    # Same user-first lock order as all security mutations. Recovery is available
    # even when wrong MFA attempts temporarily block interactive step-up.
    user = db.query(User).filter_by(id=row.user_id).with_for_update().populate_existing().first()
    row = db.query(MFAChallenge).filter_by(token_hash=token_hash, purpose='password_reset').populate_existing().first()
    if not user or not user.is_active or not (user.is_whitelisted or user.is_superuser) or not row or row.used_at or row.expires_at <= datetime.utcnow() or row.auth_version != (user.mfa_version or 0):
        raise invalid
    password = validate(data, user)
    user.hashed_password = get_password_hash(password)
    user.must_change_password = False
    user.temporary_password_expires_at = None
    invalidate_credentials(db, user)
    audit(db, user, 'password.reset_completed')
    db.commit()
    clear_trust(response)
    return {'message': 'Mot de passe réinitialisé. Reconnectez-vous ; votre A2F reste active si elle était configurée.'}


@router.post('/password/change')
def change(data: ChangeInput, request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = mfa.lock_user(db, user.id)
    session = require_session(db, user, claims(request), lock=True)
    if not user.hashed_password:
        raise HTTPException(409, 'Ce compte ne possède pas de mot de passe Radar. Utilisez le lien envoyé par e-mail pour en définir un.')
    if not verify_password(data.current_password.get_secret_value(), user.hashed_password):
        _, failed = mfa.create_challenge(db, user, 'password_reauth')
        mfa.reject(db, failed, 'Ancien mot de passe incorrect.')
    if user.must_change_password and (not user.temporary_password_expires_at or user.temporary_password_expires_at <= datetime.utcnow()):
        raise HTTPException(401, 'Le mot de passe temporaire a expiré. Demandez une nouvelle invitation.')
    password = validate(data, user)
    if mfa.methods(user) or data.management_token:
        if not data.management_token:
            raise HTTPException(403, 'Confirmez votre identité avec votre A2F avant de changer le mot de passe.')
        _, proof = mfa.load_challenge(db, data.management_token, {'manage_verified'}, user.id)
        proof.used_at = datetime.utcnow()
    user.hashed_password = get_password_hash(password)
    user.must_change_password = False
    user.temporary_password_expires_at = None
    invalidate_credentials(db, user, preserve_session=session)
    tokens = mfa.issue_tokens(user, session=session)
    audit(db, user, 'password.changed')
    db.commit()
    clear_trust(response)
    return {**tokens, 'message': 'Mot de passe modifié. Les autres sessions ont été déconnectées.'}
