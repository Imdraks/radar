"""HTTP-level callbacks: state replaces a bearer header only on the Google return."""
import json
import time
from unittest.mock import AsyncMock
import httpx
import pytest
from app.db.models.workspace import WorkspaceMember, WorkspaceRole
from app.db.models.login_session import UserSession
from app.core.security import decode_token


class StateStore:
    def __init__(self): self.values = {}
    def setex(self, key, ttl, value): self.values[key] = value; return True
    def getdel(self, key): return self.values.pop(key, None)


@pytest.fixture
def google(monkeypatch):
    from app.core.config import settings
    store = StateStore()
    monkeypatch.setattr('app.core.integration_oauth.redis_client', store)
    monkeypatch.setattr(settings, 'google_client_id', 'explicit-test-client')
    monkeypatch.setattr(settings, 'google_client_secret', 'explicit-test-secret')
    # Mock only external token/user-info calls; keep actual router dependencies,
    # Redis state serialization, session checks and database memberships.
    response = httpx.Response(200, json={'access_token': 'explicit-provider-token', 'refresh_token': 'explicit-provider-refresh', 'expires_in': 3600, 'scope': 'drive calendar'})
    profile = httpx.Response(200, json={'email': 'provider@example.com'})
    class Provider:
        post = AsyncMock(return_value=response)
        get = AsyncMock(return_value=profile)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    monkeypatch.setattr('httpx.AsyncClient', lambda *args, **kwargs: Provider())
    return store, Provider


def paths(provider):
    return ('/api/v1/drive/auth/init', '/api/v1/drive/auth/callback') if provider == 'drive' else ('/api/v1/calendar/google/init', '/api/v1/calendar/google/callback')


@pytest.mark.parametrize('provider', ['drive', 'calendar'])
def test_random_state_format_survives_query_security_filter(client, headers, google, monkeypatch, provider):
    # These random bytes produce "--" in URL-safe base64, which the query
    # security middleware rejects. Keep the middleware active in this test.
    entropy = (bytes.fromhex('fbeffb') * 11)[:32]
    monkeypatch.setattr('secrets.token_bytes', lambda n: entropy if n == 32 else bytes(n))
    init, callback = paths(provider)
    started = client.get(init, headers=headers())
    assert started.status_code == 200, started.text
    assert started.json()['state'] == entropy.hex()
    result = client.get(callback, params={'code': 'fixture', 'state': started.json()['state']}, follow_redirects=False)
    assert result.status_code == 307, result.text
    assert 'error=' not in result.headers['location']


@pytest.mark.parametrize('provider', ['drive', 'calendar'])
def test_callback_without_bearer_uses_single_use_state_and_keeps_other_routes_private(client, actors, headers, google, provider):
    init, callback = paths(provider)
    assert client.get(init).status_code == 401
    for status in ['/api/v1/drive/auth/status', '/api/v1/calendar/google/status']:
        assert client.get(status).status_code == 401
    auth = headers()
    started = client.get(init, headers=auth)
    assert started.status_code == 200, started.text
    state = started.json()['state']
    result = client.get(callback, params={'code': 'explicit-provider-code', 'state': state}, follow_redirects=False)
    assert result.status_code == 307, result.text
    assert 'error' not in result.headers['location']
    key = f"cache:google_{'workspace' if provider == 'drive' else 'calendar'}_tokens:{actors[0][0].id}"
    from app.core.credential_cache import decode
    assert 'explicit-provider-token' not in google[0].values[key]
    assert decode(key.removeprefix('cache:'),google[0].values[key])['access_token'] == 'explicit-provider-token'
    assert client.get(callback, params={'code': 'explicit-provider-code', 'state': state}).status_code == 400
    assert client.get(callback, params={'code': 'explicit-provider-code', 'state': 'x'*43}).status_code == 400
    assert google[1].post.await_count == 1


@pytest.mark.parametrize('provider', ['drive', 'calendar'])
def test_callback_rejects_expired_and_cross_provider_states(client, headers, google, provider):
    init, callback = paths(provider)
    started = client.get(init, headers=headers()).json()
    key = 'radar:integration-oauth:' + started['state']
    value = json.loads(google[0].values[key]); value['created_at'] = time.time() - 601
    google[0].values[key] = json.dumps(value)
    assert client.get(callback, params={'code': 'fixture', 'state': started['state']}).status_code == 400
    started = client.get(init, headers=headers()).json()
    other_callback = paths('calendar' if provider == 'drive' else 'drive')[1]
    assert client.get(other_callback, params={'code': 'fixture', 'state': started['state']}).status_code == 400
    assert not google[1].post.called


@pytest.mark.parametrize('provider', ['drive', 'calendar'])
@pytest.mark.parametrize('revocation', ['session', 'membership', 'mfa', 'disabled'])
def test_callback_rechecks_radar_session_account_and_workspace(client, db_session, actors, headers, google, provider, revocation):
    user = actors[0][1]
    workspace = actors[1][0]
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.MEMBER))
    db_session.commit()
    auth = headers(1)
    init, callback = paths(provider)
    started = client.get(init, headers=auth, params={'workspace_id': workspace.id}).json()
    if revocation == 'session':
        from datetime import datetime
        sid = decode_token(auth['Authorization'].removeprefix('Bearer '))['sid']
        db_session.query(UserSession).filter_by(id=sid).update({'revoked_at': datetime.utcnow()})
    elif revocation == 'membership':
        db_session.query(WorkspaceMember).filter_by(workspace_id=workspace.id, user_id=user.id).delete()
    elif revocation == 'mfa': user.mfa_version += 1
    else: user.is_active = False
    db_session.commit()
    result = client.get(callback, params={'code': 'fixture', 'state': started['state']}, follow_redirects=False)
    assert result.status_code in {401, 403}, result.text
    assert not google[1].post.called


def test_redirect_validation_and_redis_failure_are_explicit(client, headers, google):
    result = client.get('/api/v1/drive/auth/init', headers=headers(), params={'redirect': '//attacker.example'})
    assert result.status_code == 422
    google[0].setex = lambda *args: False
    result = client.get('/api/v1/drive/auth/init', headers=headers())
    assert result.status_code == 503


@pytest.mark.parametrize('provider', ['drive', 'calendar'])
def test_provider_failure_redirect_does_not_expose_private_response(client, headers, google, provider):
    init, callback = paths(provider)
    started = client.get(init, headers=headers()).json()
    google[1].post.return_value = httpx.Response(400, text='private-provider-response-token')
    result = client.get(callback, params={'code': 'fixture', 'state': started['state']}, follow_redirects=False)
    assert result.status_code == 307
    assert 'error=' in result.headers['location']
    assert 'private-provider' not in result.headers['location']


@pytest.mark.parametrize('provider', ['drive', 'calendar'])
def test_failed_token_persistence_does_not_claim_connected(client, headers, google, provider):
    init, callback = paths(provider)
    started = client.get(init, headers=headers()).json()
    google[0].setex = lambda *args: False
    result = client.get(callback, params={'code': 'fixture', 'state': started['state']}, follow_redirects=False)
    assert result.status_code == 307
    assert 'error=' in result.headers['location']
    assert 'connected=true' not in result.headers['location']
