"""Account-scoped MFA enrollment, step-up and two-stage login."""
from datetime import datetime
from typing import Literal
import re
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db import get_db
from app.db.models.user import User
from app.core import mfa
from app.core.encryption import encrypt_sensitive, decrypt_sensitive
from app.core.security import decode_token, verify_password
from app.services.mfa_delivery import availability
from app.core.activity_logger import ActivityLogger

router = APIRouter(prefix='/auth/mfa', tags=['Account security'])
Method = Literal['totp', 'email', 'sms', 'recovery']


class ChallengeInput(BaseModel):
    challenge_token: str = Field(min_length=32, max_length=128)


class CodeInput(ChallengeInput):
    method: Method
    code: str = Field(min_length=6, max_length=40)


class LoginCodeInput(CodeInput):
    trust_device: bool = False


class SendInput(ChallengeInput):
    method: Literal['email', 'sms']


class ReauthInput(BaseModel):
    password: str | None = Field(default=None, max_length=128)


class EnrollmentInput(BaseModel):
    management_token: str = Field(min_length=32, max_length=128)
    method: Literal['totp', 'email', 'sms']
    phone: str | None = Field(default=None, max_length=32)


class ManageInput(BaseModel):
    management_token: str = Field(min_length=32, max_length=128)
    method: Literal['totp', 'email', 'sms'] | None = None


@router.get('/status')
def status(user: User = Depends(get_current_user)):
    return {'enabled': bool(mfa.methods(user)), **mfa.options(user), 'available': availability(),
            'has_backup_codes': bool(user.backup_codes)}


@router.post('/options')
def login_options(data: ChallengeInput, db: Session = Depends(get_db)):
    user, row = mfa.load_challenge(db, data.challenge_token, {'login'})
    return {**mfa.options(user), 'available': availability(), 'expires_at': row.expires_at}


@router.post('/send')
async def send(data: SendInput, db: Session = Depends(get_db)):
    user, row = mfa.load_challenge(db, data.challenge_token, {'login', 'manage', 'enroll'})
    return await mfa.send_code(db, user, row, data.method)


@router.post('/complete')
def complete(data: LoginCodeInput, request: Request, response: Response, db: Session = Depends(get_db)):
    user, row = mfa.load_challenge(db, data.challenge_token, {'login'})
    mfa.verify(db, user, row, data.method, data.code.strip())
    from app.api.auth import finish_login
    from app.core.login_sessions import authorize_browser, set_trust_cookie
    authorization = authorize_browser(db, user, request) if data.trust_device else None
    result = finish_login(db, user, request)
    if authorization:
        set_trust_cookie(response, authorization)
    return result


