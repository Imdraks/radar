"""Shared password policy and account-wide revocation after a credential change."""
from datetime import datetime
import re
from app.db.models.mfa import MFAChallenge
from app.db.models.login_session import UserSession, TrustedDevice

POLICY = {'min_length': 12, 'max_bytes': 72, 'uppercase': True, 'lowercase': True,
          'digit': True, 'special': True, 'reset_expiry_minutes': 15}
COMMON = {'password123!', 'password1234!', 'azerty123456!', 'qwerty123456!', 'radar12345678!'}


def validate_new_password(password):
    if len(password) < POLICY['min_length']:
        raise ValueError('Utilisez au moins 12 caractères.')
    if len(password.encode('utf-8')) > POLICY['max_bytes']:
        raise ValueError('Le mot de passe ne doit pas dépasser 72 octets UTF-8.')
    for pattern, message in [(r'[A-Z]', 'Ajoutez une majuscule (A–Z).'),
                             (r'[a-z]', 'Ajoutez une minuscule (a–z).'),
                             (r'[0-9]', 'Ajoutez un chiffre (0–9).'),
                             (r'[^\w\s]|_', 'Ajoutez un caractère spécial, par exemple !, ?, # ou _.')]:
        if not re.search(pattern, password):
            raise ValueError(message)
    if password.lower() in COMMON:
        raise ValueError('Ce mot de passe est trop courant. Choisissez une autre combinaison.')
    return password


def invalidate_credentials(db, user, preserve_session=None):
    """Keep configured MFA factors; invalidate outstanding proofs and old sessions."""
    now = datetime.utcnow()
    user.mfa_version = (user.mfa_version or 0) + 1
    sessions = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    if preserve_session is not None:
        sessions = sessions.filter(UserSession.id != preserve_session.id)
        preserve_session.auth_version = user.mfa_version
    sessions.update({'revoked_at': now}, synchronize_session=False)
    db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id, TrustedDevice.revoked_at.is_(None)).update({'revoked_at': now}, synchronize_session=False)
    db.query(MFAChallenge).filter(MFAChallenge.user_id == user.id, MFAChallenge.used_at.is_(None)).update(
        {'used_at': now, 'code_hash': None, 'pending_secret': None, 'destination': None}, synchronize_session=False)
