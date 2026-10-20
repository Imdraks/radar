"""Regression tests for the API audit: tenant children, realtime auth and failures."""
import json
from unittest.mock import AsyncMock
import pytest
from starlette.websockets import WebSocketDisconnect
from app.core.security import create_access_token
from app.db.models.opportunity import Opportunity, SourceType
from app.db.models.workspace import WorkspaceMember, WorkspaceRole
from app.api.tags_comments import Comment


def opportunity(db, workspace, suffix):
    row = Opportunity(workspace_id=workspace.id, external_id=suffix, title=suffix,
                      source_type=SourceType.API, source_name="test")
    db.add(row)
    db.commit()
    return row


def test_custom_tags_use_the_correct_relation(client, db_session, actors, headers):
    item = opportunity(db_session, actors[1][0], "tags-test")
    response = client.post('/api/v1/tags', headers=headers(), json={'name':'Selection'})
    assert response.status_code == 200, response.text
    tag_id = response.json()['id']
    url = f'/api/v1/tags/opportunities/{item.id}/tags/{tag_id}'
    assert client.post(url, headers=headers()).status_code == 200
    assert client.post(url, headers=headers()).status_code == 200
    tags = client.get('/api/v1/tags', headers=headers())
    assert tags.status_code == 200, tags.text
    assert tags.json()[0]['opportunities_count'] == 1
    assert client.get(f'/api/v1/tags/opportunities/{item.id}', headers=headers()).json()[0]['id'] == tag_id
    assert client.put(f'/api/v1/tags/{tag_id}', headers=headers(), json={'name':'Renamed'}).status_code == 200
    assert client.delete(url, headers=headers()).status_code == 200
    assert client.get('/api/v1/tags', headers=headers()).json()[0]['opportunities_count'] == 0


def test_annotations_do_not_follow_user_across_workspaces(client, db_session, actors, headers):
    users, workspaces = actors
    db_session.add(WorkspaceMember(workspace_id=workspaces[1].id, user_id=users[0].id, role=WorkspaceRole.ADMIN))
    first = opportunity(db_session, workspaces[0], 'first')
    second = opportunity(db_session, workspaces[1], 'second')
    tag = client.post('/api/v1/tags', headers=headers(), json={'name':'Private'}).json()['id']
    assert client.post(f'/api/v1/favorites/{first.id}', headers=headers()).status_code == 200
    comment = client.post(f'/api/v1/comments/opportunities/{first.id}', headers=headers(), json={'content':'Secret'}).json()['id']
    query = f'?workspace_id={workspaces[1].id}'
    assert client.get('/api/v1/tags'+query, headers=headers()).json() == []
    assert client.get('/api/v1/favorites'+query, headers=headers()).json() == []
    assert client.put(f'/api/v1/comments/{comment}'+query, headers=headers(), json={'content':'Intrusion'}).status_code == 404
    assert client.delete(f'/api/v1/comments/{comment}'+query, headers=headers()).status_code == 404
    assert client.get(f'/api/v1/comments/opportunities/{first.id}/count'+query, headers=headers()).status_code == 404
    assert client.post(f'/api/v1/tags/opportunities/{second.id}/tags/{tag}'+query, headers=headers()).status_code == 404


@pytest.mark.parametrize('subject', ['invalid-id', '-1', '0', '99999999999999999999999999'])
def test_signed_malformed_subject_returns_401(client, subject):
    token = create_access_token({'sub':subject})
    assert client.get('/api/v1/subscription/current', headers={'Authorization':f'Bearer {token}'}).status_code == 401


def test_websocket_rejects_inactive_and_missing_accounts(client, db_session, actors):
    user = actors[0][0]
    user.is_active = False
    db_session.commit()
    for subject in (str(user.id), '2147483647', 'bad'):
        token = create_access_token({'sub':subject})
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f'/ws/notifications?token={token}'):
                pass
        assert error.value.code == 4001


def test_websocket_active_account_connects(client, actors):
    token = create_access_token({'sub':str(actors[0][0].id)})
    with client.websocket_connect(f'/ws/notifications?token={token}') as websocket:
        assert websocket.receive_json()['type'] == 'connected'
        websocket.send_text('ping')
        assert websocket.receive_json()['type'] == 'pong'


