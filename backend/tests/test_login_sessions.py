"""Session revocation, account boundaries and fixed, explicitly opted-in browser trust."""
from datetime import datetime, timedelta
from uuid import uuid4
import pytest
from app.core import mfa
from app.core.security import decode_token, create_access_token, create_refresh_token, get_password_hash
from app.core.login_sessions import COOKIE
from app.db.models.login_session import UserSession, TrustedDevice


@pytest.fixture(autouse=True)
def reset_limits(actors, db_session):
    for user in actors[0]:
        user.email = f"sessions-{user.id}@example.com"
    db_session.commit()
    from app.core.security_middleware import rate_limiter
    rate_limiter.requests.clear()
    rate_limiter.blocked_ips.clear()


def session(db, user):
    tokens = mfa.issue_tokens(user)
    db.commit()
    return {'Authorization': 'Bearer ' + tokens['access_token']}, tokens


def test_revoke_one_and_all_others_preserves_current_and_other_accounts(client, db_session, actors):
    user, other = actors[0][:2]
    current, _ = session(db_session, user)
    second, tokens = session(db_session, user)
    foreign, foreign_tokens = session(db_session, other)
    sid = decode_token(tokens['access_token'])['sid']
    foreign_sid = decode_token(foreign_tokens['access_token'])['sid']
    rows = client.get('/api/v1/auth/sessions', headers=current).json()['items']
    assert len(rows) == 2 and sum(row['is_current'] for row in rows) == 1
    assert client.delete('/api/v1/auth/sessions/' + foreign_sid, headers=current).status_code == 404
    current_id = next(row['id'] for row in rows if row['is_current'])
    assert client.delete('/api/v1/auth/sessions/' + current_id, headers=current).status_code == 409
    assert client.delete('/api/v1/auth/sessions/' + sid, headers=current).status_code == 200
    assert client.get('/api/v1/auth/me', headers=second).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    session(db_session, user)
    assert client.post('/api/v1/auth/sessions/revoke-others', headers=current).json()['revoked'] == 1
    assert client.get('/api/v1/auth/me', headers=current).status_code == 200
    assert client.get('/api/v1/auth/me', headers=foreign).status_code == 200
    assert client.post('/api/v1/auth/sessions/revoke-others', headers=current).json()['revoked'] == 0


def test_logout_expiry_and_untracked_tokens(client, db_session, actors):
    user = actors[0][0]
    header, tokens = session(db_session, user)
    refreshed = client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert refreshed.status_code == 200
    assert decode_token(refreshed.json()['access_token'])['sid'] == decode_token(tokens['access_token'])['sid']
    assert client.post('/api/v1/auth/logout', headers=header).status_code == 200
    assert client.get('/api/v1/auth/me', headers=header).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': refreshed.json()['refresh_token']}).status_code == 401
    legacy = create_access_token({'sub': str(user.id)})
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + legacy}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': create_refresh_token({'sub': str(user.id)})}).status_code == 401
    header, tokens = session(db_session, user)
    db_session.query(UserSession).filter(UserSession.id == decode_token(tokens['access_token'])['sid']).update({'expires_at': datetime.utcnow() - timedelta(seconds=1)})
    db_session.commit()
    assert client.get('/api/v1/auth/me', headers=header).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401


def test_sessions_require_authentication(client):
    for method, path in [('get', '/sessions'), ('post', '/sessions/revoke-others'), ('delete', '/sessions/' + str(uuid4())), ('get', '/trusted-devices'), ('post', '/trusted-devices/revoke-all')]:
        assert getattr(client, method)('/api/v1/auth' + path).status_code == 401


def prepare_mfa(db, user):
    user.hashed_password = get_password_hash('Disposable-Session-42!')
    user.two_factor_enabled = True
    user.two_factor_secret = 'JBSWY3DPEHPK3PXP'
    codes = mfa.new_recovery(user)
    db.commit()
    return codes


def login(client, user):
    response = client.post('/api/v1/auth/login', json={'email': user.email, 'password': 'Disposable-Session-42!'})
    assert response.status_code == 200, response.text
    return response.json()


def complete(client, pending, code, trust=False):
    return client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending['temp_token'], 'method': 'recovery', 'code': code, 'trust_device': trust})


def install_cookie(client, response):
    # The application correctly never sends this Secure cookie over plain HTTP.
    client.cookies.set(COOKIE, response.cookies[COOKIE], path='/api/v1/auth')


