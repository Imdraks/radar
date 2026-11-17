"""Real PostgreSQL proofs; delivery is an explicit in-memory test provider."""
from datetime import datetime, timedelta
import time
from unittest.mock import AsyncMock
import pyotp
import pytest
from fastapi import HTTPException
from app.core import mfa
from app.core.security import get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.encryption import decrypt_sensitive, encrypt_sensitive
from app.db.models.mfa import MFAChallenge

PASSWORD = 'Disposable-Mfa-42!'


@pytest.fixture(autouse=True)
def rate_limits():
    from app.core.security_middleware import rate_limiter
    rate_limiter.requests.clear()
    rate_limiter.blocked_ips.clear()


@pytest.fixture
def account(db_session, actors):
    user = actors[0][0]
    user.email = 'mfa-test@example.com'
    user.hashed_password = get_password_hash(PASSWORD)
    db_session.commit()
    return user


@pytest.fixture
def delivery(monkeypatch):
    sent = []
    async def deliver(method, destination, code):
        sent.append((method, destination, code))
    monkeypatch.setattr('app.services.mfa_delivery.deliver', deliver)
    monkeypatch.setattr('app.services.mfa_delivery.availability', lambda: {'email': True, 'sms': True, 'totp': True})
    monkeypatch.setattr('app.api.mfa.availability', lambda: {'email': True, 'sms': True, 'totp': True})
    return sent


def fresh_header(user):
    return {'Authorization': 'Bearer ' + mfa.issue_tokens(user)['access_token']}


def first_login(client, account):
    response = client.post('/api/v1/auth/login', json={'email': account.email, 'password': PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def reauth(client, headers):
    response = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={'password': PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def enroll(client, account, method, delivery=None):
    headers = fresh_header(account)
    proof = reauth(client, headers)
    assert proof['requires_2fa'] is False
    started = client.post('/api/v1/auth/mfa/enroll/start', headers=headers,
        json={'management_token': proof['management_token'], 'method': method, 'phone': '+33612345678'})
    assert started.status_code == 200, started.text
    stage = started.json()
    code = pyotp.TOTP(stage['secret']).now() if method == 'totp' else delivery[-1][2]
    result = client.post('/api/v1/auth/mfa/enroll/complete', headers=headers,
        json={'challenge_token': stage['challenge_token'], 'method': method, 'code': code})
    assert result.status_code == 200, result.text
    return stage, result.json(), headers


def test_login_without_mfa_and_refresh_keep_auth_time(client, account):
    result = first_login(client, account)
    assert result['requires_2fa'] is False
    before = decode_token(result['access_token'])['auth_time']
    refreshed = client.post('/api/v1/auth/refresh', json={'refresh_token': result['refresh_token']})
    assert refreshed.status_code == 200, refreshed.text
    assert decode_token(refreshed.json()['access_token'])['auth_time'] == before
    assert refreshed.headers.get('cache-control') == 'no-store'


def test_totp_enrollment_does_not_replace_active_secret_and_revokes_old_tokens(client, db_session, account):
    stage, result, old_headers = enroll(client, account, 'totp')
    db_session.refresh(account)
    assert account.two_factor_enabled
    assert account.two_factor_secret.startswith('enc:')
    assert mfa.totp_secret(account) == stage['secret']
    assert all(code.startswith('v1:') for code in account.backup_codes)
    assert all(code not in account.backup_codes for code in result['backup_codes'])
    assert client.get('/api/v1/auth/me', headers=old_headers).status_code == 401
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + result['access_token']}).status_code == 200
    assert client.post('/api/v1/auth/2fa/setup', headers=fresh_header(account)).status_code == 410


def test_app_enrollment_requires_code_and_password(client, db_session, account):
    headers = fresh_header(account)
    denied = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={'password': 'wrong'})
    assert denied.status_code == 401
    assert denied.json()['detail'] == 'Mot de passe Radar incorrect.'
    failed = db_session.query(MFAChallenge).filter_by(user_id=account.id, purpose='password_reauth').one()
    assert failed.attempts == 1 and failed.last_attempt_at is not None
    proof = reauth(client, headers)
    result = client.post('/api/v1/auth/mfa/enroll/start', headers=headers,
        json={'management_token': proof['management_token'], 'method': 'totp'})
    assert result.status_code == 200
    db_session.refresh(account)
    assert not account.two_factor_enabled and not account.two_factor_secret
    repeated = client.post('/api/v1/auth/mfa/enroll/start', headers=headers,
        json={'management_token': proof['management_token'], 'method': 'totp'})
    assert repeated.status_code == 401