@pytest.fixture
def progress_redis(monkeypatch):
    cache = AsyncMock()
    monkeypatch.setattr('app.api.progress.redis_connection', lambda: cache)
    return cache


def test_progress_enforces_owner_and_selected_workspace(client, actors, headers, progress_redis):
    users, workspaces = actors
    cache = progress_redis
    cache.get.side_effect = [json.dumps([users[0].id, workspaces[0].id]), json.dumps({'task_id':'job', 'type':'completed'})]
    response = client.get('/api/v1/progress/task/job', headers=headers())
    assert response.status_code == 200 and response.json()['type'] == 'completed'
    cache.get.side_effect = None
    cache.get.return_value = json.dumps([users[1].id, workspaces[1].id])
    assert client.get('/api/v1/progress/task/job', headers=headers()).status_code == 404
    cache.get.return_value = None
    assert client.get('/api/v1/progress/task/job', headers=headers()).status_code == 404
    assert client.get('/api/v1/progress/stream?task_ids=', headers=headers()).status_code == 422
    assert client.get('/api/v1/progress/stream', headers=headers()).status_code == 422
    cache.aclose.assert_awaited()


def test_progress_query_auth_and_unavailable_service(client, actors, progress_redis):
    assert client.get('/api/v1/progress/task/job').status_code == 401
    token = create_access_token({'sub':str(actors[0][0].id)})
    progress_redis.get.side_effect = ConnectionError('internal.redis:6379 secret')
    response = client.get(f'/api/v1/progress/task/job?token={token}')
    assert response.status_code == 503
    assert 'internal.redis' not in response.text and 'secret' not in response.text
    assert client.get(f'/api/v1/progress/task/job?token={token}&workspace_id={actors[1][1].id}').status_code == 403


def test_contact_results_are_integer_identified_and_tenant_scoped(client, db_session, actors, headers):
    from app.db.models.radar_features import ContactFinderResult
    workspaces = actors[1]
    for index in range(2):
        workspaces[index].plan = 'business'
    item = opportunity(db_session, workspaces[0], 'contact-result')
    db_session.add(ContactFinderResult(opportunity_id=item.id, status='found', contact_email='contact@agency.invalid'))
    db_session.commit()
    route = f'/api/v1/contact-finder/opportunities/{item.id}/result'
    result = client.get(route, headers=headers())
    assert result.status_code == 200, result.text
    assert result.json()['contact_email'] == 'contact@agency.invalid'
    other = client.get(route, headers=headers(1))
    assert other.status_code == 200 and other.json() is None