def test_trust_is_opt_in_secure_fixed_and_revocable(client, db_session, actors):
    user = actors[0][0]
    codes = prepare_mfa(db_session, user)
    response = complete(client, login(client, user), codes[0])
    assert response.status_code == 200 and 'set-cookie' not in response.headers
    assert db_session.query(TrustedDevice).count() == 0
    response = complete(client, login(client, user), codes[1], trust=True)
    assert response.status_code == 200, response.text
    cookie = response.headers['set-cookie']
    for attribute in ['HttpOnly', 'Secure', 'SameSite=lax', 'Max-Age=2592000', 'Path=/api/v1/auth']:
        assert attribute in cookie
    row = db_session.query(TrustedDevice).one()
    assert row.token_hash != response.cookies[COOKIE]
    expires = row.expires_at
    install_cookie(client, response)
    assert login(client, user)['requires_2fa'] is False
    db_session.refresh(row)
    assert row.expires_at == expires
    header = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert client.post('/api/v1/auth/logout', headers=header).status_code == 200
    result = login(client, user)  # Normal logout preserves the explicit trust authorization.
    assert result['requires_2fa'] is False
    header = {'Authorization': 'Bearer ' + result['access_token']}
    listed = client.get('/api/v1/auth/trusted-devices', headers=header).json()['items']
    assert len(listed) == 1 and listed[0]['is_current'] is True
    assert client.delete('/api/v1/auth/trusted-devices/' + str(row.id), headers=header).status_code == 200
    assert login(client, user)['requires_2fa'] is True
    assert client.get('/api/v1/auth/me', headers=header).status_code == 200


def test_trust_cannot_be_minted_with_bad_code_or_reused_across_users_ua_or_expiry(client, db_session, actors):
    user, other = actors[0][:2]
    codes = prepare_mfa(db_session, user)
    prepare_mfa(db_session, other)
    pending = login(client, user)
    assert complete(client, pending, 'INVALID-RECOVERY-CODE', trust=True).status_code == 401
    assert db_session.query(TrustedDevice).count() == 0
    response = complete(client, pending, codes[0], trust=True)
    assert response.status_code == 200
    install_cookie(client, response)
    assert login(client, other)['requires_2fa'] is True
    ua = client.headers['user-agent']
    client.headers['user-agent'] = 'Different browser'
    assert login(client, user)['requires_2fa'] is True
    client.headers['user-agent'] = ua
    row = db_session.query(TrustedDevice).one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert login(client, user)['requires_2fa'] is True


def test_sso_pending_challenge_can_use_browser_trust_once(client, db_session, actors):
    user = actors[0][0]
    codes = prepare_mfa(db_session, user)
    response = complete(client, login(client, user), codes[0], trust=True)
    install_cookie(client, response)
    token, _ = mfa.create_challenge(db_session, user, 'login')
    db_session.commit()
    result = client.post('/api/v1/auth/mfa/trusted/complete', json={'challenge_token': token})
    assert result.status_code == 200 and result.json()['trusted'] is True
    assert client.post('/api/v1/auth/mfa/trusted/complete', json={'challenge_token': token}).status_code == 401
    user.mfa_version += 1
    db_session.commit()
    assert login(client, user)['requires_2fa'] is True


def test_session_cannot_be_claimed_by_another_signed_subject(client, db_session, actors):
    user, other = actors[0][:2]
    _, tokens = session(db_session, user)
    payload = decode_token(tokens['access_token'])
    payload['sub'] = str(other.id)
    stolen_sid = create_access_token(payload)
    assert client.get('/api/v1/auth/sessions', headers={'Authorization': 'Bearer ' + stolen_sid}).status_code == 401


def test_no_trust_sso_probe_preserves_pending_proof_and_device_lists_are_private(client, db_session, actors):
    user, other = actors[0][:2]
    codes = prepare_mfa(db_session, user)
    pending = login(client, user)
    assert client.post('/api/v1/auth/mfa/trusted/complete', json={'challenge_token': pending['temp_token']}).json() == {'trusted': False}
    response = complete(client, pending, codes[0], trust=True)
    assert response.status_code == 200
    foreign, _ = session(db_session, other)
    row = db_session.query(TrustedDevice).one()
    assert client.get('/api/v1/auth/trusted-devices', headers=foreign).json()['items'] == []
    assert client.delete('/api/v1/auth/trusted-devices/' + str(row.id), headers=foreign).status_code == 404
    header = {'Authorization': 'Bearer ' + response.json()['access_token']}
    install_cookie(client, response)
    assert client.post('/api/v1/auth/trusted-devices/revoke-all', headers=header).json()['revoked'] == 1
    assert login(client, user)['requires_2fa'] is True