@router.post('/reauth/start')
def reauth_start(data: ReauthInput, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = mfa.lock_user(db, user.id)
    if user.hashed_password:
        if not data.password or not verify_password(data.password, user.hashed_password):
            _, failed = mfa.create_challenge(db, user, 'password_reauth')
            mfa.reject(db, failed, "Mot de passe Radar incorrect." if data.password else "Saisissez le mot de passe Radar de ce compte.")
    else:
        payload = decode_token(request.headers.get('authorization', '').removeprefix('Bearer ')) or {}
        authenticated_at = payload.get('auth_time', 0)
        if not isinstance(authenticated_at, int) or not 0 <= time.time() - authenticated_at <= 300:
            raise HTTPException(401, 'Reconnectez-vous avec votre fournisseur SSO avant de modifier la sécurité.')
    if mfa.methods(user):
        token, _ = mfa.create_challenge(db, user, 'manage')
        db.commit()
        return {'requires_2fa': True, 'challenge_token': token, **mfa.options(user)}
    token, _ = mfa.create_challenge(db, user, 'manage_verified')
    db.commit()
    return {'requires_2fa': False, 'management_token': token}


@router.post('/reauth/complete')
def reauth_complete(data: CodeInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user, row = mfa.load_challenge(db, data.challenge_token, {'manage'}, user.id)
    mfa.verify(db, user, row, data.method, data.code.strip())
    token, _ = mfa.create_challenge(db, user, 'manage_verified')
    db.commit()
    return {'management_token': token}


@router.post('/enroll/start')
async def enroll_start(data: EnrollmentInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user, proof = mfa.load_challenge(db, data.management_token, {'manage_verified'}, user.id)
    if data.method in mfa.methods(user):
        raise HTTPException(409, 'Cette méthode est déjà activée. Elle ne sera pas remplacée.')
    if not availability().get(data.method):
        raise HTTPException(503, 'Cette méthode n’est pas configurée sur le serveur.')
    target, secret = None, None
    if data.method == 'sms':
        if not data.phone or not re.fullmatch(r'\+[1-9][0-9]{7,14}', data.phone):
            raise HTTPException(422, 'Utilisez un numéro international E.164, par exemple +33612345678.')
        target = data.phone
    elif data.method == 'email':
        if not user.email:
            raise HTTPException(422, 'Le compte ne possède pas d’adresse e-mail.')
        target = user.email
    else:
        secret = mfa.two_factor_auth.generate_secret()
    proof.used_at = datetime.utcnow()
    token, row = mfa.create_challenge(db, user, 'enroll', data.method, target, secret)
    result = {'challenge_token': token, 'method': data.method, 'expires_at': row.expires_at}
    if secret:
        result.update(secret=secret, qr_code=mfa.two_factor_auth.generate_qr_code(secret, user.email or str(user.id)))
        db.commit()
    else:
        result.update(await mfa.send_code(db, user, row, data.method))
    return result


@router.post('/enroll/complete')
def enroll_complete(request: Request, data: CodeInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user, row = mfa.load_challenge(db, data.challenge_token, {'enroll'}, user.id)
    if row.method != data.method or data.method == 'recovery':
        raise HTTPException(422, 'Méthode de confirmation différente.')
    mfa.verify(db, user, row, data.method, data.code.strip(), enrollment=True)
    if data.method == 'totp':
        user.two_factor_enabled = True
        user.two_factor_secret = 'enc:' + row.pending_secret
    elif data.method == 'email':
        user.mfa_email_enabled, user.mfa_email = True, row.destination
    else:
        user.mfa_sms_enabled, user.mfa_phone = True, row.destination
    row.pending_secret = row.destination = None
    codes = mfa.new_recovery(user)
    user.mfa_version = (user.mfa_version or 0) + 1
    from app.core.login_sessions import current_after_security_change
    tokens = mfa.issue_tokens(user, session=current_after_security_change(db, user, request))
    ActivityLogger.log(db, user, 'mfa.method_enabled', details={'method': data.method})
    return {'enabled': True, 'backup_codes': codes, **tokens}


@router.post('/disable')
def disable(request: Request, data: ManageInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user, proof = mfa.load_challenge(db, data.management_token, {'manage_verified'}, user.id)
    if data.method not in mfa.methods(user) or data.method == 'recovery':
        raise HTTPException(422, 'Méthode non activée.')
    proof.used_at = datetime.utcnow()
    if data.method == 'totp':
        user.two_factor_enabled, user.two_factor_secret, user.mfa_totp_last_step = False, None, None
    elif data.method == 'email':
        user.mfa_email_enabled, user.mfa_email = False, None
    else:
        user.mfa_sms_enabled, user.mfa_phone = False, None
    if not any(value != 'recovery' for value in mfa.methods(user)):
        user.backup_codes = None
    user.mfa_version = (user.mfa_version or 0) + 1
    from app.core.login_sessions import current_after_security_change
    tokens = mfa.issue_tokens(user, session=current_after_security_change(db, user, request))
    ActivityLogger.log(db, user, 'mfa.method_disabled', details={'method': data.method})
    return {'enabled': bool(mfa.methods(user)), **tokens}


@router.post('/recovery/regenerate')
def regenerate(request: Request, data: ManageInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user, proof = mfa.load_challenge(db, data.management_token, {'manage_verified'}, user.id)
    if not mfa.methods(user):
        raise HTTPException(409, 'Activez d’abord une méthode de vérification.')
    proof.used_at = datetime.utcnow()
    codes = mfa.new_recovery(user)
    user.mfa_version = (user.mfa_version or 0) + 1
    from app.core.login_sessions import current_after_security_change
    tokens = mfa.issue_tokens(user, session=current_after_security_change(db, user, request))
    ActivityLogger.log(db, user, 'mfa.recovery_regenerated')
    return {'backup_codes': codes, **tokens}


@router.post('/trusted/complete')
def trusted_complete(data: ChallengeInput, request: Request, db: Session = Depends(get_db)):
    user, row = mfa.load_challenge(db, data.challenge_token, {'login'})
    from app.core.login_sessions import trusted
    if not trusted(db, user, request):
        return {'trusted': False}
    row.used_at = datetime.utcnow()
    from app.api.auth import finish_login
    return {'trusted': True, **finish_login(db, user, request).model_dump()}