@pytest.mark.parametrize('method', ['email', 'sms'])
def test_delivery_enrollment_verified_destination_and_real_two_stage_login(client, db_session, account, delivery, method):
    _, enabled, _ = enroll(client, account, method, delivery)
    db_session.refresh(account)
    destination = account.email if method == 'email' else '+33612345678'
    assert mfa.destination(account, method) == destination
    assert destination not in str(account.mfa_email if method == 'email' else account.mfa_phone)
    pending = first_login(client, account)
    assert pending['requires_2fa'] and pending['access_token'] is None
    token = pending['temp_token']
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    # Move test timestamps past the real account send cooldown.
    db_session.query(MFAChallenge).filter_by(user_id=account.id).update({'last_sent_at': datetime.utcnow() - timedelta(seconds=61)})
    db_session.commit()
    sent = client.post('/api/v1/auth/mfa/send', json={'challenge_token': token, 'method': method})
    assert sent.status_code == 200, sent.text
    assert sent.json()['sent'] is True and 'code' not in sent.json()
    code = delivery[-1][2]
    row = db_session.query(MFAChallenge).filter_by(purpose='login', user_id=account.id).first()
    db_session.refresh(row)
    assert row.token_hash != token and row.code_hash != code
    complete = client.post('/api/v1/auth/mfa/complete', json={'challenge_token': token, 'method': method, 'code': code})
    assert complete.status_code == 200, complete.text
    assert complete.json()['access_token']
    replay = client.post('/api/v1/auth/mfa/complete', json={'challenge_token': token, 'method': method, 'code': code})
    assert replay.status_code == 401


def test_sms_unavailable_cannot_activate_or_claim_sent(client, db_session, account, monkeypatch):
    headers = fresh_header(account)
    proof = reauth(client, headers)
    monkeypatch.setattr('app.api.mfa.availability', lambda: {'sms': False, 'totp': True, 'email': False})
    response = client.post('/api/v1/auth/mfa/enroll/start', headers=headers,
        json={'management_token': proof['management_token'], 'method': 'sms', 'phone': '+33612345678'})
    assert response.status_code == 503
    db_session.refresh(account)
    assert not account.mfa_sms_enabled and not account.mfa_phone


def test_expired_or_foreign_enrollment_proof_cannot_enable(client, db_session, account, actors):
    proof = reauth(client, fresh_header(account))['management_token']
    foreign = {'Authorization': 'Bearer ' + mfa.issue_tokens(actors[0][1])['access_token']}
    assert client.post('/api/v1/auth/mfa/enroll/start', headers=foreign,
        json={'management_token': proof, 'method': 'totp'}).status_code == 401
    row = db_session.query(MFAChallenge).filter_by(user_id=account.id).first()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.post('/api/v1/auth/mfa/enroll/start', headers=fresh_header(account),
        json={'management_token': proof, 'method': 'totp'}).status_code == 401


def test_recovery_is_one_use_and_legacy_plaintext_converted(client, db_session, account):
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    account.backup_codes = ['ABCD-1234', 'FFFF-EEEE']
    db_session.commit()
    pending = first_login(client, account)
    complete = client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending['temp_token'], 'method': 'recovery', 'code': 'abcd1234'})
    assert complete.status_code == 200, complete.text
    db_session.refresh(account)
    assert account.backup_codes == [mfa.recovery_hash(account.id, 'FFFF-EEEE')]
    next_pending = first_login(client, account)
    assert client.post('/api/v1/auth/mfa/complete', json={'challenge_token': next_pending['temp_token'], 'method': 'recovery', 'code': 'ABCD-1234'}).status_code == 401


