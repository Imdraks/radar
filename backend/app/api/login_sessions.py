"""Self-service session management. No client-controlled owner or current session ID."""
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db import get_db
from app.db.models.user import User
from app.db.models.login_session import UserSession, TrustedDevice
from app.core.login_sessions import require_session, claims, trusted, COOKIE, COOKIE_PATH

router = APIRouter(prefix='/auth', tags=['Account security'])


def active(db, model, user):
    return db.query(model).filter(model.user_id == user.id, model.revoked_at.is_(None),
        model.expires_at > datetime.utcnow(), model.auth_version == (user.mfa_version or 0))


def current(db, user, request):
    # Same lock order as MFA changes; revalidate after acquiring account lock.
    db.query(User).filter(User.id == user.id).with_for_update().populate_existing().one()
    return require_session(db, user, claims(request), lock=True)


def describe(row, current_id):
    return {'id': str(row.id), 'label': row.label, 'created_at': row.created_at.isoformat() + 'Z',
            'expires_at': row.expires_at.isoformat() + 'Z', 'is_current': row.id == current_id}


@router.get('/sessions')
def sessions(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = require_session(db, user, claims(request))
    return {'items': [describe(row, session.id) for row in active(db, UserSession, user).order_by(UserSession.created_at.desc()).all()]}


@router.post('/sessions/revoke-others')
def revoke_others(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = current(db, user, request)
    count = active(db, UserSession, user).filter(UserSession.id != session.id).update({'revoked_at': datetime.utcnow()}, synchronize_session=False)
    db.commit()
    return {'revoked': count}


@router.delete('/sessions/{session_id}')
def revoke(session_id: UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = current(db, user, request)
    if session.id == session_id:
        raise HTTPException(409, 'Utilisez Déconnexion pour fermer la session actuelle.')
    row = active(db, UserSession, user).filter(UserSession.id == session_id).first()
    if not row:
        raise HTTPException(404, 'Session introuvable.')
    row.revoked_at = datetime.utcnow()
    db.commit()
    return {'revoked': True}


@router.post('/logout')
def logout(request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = current(db, user, request)
    row.revoked_at = datetime.utcnow()
    db.commit()
    from app.core.browser_sessions import clear_cookies
    clear_cookies(response)
    return {'revoked': True}


@router.get('/trusted-devices')
def devices(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = trusted(db, user, request)
    return {'items': [describe(row, device.id if device else None) for row in active(db, TrustedDevice, user).order_by(TrustedDevice.created_at.desc()).all()]}


@router.delete('/trusted-devices/{device_id}')
def forget(device_id: UUID, request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current(db, user, request)
    device = trusted(db, user, request)
    row = active(db, TrustedDevice, user).filter(TrustedDevice.id == device_id).first()
    if not row:
        raise HTTPException(404, 'Appareil introuvable.')
    row.revoked_at = datetime.utcnow()
    if device and device.id == row.id:
        response.delete_cookie(COOKIE, path=COOKIE_PATH, secure=True, httponly=True, samesite='lax')
    db.commit()
    return {'revoked': True}


@router.post('/trusted-devices/revoke-all')
def forget_all(request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current(db, user, request)
    count = active(db, TrustedDevice, user).update({'revoked_at': datetime.utcnow()}, synchronize_session=False)
    response.delete_cookie(COOKIE, path=COOKIE_PATH, secure=True, httponly=True, samesite='lax')
    db.commit()
    return {'revoked': count}
