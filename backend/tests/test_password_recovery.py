"""Recovery uses simulated mail, real PostgreSQL locks and real password hashes."""
from datetime import datetime, timedelta
from urllib.parse import urlsplit, parse_qs
from unittest.mock import AsyncMock
import pytest
import pyotp
from app.core import mfa
from app.core.security import get_password_hash, verify_password, decode_token
from app.db.models.mfa import MFAChallenge
from app.db.models.login_session import UserSession
from app.db.models.activity_log import ActivityLog

OLD = 'Old-Password-42!'
NEW = 'New-Secure-Password-57!'


@pytest.fixture
def account(db_session, actors):
    user = actors[0][0]
    user.email = 'password-test@example.com'
    user.hashed_password = get_password_hash(OLD)
    db_session.commit()
    return user


@pytest.fixture
def mail(monkeypatch, db_session):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'frontend_url', 'https://radarapp.fr')
    monkeypatch.setattr('app.services.password_recovery.availability', lambda: {'email': True})
    delivery = AsyncMock()
    monkeypatch.setattr('app.services.password_recovery.send_reset_link', delivery)
    import asyncio
    from app.services.password_recovery import create_and_send_reset
    monkeypatch.setattr('app.workers.password_tasks.request_password_reset.delay', lambda email: asyncio.run(create_and_send_reset(db_session, email)))
    return delivery


def header(db, user):
    tokens = mfa.issue_tokens(user)
    db.commit()
    return {'Authorization': 'Bearer ' + tokens['access_token']}, tokens


def request_link(client, account, mail):
    response = client.post('/api/v1/auth/forgot-password', json={'email': account.email})
    assert response.status_code == 202, response.text
    return parse_qs(urlsplit(mail.call_args.args[1]).fragment)['token'][0]


def reset(client, token, password=NEW, confirm=None):
    return client.post('/api/v1/auth/reset-password', json={'token': token, 'new_password': password, 'confirm_password': password if confirm is None else confirm})


def test_link_expires_in_fifteen_minutes_hashed_and_consumed_once(client, db_session, account, mail):
    headers, tokens = header(db_session, account)
    token = request_link(client, account, mail)
    row = db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).one()
    assert row.token_hash != token and token not in row.token_hash
    assert 890 <= (row.expires_at - row.created_at).total_seconds() <= 900
    assert '/reset-password#token=' in mail.call_args.args[1]
    response = reset(client, token)
    assert response.status_code == 200, response.text
    assert 'access_token' not in response.json()
    db_session.refresh(account)
    assert verify_password(NEW, account.hashed_password)
    assert reset(client, token).status_code == 400
    assert client.get('/api/v1/auth/me', headers=headers).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': account.email, 'password': OLD}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': account.email, 'password': NEW}).status_code == 200
    logs = db_session.query(ActivityLog).filter(ActivityLog.action.like('password.%')).all()
    assert len(logs) == 2 and all(token not in str(log.details) and NEW not in str(log.details) for log in logs)


def test_expired_wrong_purpose_revision_and_invalid_links_fail(client, db_session, account, mail):
    token = request_link(client, account, mail)
    row = db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert reset(client, token).status_code == 400
    row.expires_at = datetime.utcnow() + timedelta(minutes=5)
    account.mfa_version += 1
    db_session.commit()
    assert reset(client, token).status_code == 400
    token, _ = mfa.create_challenge(db_session, account, 'login')
    db_session.commit()
    assert reset(client, token).status_code == 400
    assert reset(client, 'x'*43).status_code == 400


def test_unknown_disabled_and_delivery_failure_share_generic_response(client, db_session, account, mail):
    mail.side_effect = RuntimeError('private provider body and credential')
    known = client.post('/api/v1/auth/forgot-password', json={'email': account.email})
    unknown = client.post('/api/v1/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json() and 'private' not in known.text
    row = db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).one()
    assert row.used_at and row.send_count == 1
    account.is_active = False
    db_session.commit()
    inactive = client.post('/api/v1/auth/forgot-password', json={'email': account.email})
    assert inactive.json() == unknown.json()
    assert mail.call_count == 1


def test_missing_mail_configuration_fails_for_all_addresses(client, account, monkeypatch):
    monkeypatch.setattr('app.services.password_recovery.availability', lambda: {'email': False})
    for email in [account.email, 'unknown@example.com']:
        assert client.post('/api/v1/auth/forgot-password', json={'email': email}).status_code == 503


def test_cooldown_resends_and_previous_links(client, db_session, account, mail):
    first = request_link(client, account, mail)
    assert client.post('/api/v1/auth/forgot-password', json={'email': account.email}).status_code == 202
    assert mail.call_count == 1
    row = db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).one()
    row.created_at -= timedelta(seconds=61)
    db_session.commit()
    second = request_link(client, account, mail)
    assert second != first
    assert reset(client, first).status_code == 400
    assert reset(client, second).status_code == 200