def test_failed_attempt_budget_cannot_be_reset_by_new_challenges(client, account):
    account.two_factor_enabled = True
    account.two_factor_secret = 'INVALID-FOR-TEST'
    # Fixture session state is flushed before requests.
    from sqlalchemy.orm import object_session
    object_session(account).commit()
    for attempt in range(5):
        pending = first_login(client, account)
        result = client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending['temp_token'], 'method': 'totp', 'code': '000000'})
        assert result.status_code == 401, (attempt, result.text)
    result = client.post('/api/v1/auth/login', json={'email': account.email, 'password': PASSWORD})
    assert result.status_code == 429


def test_totp_code_cannot_be_reused_across_login_challenges(client, db_session, account):
    secret = pyotp.random_base32()
    account.two_factor_enabled = True
    account.two_factor_secret = secret
    db_session.commit()
    code = pyotp.TOTP(secret).now()
    for expected in [200, 401]:
        pending = first_login(client, account)
        response = client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending['temp_token'], 'method': 'totp', 'code': code})
        assert response.status_code == expected, response.text


def test_delivery_failure_is_sanitized_and_method_stays_disabled(client, db_session, account, monkeypatch):
    monkeypatch.setattr('app.services.mfa_delivery.availability', lambda: {'email': True})
    monkeypatch.setattr('app.api.mfa.availability', lambda: {'email': True})
    monkeypatch.setattr('app.services.mfa_delivery.EmailService.send_email', AsyncMock(side_effect=RuntimeError('provider-secret-body')))
    from app.core.config import settings
    monkeypatch.setattr(settings, 'resend_api_key', 'explicit-test-only')
    proof = reauth(client, fresh_header(account))['management_token']
    response = client.post('/api/v1/auth/mfa/enroll/start', headers=fresh_header(account), json={'management_token': proof, 'method': 'email'})
    assert response.status_code == 503
    assert 'provider-secret-body' not in response.text
    db_session.refresh(account)
    assert not account.mfa_email_enabled


def test_sso_session_cannot_bypass_enabled_mfa(client, db_session, account):
    from app.core.sso import SSOService
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    db_session.commit()
    result = SSOService(db_session).create_session_tokens(account)
    assert result['requires_2fa'] is True
    assert 'access_token' not in result and 'refresh_token' not in result


def test_old_authentication_does_not_turn_into_recent_sso_proof(client, db_session, account):
    account.hashed_password = None
    db_session.commit()
    refresh = mfa.issue_tokens(account, auth_time=0)['refresh_token']
    db_session.commit()
    response = client.post('/api/v1/auth/refresh', json={'refresh_token': refresh})
    assert response.status_code == 200
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    proof = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={})
    assert proof.status_code == 401


def test_disabled_account_challenge_and_refresh_are_rejected(client, db_session, account):
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    db_session.commit()
    pending = first_login(client, account)
    refresh = create_refresh_token({'sub': str(account.id)})
    account.is_active = False
    db_session.commit()
    assert client.post('/api/v1/auth/mfa/options', json={'challenge_token': pending['temp_token']}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': refresh}).status_code == 401


def test_purge_preserves_recent_and_active_challenges(db_session, account):
    from app.workers.mfa_tasks import purge_challenges
    _, old = mfa.create_challenge(db_session, account, 'login')
    old.expires_at = datetime.utcnow() - timedelta(hours=25)
    _, recent = mfa.create_challenge(db_session, account, 'login')
    db_session.commit()
    assert purge_challenges(db_session) == 1
    assert db_session.query(MFAChallenge).filter_by(id=recent.id).count() == 1


def test_resend_cooldown_and_old_code_invalidated(client, db_session, account, delivery):
    _, result, _ = enroll(client, account, 'email', delivery)
    pending = first_login(client, account)['temp_token']
    assert client.post('/api/v1/auth/mfa/send', json={'challenge_token': pending, 'method': 'email'}).status_code == 429
    db_session.query(MFAChallenge).update({'last_sent_at': datetime.utcnow() - timedelta(seconds=61)})
    db_session.commit()
    assert client.post('/api/v1/auth/mfa/send', json={'challenge_token': pending, 'method': 'email'}).status_code == 200
    old_code = delivery[-1][2]
    row = db_session.query(MFAChallenge).filter_by(purpose='login').first()
    original_expiry = row.expires_at
    db_session.query(MFAChallenge).update({'last_sent_at': datetime.utcnow() - timedelta(seconds=61)})
    db_session.commit()
    assert client.post('/api/v1/auth/mfa/send', json={'challenge_token': pending, 'method': 'email'}).status_code == 200
    new_code = delivery[-1][2]
    db_session.refresh(row)
    assert row.expires_at == original_expiry
    if old_code != new_code:
        assert client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending, 'method': 'email', 'code': old_code}).status_code == 401
    assert client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending, 'method': 'email', 'code': new_code}).status_code == 200


