"""One-use Google integration state shared by workers, bound to the Radar session."""
import json
import secrets
import time
from urllib.parse import urlsplit
from fastapi import HTTPException
from app.core.cache import redis_client
from app.core.login_sessions import claims, require_session
from app.api.deps import resolve_workspace_id
from app.db.models.user import User

TTL = 600


def safe_redirect(path):
    path = path or '/workspace/settings'
    parsed = urlsplit(path)
    if not path.startswith('/') or path.startswith('//') or '\\' in path or parsed.netloc or parsed.scheme or any(ord(c) < 32 for c in path):
        raise HTTPException(422, 'Chemin de retour non autorisé.')
    return path


def issue(db, user, workspace, request, provider, redirect=None):
    session = require_session(db, user, claims(request))
    state = secrets.token_urlsafe(32)
    payload = {'user_id': user.id, 'workspace_id': workspace.id, 'sid': str(session.id),
               'mfa_ver': user.mfa_version or 0, 'provider': provider,
               'created_at': time.time(), 'redirect': safe_redirect(redirect)}
    try:
        if not redis_client.setex('radar:integration-oauth:' + state, TTL, json.dumps(payload)):
            raise RuntimeError('State not persisted')
    except Exception:
        raise HTTPException(503, 'La connexion Google est temporairement indisponible.') from None
    return state


def validate_context(db, payload):
    user = db.query(User).filter_by(id=payload['user_id']).populate_existing().first()
    if not user or not user.is_active or not (user.is_whitelisted or user.is_superuser) or (user.mfa_version or 0) != payload['mfa_ver']:
        raise HTTPException(403, 'Accès au compte révoqué.')
    require_session(db, user, payload)
    resolve_workspace_id(db, user, payload['workspace_id'])
    return user


def consume(db, state, provider):
    if not isinstance(state, str) or not 32 <= len(state) <= 128:
        raise HTTPException(400, 'Autorisation Google invalide ou expirée.')
    try:
        raw = redis_client.getdel('radar:integration-oauth:' + state)
    except Exception:
        raise HTTPException(503, 'La connexion Google est temporairement indisponible.') from None
    try:
        payload = json.loads(raw) if raw else None
        if not payload or payload['provider'] != provider or not 0 <= time.time() - payload['created_at'] <= TTL:
            raise ValueError('Expired')
        safe_redirect(payload['redirect'])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, 'Autorisation Google invalide ou expirée.') from None
    validate_context(db, payload)
    return payload


def save_tokens(db, payload, key, tokens):
    validate_context(db, payload)  # Recheck after the external round trip too.
    try:
        if not redis_client.setex('cache:' + key, 86400 * 30, json.dumps(tokens)):
            raise RuntimeError('Tokens not persisted')
    except Exception:
        raise HTTPException(503, 'Les autorisations Google n’ont pas pu être enregistrées.') from None
