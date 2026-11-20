"""All bearer sessions are server-revocable; browser trust never authenticates alone."""
import hashlib
import secrets
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.db.models.login_session import UserSession, TrustedDevice
from app.core.security import decode_token

COOKIE = '__Secure-radar_mfa_device'
COOKIE_PATH = '/api/v1/auth'


def browser(request):
    ua = request.headers.get('user-agent', '') if request else ''
    app = next((label for marker, label in [('RadarChatGPT', 'Radar Connect'), ('Edg/', 'Edge'), ('Firefox/', 'Firefox'), ('Chrome/', 'Chrome'), ('Safari/', 'Safari')] if marker in ua), 'Navigateur')
    os = next((label for marker, label in [('Android', 'Android'), ('iPhone', 'iOS'), ('iPad', 'iPadOS'), ('Windows', 'Windows'), ('Macintosh', 'macOS'), ('Linux', 'Linux')] if marker in ua), '')
    return app + (' · ' + os if os else '')


def claims(request):
    from app.core.browser_sessions import request_token
    return decode_token(request_token(request)) or {}


def require_session(db, user, payload, lock=False):
    try:
        sid = UUID(str(payload.get('sid', '')))
    except ValueError:
        raise HTTPException(401, 'Session expirée. Reconnectez-vous.')
    query = db.query(UserSession).filter(UserSession.id == sid, UserSession.user_id == user.id)
    if lock:
        query = query.with_for_update()
    row = query.populate_existing().first()
    if not row or row.revoked_at or row.expires_at <= datetime.utcnow() or row.auth_version != (user.mfa_version or 0):
        raise HTTPException(401, 'Session expirée ou révoquée. Reconnectez-vous.')
    return row


def current_after_security_change(db, user, request):
    # get_current_user already validated this session before the revision changes.
    sid = UUID(str(claims(request)['sid']))
    row = db.query(UserSession).filter(UserSession.id == sid, UserSession.user_id == user.id).with_for_update().populate_existing().first()
    if not row or row.revoked_at or row.expires_at <= datetime.utcnow():
        raise HTTPException(401, 'Session révoquée. Reconnectez-vous.')
    row.auth_version = user.mfa_version or 0
    return row


def trusted(db, user, request):
    token = request.cookies.get(COOKIE, '')
    if not token or len(token) > 128:
        return None
    return db.query(TrustedDevice).filter(
        TrustedDevice.token_hash == hashlib.sha256(token.encode()).hexdigest(),
        TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None),
        TrustedDevice.expires_at > datetime.utcnow(), TrustedDevice.auth_version == (user.mfa_version or 0),
        TrustedDevice.ua_hash == hashlib.sha256(request.headers.get('user-agent', '').encode()).hexdigest()).first()


def authorize_browser(db, user, request):
    # Replace this browser's old authorization; never slide its expiry on use.
    old = trusted(db, user, request)
    if old:
        old.revoked_at = datetime.utcnow()
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(days=30)
    db.add(TrustedDevice(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
        ua_hash=hashlib.sha256(request.headers.get('user-agent', '').encode()).hexdigest(),
        auth_version=user.mfa_version or 0, label=browser(request), expires_at=expiry))
    db.flush()
    return token, expiry


def set_trust_cookie(response, authorization):
    token, expiry = authorization
    response.set_cookie(COOKIE, token, max_age=30*86400, expires=expiry.replace(tzinfo=timezone.utc),
                        httponly=True, secure=True, samesite='lax', path=COOKIE_PATH)