def test_disabling_last_factor_needs_stepup_and_invalidates_refresh(client, db_session, account, delivery):
    _, result, _ = enroll(client, account, 'email', delivery)
    db_session.refresh(account)
    headers = fresh_header(account)
    assert client.post('/api/v1/auth/mfa/disable', headers=headers, json={'management_token': 'x'*43, 'method': 'email'}).status_code == 401
    stage = reauth(client, headers)
    db_session.query(MFAChallenge).update({'last_sent_at': datetime.utcnow() - timedelta(seconds=61)})
    db_session.commit()
    assert client.post('/api/v1/auth/mfa/send', json={'challenge_token': stage['challenge_token'], 'method': 'email'}).status_code == 200
    proof = client.post('/api/v1/auth/mfa/reauth/complete', headers=headers,
        json={'challenge_token': stage['challenge_token'], 'method': 'email', 'code': delivery[-1][2]})
    assert proof.status_code == 200, proof.text
    disabled = client.post('/api/v1/auth/mfa/disable', headers=headers,
        json={'management_token': proof.json()['management_token'], 'method': 'email'})
    assert disabled.status_code == 200 and disabled.json()['enabled'] is False
    db_session.refresh(account)
    assert not account.mfa_email and not account.backup_codes
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': result['refresh_token']}).status_code == 401


def test_verified_email_stays_bound_when_account_address_changes(client, db_session, account, delivery):
    original_email = account.email
    enroll(client, account, 'email', delivery)
    db_session.refresh(account)
    account.email = 'another-test@example.com'
    db_session.commit()
    pending = first_login(client, account)['temp_token']
    db_session.query(MFAChallenge).update({'last_sent_at': datetime.utcnow() - timedelta(seconds=61)})
    db_session.commit()
    assert client.post('/api/v1/auth/mfa/send', json={'challenge_token': pending, 'method': 'email'}).status_code == 200
    assert delivery[-1][1] == original_email


def test_existing_enabled_method_cannot_be_overwritten(client, db_session, account):
    _, enabled, _ = enroll(client, account, 'totp')
    db_session.refresh(account)
    original = account.two_factor_secret
    headers = fresh_header(account)
    # Generate a separate, independently verified management proof as fixture.
    token, _ = mfa.create_challenge(db_session, account, 'manage_verified')
    db_session.commit()
    result = client.post('/api/v1/auth/mfa/enroll/start', headers=headers,
        json={'management_token': token, 'method': 'totp'})
    assert result.status_code == 409
    db_session.refresh(account)
    assert account.two_factor_secret == original


def test_two_concurrent_recovery_uses_only_one_succeeds(engine):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy.orm import Session
    from app.db.models.user import User, Role
    from uuid import uuid4
    with Session(engine) as db:
        user = User(email=f'concurrency-{uuid4().hex}@example.com', role=Role.PM, is_active=True,
                    is_whitelisted=True, two_factor_enabled=True, two_factor_secret=pyotp.random_base32(), backup_codes=['ABCD-1234'])
        db.add(user); db.flush()
        user_id = user.id
        tokens = [mfa.create_challenge(db, user, 'login')[0] for _ in range(2)]
        db.commit()
    def consume(token):
        with Session(engine) as db:
            try:
                user, row = mfa.load_challenge(db, token, {'login'})
                mfa.verify(db, user, row, 'recovery', 'ABCD-1234')
                db.commit()
                return 200
            except HTTPException as error:
                return error.status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(consume, tokens)) == [200, 401]
    finally:
        with Session(engine) as db:
            db.delete(db.get(User, user_id)); db.commit()


