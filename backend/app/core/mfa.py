"""Database-backed MFA proofs with account locks, bounded attempts and one-use challenges."""
from datetime import datetime, timedelta
import hashlib
import hmac
import re
import secrets
import time
from fastapi import HTTPException
from sqlalchemy import func
import pyotp
from app.core.config import settings
from app.core.encryption import encrypt_sensitive, decrypt_sensitive
from app.core.security import create_access_token, create_refresh_token
from app.core.two_factor import two_factor_auth
from app.db.models.user import User
from app.db.models.mfa import MFAChallenge

TTL = timedelta(minutes=5)


def digest(value):
    return hmac.new(settings.secret_key.encode(), ('radar-mfa:' + value).encode(), hashlib.sha256).hexdigest()


def methods(user):
    result = []
    if user.two_factor_enabled:
        result.append('totp')  # Fail closed even if an enabled secret is corrupted/missing.
    if user.mfa_email_enabled:
        result.append('email')
    if user.mfa_sms_enabled:
        result.append('sms')
    if result and user.backup_codes:
        result.append('recovery')
    return result


def mask(destination, method):
    if not destination:
        return None
    if method == 'sms':
        return '••••' + destination[-4:]
    local, _, domain = destination.partition('@')
    return local[:1] + '•••@' + domain


def destination(user, method):
    return decrypt_sensitive(user.mfa_email) if method == 'email' else decrypt_sensitive(user.mfa_phone)


def options(user):
    return {'methods': methods(user), 'destinations': {method: mask(destination(user, method), method)
            for method in ['email', 'sms'] if method in methods(user)}}


def lock_user(db, user_id):
    user = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if not user or not user.is_active or not (user.is_whitelisted or user.is_superuser):
        raise HTTPException(401, 'Compte indisponible.')
    failures = db.query(func.coalesce(func.sum(MFAChallenge.attempts), 0)).filter(
        MFAChallenge.user_id == user.id, MFAChallenge.last_attempt_at > datetime.utcnow() - timedelta(minutes=10)).scalar()
    if failures >= 5:
        raise HTTPException(429, 'Trop de codes invalides. Patientez dix minutes avant de réessayer.')
    return user


def create_challenge(db, user, purpose, method=None, target=None, pending_secret=None):
    token = secrets.token_urlsafe(32)
    challenge = MFAChallenge(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
        purpose=purpose, method=method, auth_version=user.mfa_version or 0,
        destination=encrypt_sensitive(target) if target else None,
        pending_secret=encrypt_sensitive(pending_secret) if pending_secret else None,
        expires_at=datetime.utcnow() + TTL)
    db.add(challenge)
    db.flush()
    return token, challenge


def load_challenge(db, token, purposes, owner_id=None):
    row = db.query(MFAChallenge).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not row:
        raise HTTPException(401, 'Vérification expirée ou invalide. Recommencez la connexion.')
    user = lock_user(db, row.user_id)
    row = db.query(MFAChallenge).filter_by(id=row.id).populate_existing().first()
    if row is None or row.used_at or row.expires_at <= datetime.utcnow() or row.purpose not in purposes or row.auth_version != (user.mfa_version or 0) or (owner_id is not None and row.user_id != owner_id):
        raise HTTPException(401, 'Vérification expirée ou invalide. Recommencez la connexion.')
    return user, row


def reject(db, row):
    row.attempts += 1
    row.last_attempt_at = datetime.utcnow()
    db.commit()  # Persist attempts even though the HTTP request fails.
    raise HTTPException(401, 'Code invalide ou déjà utilisé.')


def totp_secret(user):
    secret = user.two_factor_secret or ''
    return decrypt_sensitive(secret[4:]) if secret.startswith('enc:') else secret


def totp_step(secret, code):
    if not secret or not re.fullmatch(r'[0-9]{6}', code):
        return None
    current = int(time.time()) // 30
    try:
        for step in [current - 1, current, current + 1]:
            if secrets.compare_digest(pyotp.TOTP(secret).at(step * 30), code):
                return step
    except Exception:
        return None
    return None


def recovery_hash(user_id, code):
    normalized = code.upper().replace('-', '').replace(' ', '')
    return 'v1:' + digest(f'recovery:{user_id}:{normalized}')


