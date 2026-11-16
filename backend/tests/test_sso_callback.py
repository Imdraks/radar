"""Exercise the HTTP callback after a simulated Google identity-provider response."""
from urllib.parse import urlparse, parse_qs
from unittest.mock import AsyncMock, Mock
import pytest
from app.core.security import decode_token
from app.db.models.mfa import MFAChallenge
from app.db.models.login_session import UserSession


@pytest.mark.parametrize('mfa_enabled', [False, True])
def test_google_callback_passes_request_and_enforces_mfa(client, db_session, actors, monkeypatch, mfa_enabled):
    from app.core.sso import SSOService
    user = actors[0][0]
    user.email = 'google-callback@example.com'
    user.two_factor_enabled = mfa_enabled
    user.two_factor_secret = 'JBSWY3DPEHPK3PXP' if mfa_enabled else None
    db_session.commit()
    monkeypatch.setattr('app.api.sso.get_oauth_state', lambda state: {'provider': 'google'})
    monkeypatch.setattr('app.services.email_whitelist.is_email_allowed', lambda db, email: (True, 'test'))
    monkeypatch.setattr('app.core.cache.cache_set', lambda *args, **kwargs: None)
    monkeypatch.setattr('app.workers.tasks.ensure_drive_structure_task.delay', Mock())
    monkeypatch.setattr(SSOService, 'exchange_google_code', AsyncMock(return_value={
        'id_token': 'explicit-google-fixture', 'access_token': 'explicit-provider-token', 'expires_in': 3600}))
    monkeypatch.setattr(SSOService, 'decode_google_id_token', lambda self, token: {
        'sub': 'explicit-google-account', 'email': user.email, 'email_verified': True, 'name': 'TEST Google'})
    response = client.get('/api/v1/auth/sso/google/callback', params={'code': 'explicit-code', 'state': 'explicit-state'},
        headers={'User-Agent': 'Mozilla/5.0 Chrome/130.0 Linux'}, follow_redirects=False)
    assert response.status_code == 307
    location = response.headers['location']
    assert 'sso_failed' not in location
    values = parse_qs(urlparse(location).fragment)
    if mfa_enabled:
        assert 'mfa_token' in values and 'access_token' not in values
        assert db_session.query(MFAChallenge).filter_by(user_id=user.id, purpose='login').count() == 1
        assert db_session.query(UserSession).filter_by(user_id=user.id).count() == 0
    else:
        token = values['access_token'][0]
        assert decode_token(token)['sid']
        row = db_session.query(UserSession).filter_by(user_id=user.id).one()
        assert row.label == 'Chrome · Linux'
        assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 200