def test_account_delivery_budget_is_shared_across_new_challenges(client, db_session, account, delivery):
    enroll(client, account, 'email', delivery)
    for expected in [200, 200, 200, 200, 429]:
        token = first_login(client, account)['temp_token']
        db_session.query(MFAChallenge).update({'last_sent_at': datetime.utcnow() - timedelta(seconds=61)})
        db_session.commit()
        response = client.post('/api/v1/auth/mfa/send', json={'challenge_token': token, 'method': 'email'})
        assert response.status_code == expected, response.text
    assert len(delivery) == 5


def test_lockout_window_uses_failure_time_not_challenge_creation(client, db_session, account):
    _, row = mfa.create_challenge(db_session, account, 'login')
    row.created_at = datetime.utcnow() - timedelta(minutes=11)
    row.expires_at = datetime.utcnow() - timedelta(minutes=6)
    row.last_attempt_at = datetime.utcnow() - timedelta(minutes=6)
    row.attempts = 5
    db_session.commit()
    response = client.post('/api/v1/auth/login', json={'email': account.email, 'password': PASSWORD})
    assert response.status_code == 429


def test_delivery_budget_uses_send_time_not_challenge_creation(client, db_session, account, delivery):
    enroll(client, account, 'email', delivery)
    row = db_session.query(MFAChallenge).filter_by(user_id=account.id).first()
    row.created_at = datetime.utcnow() - timedelta(hours=2)
    row.last_sent_at = datetime.utcnow() - timedelta(minutes=1, seconds=1)
    row.send_count = 5
    db_session.commit()
    token = first_login(client, account)['temp_token']
    assert client.post('/api/v1/auth/mfa/send', json={'challenge_token': token, 'method': 'email'}).status_code == 429


def test_login_does_not_adopt_unverified_concurrent_mfa_revision(client, account, monkeypatch):
    def change_security(db, user):
        user.mfa_version = (user.mfa_version or 0) + 1
        user.mfa_email_enabled = True
        db.commit()
    monkeypatch.setattr('app.api.workspace.auto_assign_user_to_workspaces', change_security)
    response = client.post('/api/v1/auth/login', json={'email': account.email, 'password': PASSWORD})
    assert response.status_code == 401
    assert 'access_token' not in response.json()


def test_enrollment_session_does_not_adopt_later_revision(client, db_session, account, monkeypatch):
    from app.core.activity_logger import ActivityLogger
    original = ActivityLogger.log
    def audit_then_external_change(db, user, action, **kwargs):
        result = original(db=db, user=user, action=action, **kwargs)
        if action == 'mfa.method_enabled':
            user.mfa_version += 1
            db.commit()
            db.expire(user)
        return result
    monkeypatch.setattr(ActivityLogger, 'log', audit_then_external_change)
    _, result, _ = enroll(client, account, 'totp')
    db_session.refresh(account)
    assert decode_token(result['access_token'])['mfa_ver'] == account.mfa_version - 1
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + result['access_token']}).status_code == 401


def test_sso_first_factor_does_not_record_completed_login(client, db_session, account):
    from app.db.models.account import Account
    from app.core.sso import SSOService
    old = datetime(2020, 1, 1)
    account.last_login_at = old
    account.two_factor_enabled = True
    account.two_factor_secret = pyotp.random_base32()
    secret = account.two_factor_secret
    db_session.add(Account(user_id=account.id, provider='google', provider_account_id='explicit-test-subject'))
    db_session.commit()
    service = SSOService(db_session)
    user, _ = service.find_or_create_user_from_sso('google', 'explicit-test-subject', account.email, True, 'TEST', None, {})
    pending = service.create_session_tokens(user)
    db_session.refresh(account)
    assert account.last_login_at == old
    assert pending['requires_2fa']
    completed = client.post('/api/v1/auth/mfa/complete', json={'challenge_token': pending['temp_token'], 'method': 'totp', 'code': pyotp.TOTP(secret).now()})
    assert completed.status_code == 200, completed.text
    db_session.refresh(account)
    assert account.last_login_at > old