def new_recovery(user):
    codes = ['-'.join(re.findall('.{4}', secrets.token_hex(8).upper())) for _ in range(10)]
    user.backup_codes = [recovery_hash(user.id, code) for code in codes]
    return codes


def verify(db, user, row, method, code, enrollment=False):
    if method != 'recovery':
        code = code.replace(' ', '').replace('-', '')
    if not enrollment and method not in methods(user):
        reject(db, row)
    valid = False
    if method == 'totp':
        secret = decrypt_sensitive(row.pending_secret) if enrollment else totp_secret(user)
        step = totp_step(secret, code)
        valid = step is not None and (enrollment or user.mfa_totp_last_step is None or step > user.mfa_totp_last_step)
        if valid:
            user.mfa_totp_last_step = step
            if not enrollment and not (user.two_factor_secret or '').startswith('enc:'):
                user.two_factor_secret = 'enc:' + encrypt_sensitive(secret)
    elif method == 'recovery' and not enrollment:
        values = user.backup_codes if isinstance(user.backup_codes, list) else []
        hashed = [value if value.startswith('v1:') else recovery_hash(user.id, value) for value in values]
        expected = recovery_hash(user.id, code)
        valid = any(secrets.compare_digest(value, expected) for value in hashed)
        if valid:
            user.backup_codes = [value for value in hashed if not secrets.compare_digest(value, expected)]
    elif method in {'email', 'sms'}:
        valid = bool(row.method == method and row.code_hash and re.fullmatch(r'[0-9]{6}', code)
                     and secrets.compare_digest(row.code_hash, digest(f'{row.id}:{method}:{code}')))
    if not valid:
        reject(db, row)
    if isinstance(user.backup_codes, list):
        user.backup_codes = [value if value.startswith('v1:') else recovery_hash(user.id, value) for value in user.backup_codes]
    row.used_at = datetime.utcnow()
    row.code_hash = None
    return True


async def send_code(db, user, row, method):
    from app.services.mfa_delivery import deliver, availability
    if method not in {'email', 'sms'} or (row.purpose != 'enroll' and method not in methods(user)) or (row.purpose == 'enroll' and row.method != method):
        raise HTTPException(422, 'Méthode indisponible.')
    if not availability().get(method):
        raise HTTPException(503, 'Cette méthode d’envoi n’est pas configurée.')
    now = datetime.utcnow()
    last = db.query(func.max(MFAChallenge.last_sent_at)).filter(MFAChallenge.user_id == user.id).scalar()
    count = db.query(func.coalesce(func.sum(MFAChallenge.send_count), 0)).filter(
        MFAChallenge.user_id == user.id, MFAChallenge.last_sent_at > now - timedelta(hours=1)).scalar()
    if (last and last > now - timedelta(seconds=60)) or count >= 5 or row.send_count >= 3:
        raise HTTPException(429, 'Patientez avant de demander un nouveau code. Maximum cinq envois par heure.')
    target = decrypt_sensitive(row.destination) if row.purpose == 'enroll' else destination(user, method)
    if not target:
        raise HTTPException(503, 'Adresse de vérification indisponible.')
    code = f'{secrets.randbelow(1000000):06d}'
    row.method, row.code_hash = method, digest(f'{row.id}:{method}:{code}')
    row.last_sent_at, row.send_count = now, row.send_count + 1
    # Hold the account lock throughout delivery; no concurrent budget bypass.
    try:
        await deliver(method, target, code)
    except HTTPException:
        row.code_hash = None
        db.commit()  # Failed deliveries consume their rate budget too.
        raise
    db.commit()
    return {'sent': True, 'destination': mask(target, method), 'retry_after_seconds': 60,
            'expires_at': row.expires_at}


def issue_tokens(user, auth_time=None):
    authenticated_at = int(time.time()) if auth_time is None else auth_time
    data = {'sub': str(user.id), 'email': user.email,
            'role': user.role.value if hasattr(user.role, 'value') else str(user.role),
            'mfa_ver': user.mfa_version or 0, 'auth_time': authenticated_at}
    return {'access_token': create_access_token(data),
            'refresh_token': create_refresh_token({'sub': str(user.id), 'mfa_ver': user.mfa_version or 0, 'auth_time': authenticated_at}), 'token_type': 'bearer'}
