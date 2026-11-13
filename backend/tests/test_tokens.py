"""Signed legacy-format JWTs remain valid; invalid and expired tokens are rejected."""
from datetime import timedelta
import base64,hashlib,hmac,json,time
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_token


def test_existing_hs256_token_format_remains_compatible():
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).rstrip(b'=')
    header=encode({'alg':'HS256','typ':'JWT'})
    payload=encode({'sub':'123','type':'access','exp':int(time.time())+300})
    content=header+b'.'+payload
    signature=base64.urlsafe_b64encode(hmac.new(settings.jwt_secret_key.encode(),content,hashlib.sha256).digest()).rstrip(b'=')
    assert verify_token((content+b'.'+signature).decode()) == '123'


def test_expiry_and_token_type_are_enforced():
    assert verify_token(create_access_token({'sub':'1'},timedelta(seconds=-1))) is None
    refresh=create_refresh_token({'sub':'1'})
    assert verify_token(refresh) is None
    assert verify_token(refresh,'refresh') == '1'
    assert verify_token('invalid') is None


def test_login_issues_a_real_token_and_rejects_wrong_password(client, db_session, actors):
    from app.core.security import get_password_hash
    user=actors[0][0]
    user.email="login-test@example.com"
    user.hashed_password=get_password_hash('LocalTestPassword42!')
    db_session.commit()
    wrong=client.post('/api/v1/auth/login',json={'email':user.email,'password':'wrong'})
    assert wrong.status_code == 401
    valid=client.post('/api/v1/auth/login',json={'email':user.email,'password':'LocalTestPassword42!'})
    assert valid.status_code == 200,valid.text
    token=valid.json()['access_token']
    assert verify_token(token) == str(user.id)


def test_normal_api_activity_does_not_consume_login_attempts():
    from app.core.security_middleware import RateLimiter
    from starlette.requests import Request
    limiter=RateLimiter()
    def request(path,headers=()):
        return Request({'type':'http','method':'GET','path':path,'headers':list(headers),'client':('192.0.2.20',1234),'scheme':'http','server':('test',80),'query_string':b''})
    for _ in range(20):
        assert limiter.check_rate_limit(request('/api/v1/agency/projects'))
    assert limiter.check_rate_limit(request('/api/v1/auth/login'),max_requests=2)
    assert limiter.check_rate_limit(request('/api/v1/auth/login'),max_requests=2)
    assert not limiter.check_rate_limit(request('/api/v1/auth/login'),max_requests=2)
    assert limiter._get_client_ip(request('/api/v1/auth/login',[(b'x-forwarded-for',b'127.0.0.1')])) == '192.0.2.20'