def test_reset_preserves_existing_mfa_and_never_logs_in_automatically(client, db_session, account, mail):
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    db_session.commit()
    token = request_link(client, account, mail)
    assert reset(client, token).status_code == 200
    db_session.refresh(account)
    assert account.two_factor_enabled and account.two_factor_secret
    response = client.post('/api/v1/auth/login', json={'email': account.email, 'password': NEW})
    assert response.status_code == 200 and response.json()['requires_2fa'] is True
    assert not response.json().get('access_token')


@pytest.mark.parametrize('password,confirm', [('weak', 'weak'), (NEW, 'different'), ('A'*80+'a1!', 'A'*80+'a1!'), (OLD, OLD), ('Password1234!', 'Password1234!')])
def test_password_policy_and_confirmation_enforced_by_backend(client, db_session, account, mail, password, confirm):
    token = request_link(client, account, mail)
    assert reset(client, token, password, confirm).status_code == 422
    db_session.refresh(account)
    assert verify_password(OLD, account.hashed_password)
    assert db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).one().used_at is None


def test_change_requires_old_password_preserves_current_revokes_other_sessions(client, db_session, account):
    headers, tokens = header(db_session, account)
    other_headers, other_tokens = header(db_session, account)
    payload = {'current_password': 'wrong', 'new_password': NEW, 'confirm_password': NEW}
    denied = client.post('/api/v1/auth/password/change', headers=headers, json=payload)
    assert denied.status_code == 401 and denied.json()['detail'] == 'Ancien mot de passe incorrect.'
    payload['current_password'] = OLD
    result = client.post('/api/v1/auth/password/change', headers=headers, json=payload)
    assert result.status_code == 200, result.text
    assert decode_token(result.json()['access_token'])['sid'] == decode_token(tokens['access_token'])['sid']
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer '+result.json()['access_token']}).status_code == 200
    assert client.get('/api/v1/auth/me', headers=other_headers).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': other_tokens['refresh_token']}).status_code == 401
    assert client.get('/api/v1/auth/me', headers=headers).status_code == 401


def test_mfa_code_required_to_validate_change_and_proof_is_account_scoped(client, db_session, account, actors):
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    db_session.commit()
    headers, _ = header(db_session, account)
    payload = {'current_password': OLD, 'new_password': NEW, 'confirm_password': NEW}
    assert client.post('/api/v1/auth/password/change', headers=headers, json=payload).status_code == 403
    start = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={'password': OLD}).json()
    assert start['requires_2fa'] is True
    wrong = client.post('/api/v1/auth/mfa/reauth/complete', headers=headers, json={'challenge_token': start['challenge_token'], 'method': 'totp', 'code': '000000'})
    assert wrong.status_code == 401
    verified = client.post('/api/v1/auth/mfa/reauth/complete', headers=headers, json={'challenge_token': start['challenge_token'], 'method': 'totp', 'code': pyotp.TOTP(account.two_factor_secret).now()})
    assert verified.status_code == 200
    foreign, _ = mfa.create_challenge(db_session, actors[0][1], 'manage_verified')
    db_session.commit()
    payload['management_token'] = foreign
    assert client.post('/api/v1/auth/password/change', headers=headers, json=payload).status_code == 401
    payload['management_token'] = verified.json()['management_token']
    result = client.post('/api/v1/auth/password/change', headers=headers, json=payload)
    assert result.status_code == 200, result.text
    db_session.refresh(account)
    assert account.two_factor_enabled and verify_password(NEW, account.hashed_password)


def test_sso_account_can_set_password_by_email_but_not_bypass_old_password_check(client, db_session, account, mail):
    account.hashed_password = None
    db_session.commit()
    headers, _ = header(db_session, account)
    assert client.post('/api/v1/auth/password/change', headers=headers, json={'current_password': '', 'new_password': NEW, 'confirm_password': NEW}).status_code == 409
    token = request_link(client, account, mail)
    assert reset(client, token).status_code == 200
    db_session.refresh(account)
    assert verify_password(NEW, account.hashed_password)


def test_reset_link_origin_ignores_host_header(client, account, mail):
    response = client.post('/api/v1/auth/forgot-password', headers={'X-Forwarded-Host': 'attacker.example'}, json={'email': account.email})
    assert response.status_code == 202
    assert mail.call_args.args[1].startswith('https://radarapp.fr/reset-password#token=')


def test_two_concurrent_uses_of_reset_link_only_one_succeeds(engine):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy.orm import Session
    from fastapi import HTTPException, Response
    from app.db.models.user import User, Role
    from app.api.passwords import reset as reset_endpoint, ResetInput
    from uuid import uuid4
    with Session(engine) as db:
        user = User(email=f'reset-concurrent-{uuid4().hex}@example.com', full_name='TEST concurrent', role=Role.VIEWER,
                    is_active=True, is_whitelisted=True, hashed_password=get_password_hash(OLD))
        db.add(user); db.flush()
        token, row = mfa.create_challenge(db, user, 'password_reset')
        row.expires_at = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
    def consume():
        with Session(engine) as db:
            try:
                reset_endpoint(ResetInput(token=token, new_password=NEW, confirm_password=NEW), Response(), db)
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: consume(), range(2))) == [200, 400]