def test_contact_crawler_does_not_follow_redirects(monkeypatch):
    import httpx
    from app.api.contact_finder import search_official_website
    calls = []
    def handle(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={'Location':'http://169.254.169.254/metadata'})
    real_client = httpx.Client
    monkeypatch.setattr('httpx.Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    monkeypatch.setattr('app.api.contact_finder.is_safe_url', lambda url: True)
    result = search_official_website('https://agency.invalid/', [], max_pages=1)
    assert calls == ['https://agency.invalid/']
    assert result['found'] is False


@pytest.mark.parametrize('url', ['http://localhost/', 'http://169.254.169.254/', 'file:///etc/passwd', 'https://user:password@example.com/', 'http://example.com:6379/'])
def test_contact_crawler_blocks_unsafe_urls(url):
    from app.api.contact_finder import is_safe_url
    assert is_safe_url(url) is False


@pytest.mark.asyncio
async def test_progress_filters_foreign_events_and_waits_for_all_selected_tasks():
    from app.api.progress import event_generator
    cache, pubsub = AsyncMock(), AsyncMock()
    messages = [ {'task_id':'foreign', 'type':'progress', 'data':{'message':'secret'}},
                 {'task_id':'one', 'type':'completed'}, {'task_id':'two', 'type':'completed'} ]
    pubsub.get_message.side_effect = [{'data':json.dumps(message)} for message in messages]
    events = [event async for event in event_generator(cache, pubsub, ['one','two'])]
    assert [json.loads(event['data']).get('task_id') for event in events] == [None, 'one', 'two']
    pubsub.aclose.assert_awaited_once()
    cache.aclose.assert_awaited_once()


def test_source_health_static_route_and_integer_source_ids(client, db_session, actors, headers, monkeypatch):
    from app.db.models.source import SourceConfig
    monkeypatch.setattr('app.api.source_health.cache_get', lambda *args: None)
    monkeypatch.setattr('app.api.source_health.cache_set', lambda *args, **kwargs: None)
    source = SourceConfig(name='Audit test source', source_type=SourceType.RSS, url='https://agency.invalid/feed')
    db_session.add(source)
    db_session.commit()
    response = client.get('/api/v1/sources/health', headers=headers(2))
    assert response.status_code == 200, response.text
    response = client.get(f'/api/v1/sources/{source.id}', headers=headers(2))
    assert response.status_code == 200, response.text
    assert response.json()['id'] == source.id
    assert client.get('/api/v1/sources/health', headers=headers()).status_code == 403


def test_openapi_operation_ids_are_unique():
    from app.main import app
    schema = app.openapi()
    ids = [op['operationId'] for path in schema['paths'].values() for method,op in path.items()
           if method in {'get','post','put','patch','delete'}]
    assert len(ids) == len(set(ids))


def test_collection_runs_are_tenant_scoped_and_unassigned_runs_hidden(client, db_session, actors, headers):
    from app.db.models.entity import CollectionRun, ObjectiveType
    for workspace in actors[1]:
        workspace.plan = 'business'
    runs = [CollectionRun(workspace_id=workspace_id, objective=ObjectiveType.BOOKING, status='SUCCESS')
            for workspace_id in [actors[1][0].id, actors[1][1].id, None]]
    db_session.add_all(runs)
    db_session.commit()
    for index, run in enumerate(runs):
        response = client.get(f'/api/v1/collection/runs/{run.id}', headers=headers())
        assert response.status_code == (200 if index == 0 else 404), response.text


def test_pending_2fa_token_never_authenticates_api_or_realtime(client, actors):
    token = create_access_token({'sub':str(actors[0][0].id), '2fa_pending':True})
    assert client.get('/api/v1/auth/me', headers={'Authorization':f'Bearer {token}'}).status_code == 401
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/ws/notifications?token={token}'):
            pass
    assert client.post(f'/api/v1/auth/2fa/verify?user_id={actors[0][0].id}', json={'code':'123456'}).status_code == 401


def test_detailed_health_requires_platform_authorization(client, headers):
    assert client.get('/health').status_code == 200
    assert client.get('/health/detailed').status_code == 401
    assert client.get('/health/detailed', headers=headers()).status_code == 403


def test_market_intelligence_returns_empty_observations(client, db_session, actors, headers):
    actors[1][0].plan='business'
    db_session.commit()
    response=client.get('/api/v1/market-intelligence/feed',headers=headers())
    assert response.status_code == 200,response.text
    assert response.json()['feed'] == []


def test_real_two_factor_login_requires_second_factor(client, db_session, actors):
    import pyotp
    from app.core.security import get_password_hash
    user = actors[0][0]
    user.email = 'twofactor-test@example.com'
    user.hashed_password = get_password_hash('Disposable-test-password-42')
    user.two_factor_enabled = True
    user.two_factor_secret = pyotp.random_base32()
    db_session.commit()
    credentials={'email':user.email, 'password':'Disposable-test-password-42'}
    pending=client.post('/api/v1/auth/login',json=credentials)
    assert pending.status_code == 200,pending.text
    assert pending.json()['requires_2fa'] is True
    token=pending.json()['temp_token']
    assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {token}'}).status_code == 401
    completed=client.post('/api/v1/auth/login',json={**credentials,'totp_code':pyotp.TOTP(user.two_factor_secret).now()})
    assert completed.status_code == 200,completed.text
    assert completed.json()['requires_2fa'] is False
    token=completed.json()['access_token']
    assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {token}'}).status_code == 200