@pytest.mark.asyncio
@pytest.mark.parametrize('provider_status', [201, 403])
async def test_twilio_delivery_transport_contract_and_sanitized_error(monkeypatch, provider_status):
    import httpx
    from urllib.parse import parse_qs
    from app.services import mfa_delivery
    from app.core.config import settings
    monkeypatch.setattr(settings, 'mfa_sms_provider', 'twilio')
    monkeypatch.setattr(settings, 'twilio_account_sid', 'AC' + 'a'*32)
    monkeypatch.setattr(settings, 'twilio_auth_token', 'explicit-test-token')
    monkeypatch.setattr(settings, 'twilio_from_number', '+33123456789')
    original_client = httpx.AsyncClient
    def respond(request):
        assert request.url.host == 'api.twilio.com'
        body = parse_qs(request.content.decode())
        assert body['To'] == ['+33612345678']
        assert '123456' in body['Body'][0]
        assert request.headers['authorization'].startswith('Basic ')
        return httpx.Response(provider_status, json={'sid': 'SM-explicit-fixture'} if provider_status == 201 else {'error': 'private-provider-message'})
    monkeypatch.setattr(mfa_delivery.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    if provider_status == 201:
        await mfa_delivery.deliver('sms', '+33612345678', '123456')
    else:
        with pytest.raises(HTTPException) as error:
            await mfa_delivery.deliver('sms', '+33612345678', '123456')
        assert error.value.status_code == 503
        assert 'private-provider-message' not in error.value.detail


def test_unencrypted_smtp_and_missing_sms_are_not_available(monkeypatch):
    from app.core.config import settings
    from app.services.mfa_delivery import availability
    monkeypatch.setattr(settings, 'resend_api_key', '')
    monkeypatch.setattr(settings, 'smtp_user', 'explicit-test-user')
    monkeypatch.setattr(settings, 'smtp_password', 'explicit-test-password')
    monkeypatch.setattr(settings, 'smtp_port', 587)
    monkeypatch.setattr(settings, 'smtp_use_tls', False)
    monkeypatch.setattr(settings, 'mfa_sms_provider', '')
    assert availability() == {'email': False, 'sms': False, 'totp': True}


def test_password_reauth_missing_password_has_specific_error_and_counts_attempt(client, db_session, account):
    headers = fresh_header(account)
    response = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={})
    assert response.status_code == 401
    assert response.json()['detail'] == 'Saisissez le mot de passe Radar de ce compte.'
    failed = db_session.query(MFAChallenge).filter_by(user_id=account.id, purpose='password_reauth').one()
    assert failed.attempts == 1
    assert db_session.query(MFAChallenge).filter_by(user_id=account.id, purpose='manage_verified').count() == 0


def test_password_reauth_keeps_account_lockout_after_wrong_passwords(client, db_session, account):
    headers = fresh_header(account)
    for _ in range(5):
        response = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={'password': 'wrong'})
        assert response.status_code == 401
        assert response.json()['detail'] == 'Mot de passe Radar incorrect.'
    response = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={'password': PASSWORD})
    assert response.status_code == 429
    assert db_session.query(MFAChallenge).filter_by(user_id=account.id, purpose='manage_verified').count() == 0


def test_password_reauth_uses_connected_account_not_another_workspace_user(client, db_session, account, actors):
    other = actors[0][1]
    other.hashed_password = get_password_hash('Other-Account-Password-42!')
    db_session.commit()
    headers = fresh_header(account)
    rejected = client.post('/api/v1/auth/mfa/reauth/start', headers=headers,
        json={'password': 'Other-Account-Password-42!'})
    assert rejected.status_code == 401
    assert rejected.json()['detail'] == 'Mot de passe Radar incorrect.'
    accepted = client.post('/api/v1/auth/mfa/reauth/start', headers=headers, json={'password': PASSWORD})
    assert accepted.status_code == 200 and accepted.json()['requires_2fa'] is False