def test_password_change_revokes_pending_reset_and_browser_authorizations(client, db_session, account, mail):
    import hashlib
    from app.db.models.login_session import TrustedDevice
    headers, _ = header(db_session, account)
    db_session.add(TrustedDevice(user_id=account.id, token_hash=hashlib.sha256(b'test-device').hexdigest(),
        ua_hash=hashlib.sha256(b'ua').hexdigest(), auth_version=account.mfa_version, label='TEST browser',
        expires_at=datetime.utcnow() + timedelta(days=30)))
    db_session.commit()
    token = request_link(client, account, mail)
    changed = client.post('/api/v1/auth/password/change', headers=headers,
        json={'current_password': OLD, 'new_password': NEW, 'confirm_password': NEW})
    assert changed.status_code == 200
    assert reset(client, token).status_code == 400
    assert db_session.query(TrustedDevice).one().revoked_at is not None


def test_reset_is_available_during_mfa_attempt_lockout(client, db_session, account, mail):
    for _ in range(5):
        _, row = mfa.create_challenge(db_session, account, 'password_reauth')
        row.attempts = 1
        row.last_attempt_at = datetime.utcnow()
    db_session.commit()
    token = request_link(client, account, mail)
    assert reset(client, token).status_code == 200


def test_password_policy_is_public_and_settings_require_auth(client):
    response = client.get('/api/v1/auth/password-policy')
    assert response.status_code == 200 and response.json()['reset_expiry_minutes'] == 15
    assert response.json()['min_length'] == 12
    assert client.get('/api/v1/auth/password/status').status_code == 401
    assert client.post('/api/v1/auth/password/change', json={'current_password': OLD, 'new_password': NEW, 'confirm_password': NEW}).status_code == 401


def test_recovery_mail_uses_real_configured_resend_interface(monkeypatch):
    import asyncio
    from app.core.config import settings
    from app.services.password_email import send_reset_link
    monkeypatch.setattr(settings, 'resend_api_key', 'explicit-test-key')
    send = AsyncMock(return_value={'id': 'explicit-test-message'})
    monkeypatch.setattr('app.services.password_email.EmailService.send_email', send)
    link = 'https://radarapp.fr/reset-password#token=' + 'x'*43
    asyncio.run(send_reset_link('delivery@example.com', link))
    assert send.call_args.args[0] == 'delivery@example.com'
    assert '15 minutes' in send.call_args.args[3]
    assert link in send.call_args.args[3]
    send.return_value = {}
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        asyncio.run(send_reset_link('delivery@example.com', link))
    assert error.value.status_code == 503


def test_account_delivery_budget_does_not_issue_sixth_link(client, db_session, account, mail, monkeypatch):
    from app.core.security_middleware import RATE_LIMITS
    monkeypatch.setitem(RATE_LIMITS, '/api/v1/auth/forgot-password', {'max': 100, 'window': 300})
    for _ in range(5):
        assert client.post('/api/v1/auth/forgot-password', json={'email': account.email}).status_code == 202
        db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).update({'created_at': datetime.utcnow() - timedelta(seconds=61)})
        db_session.commit()
    assert mail.call_count == 5
    assert client.post('/api/v1/auth/forgot-password', json={'email': account.email}).status_code == 202
    assert mail.call_count == 5


def test_public_request_queues_only_email_without_lookup_delivery_or_token(client, db_session, account, mail, monkeypatch):
    from unittest.mock import Mock
    queue = Mock()
    monkeypatch.setattr('app.workers.password_tasks.request_password_reset.delay', queue)
    known = client.post('/api/v1/auth/forgot-password', json={'email': account.email})
    unknown = client.post('/api/v1/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert [call.args for call in queue.call_args_list] == [(account.email,), ('unknown@example.com',)]
    assert not mail.called
    assert db_session.query(MFAChallenge).filter_by(purpose='password_reset', user_id=account.id).count() == 0


def test_broker_failure_never_claims_a_request_was_queued(client, account, mail, monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setattr('app.workers.password_tasks.request_password_reset.delay', Mock(side_effect=RuntimeError('private broker credential')))
    for email in [account.email, 'unknown@example.com']:
        result = client.post('/api/v1/auth/forgot-password', json={'email': email})
        assert result.status_code == 503 and 'private' not in result.text
    assert not mail.called


def test_legacy_admin_routes_cannot_bypass_own_password_step_up(client, db_session, account, actors):
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    db_session.commit()
    headers, _ = header(db_session, account)
    assert client.patch(f'/api/v1/users/{account.id}', headers=headers, json={'password': NEW}).status_code == 403
    other = actors[0][1]
    assert client.patch(f'/api/v1/users/{other.id}', headers=headers, json={'password': NEW}).status_code == 403
    account.is_superuser = True
    db_session.commit()
    headers, _ = header(db_session, account)
    assert client.patch(f'/api/v1/users/{account.id}', headers=headers, json={'password': NEW}).status_code == 409
    db_session.refresh(account)
    assert verify_password(OLD, account.hashed_password)
