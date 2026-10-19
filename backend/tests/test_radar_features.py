"""Real API assertions replace legacy checks which accepted unexpected 401 responses."""
import pytest
from app.db.models.agency import Project, Client, AgencyTask, Deliverable
from app.db.models.discovery import DiscoveryArtist
from app.db.models.subscription_request import SubscriptionRequest
from app.db.models.workspace import Workspace
from app.core.subscription import Plan, Feature, get_plan_features


def test_catalog_has_only_official_offers(client):
    response = client.get('/api/v1/subscription/plans')
    assert response.status_code == 200
    assert [x['name'] for x in response.json()] == ['core', 'premium', 'business']
    assert all(x['price_monthly'] is None for x in response.json())
    assert Feature.INVOICES not in get_plan_features(Plan.PREMIUM)
    assert Feature.INVOICES in get_plan_features(Plan.BUSINESS)
    assert Feature.BANKING not in get_plan_features(Plan.BUSINESS)


@pytest.mark.parametrize('url', ['/api/v1/subscription/current', '/api/v1/agency/projects', '/api/v1/billing/quotes'])
def test_authentication_required(client, url):
    assert client.get(url).status_code == 401


def test_invalid_token_is_not_functional_success(client):
    assert client.get('/api/v1/subscription/current', headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_request_is_not_activation_and_platform_approval_is_audited(client, db_session, actors, headers):
    users, workspaces = actors
    response = client.post('/api/v1/subscription/change-plan', headers=headers(), json={'plan':'business'})
    assert response.status_code == 202
    request_id = response.json()['request_id']
    assert client.get('/api/v1/subscription/current', headers=headers()).json()['plan'] == 'core'
    duplicate = client.post('/api/v1/subscription/change-plan', headers=headers(), json={'plan':'business'})
    assert duplicate.json()['request_id'] == request_id
    decision = {'approve':True, 'authorization_reference':'Administrative commercial agreement REF-TEST'}
    assert client.post(f'/api/v1/subscription/admin/requests/{request_id}/decision', headers=headers(), json=decision).status_code == 403
    approved = client.post(f'/api/v1/subscription/admin/requests/{request_id}/decision', headers=headers(2), json=decision)
    assert approved.status_code == 200, approved.text
    assert approved.json()['subscription']['plan'] == 'business'
    entry = db_session.get(SubscriptionRequest, request_id)
    assert entry.decided_by == users[2].id and entry.authorization_reference == decision['authorization_reference']
    assert client.post(f'/api/v1/subscription/admin/requests/{request_id}/decision', headers=headers(2), json=decision).status_code == 409


@pytest.mark.parametrize('route', ['toggle-addon','toggle-pack'])
def test_legacy_toggles_never_grant_access(client, db_session, actors, headers, route):
    response = client.post(f'/api/v1/subscription/{route}', headers=headers(), json={'enable':True, 'pack':'talents', 'addon':'radar_business'})
    assert response.status_code == 409
    assert client.get('/api/v1/subscription/current', headers=headers()).json()['available_features'] == sorted(f.value for f in get_plan_features(Plan.CORE))


@pytest.mark.parametrize('route', ['/api/v1/subscription/current', '/api/v1/agency/clients','/api/v1/agency/dashboard', '/api/v1/agency/projects','/api/v1/discovery/artists'])
def test_agency_admin_cannot_access_other_workspace(client, actors, headers, route):
    other = actors[1][1].id
    assert client.get(f'{route}?workspace_id={other}', headers=headers()).status_code == 403


def test_viewer_cannot_request_or_mutate(client, actors, headers):
    assert client.post('/api/v1/subscription/change-plan', headers=headers(3), json={'plan':'business'}).status_code == 403
    assert client.post('/api/v1/agency/projects', headers=headers(3), json={'name':'Forbidden'}).status_code == 403


@pytest.mark.parametrize('route', ['/api/v1/billing/quotes','/api/v1/discovery/artists','/api/v1/events'])
def test_core_cannot_use_paid_api(client, actors, headers, route):
    assert client.get(route, headers=headers()).status_code == 403


def test_project_creation_update_and_child_isolation(client, db_session, actors, headers, monkeypatch):
    monkeypatch.setattr('app.api.agency_projects.create_project_drive_structure_task', lambda **kwargs: None)
    response = client.post('/api/v1/agency/projects', headers=headers(), json={'name':'Production project'})
    assert response.status_code == 200, response.text
    project_id = response.json()['id']
    updated = client.patch(f'/api/v1/agency/projects/{project_id}', headers=headers(), json={'name':'Updated'})
    assert updated.status_code == 200, updated.text
    assert updated.json()['name'] == 'Updated'
    assert client.get(f'/api/v1/agency/projects/{project_id}/detail', headers=headers(1)).status_code == 404
    task = client.post(f'/api/v1/agency/projects/{project_id}/tasks', headers=headers(), json={'title':'Production task'})
    assert task.status_code == 200, task.text
    task_id = task.json()['id']
    assert client.patch(f'/api/v1/agency/projects/tasks/{task_id}', headers=headers(1), json={'title':'stolen'}).status_code == 404


def test_orm_scope_prevents_list_leak(client, db_session, actors, headers):
    users, workspaces = actors
    for ws in workspaces:
        db_session.add(Client(workspace_id=ws.id, name=f'Client {ws.id}'))
        ws.plan = 'business'
    db_session.commit()
    own = client.get('/api/v1/agency/clients', headers=headers())
    assert own.status_code == 200, own.text
    assert [row['name'] for row in own.json()] == [f'Client {workspaces[0].id}']


def test_event_and_discovery_transfer_with_financial_gate(client, db_session, actors, headers):
    workspace = actors[1][0]; workspace.plan = 'premium'
    artist = DiscoveryArtist(workspace_id=workspace.id, canonical_name='Test Artist', normalized_name='test artist')
    foreign_artist = DiscoveryArtist(workspace_id=actors[1][1].id, canonical_name='Foreign', normalized_name='foreign')
    db_session.add_all([artist, foreign_artist]); db_session.commit()
    created = client.post('/api/v1/events', headers=headers(), json={'name':'Festival', 'starts_at':'2027-06-01T12:00:00','ends_at':'2027-06-01T23:00:00','forecast_budget':'1000.00'})
    assert created.status_code == 201, created.text
    event_id = created.json()['id']
    assert client.post(f'/api/v1/events/{event_id}/artists/{artist.id}', headers=headers()).status_code == 201
    assert client.post(f'/api/v1/events/{event_id}/artists/{foreign_artist.id}', headers=headers()).status_code == 404
    detail = client.get(f'/api/v1/events/{event_id}', headers=headers())
    assert detail.json()['artists'][0]['name'] == 'Test Artist'
    assert client.post(f'/api/v1/events/{event_id}/expenses', headers=headers(), json={'description':'Stage', 'amount':'120'}).status_code == 403
    workspace.plan = 'business'; db_session.commit()
    expense = client.post(f'/api/v1/events/{event_id}/expenses', headers=headers(), json={'description':'Stage', 'amount':'120'})
    assert expense.status_code == 201, expense.text


def test_provenance_and_missing_data_are_explicit(client, db_session, actors, headers):
    workspace = actors[1][0]; workspace.plan = 'premium'
    artist = DiscoveryArtist(workspace_id=workspace.id, canonical_name='No Data', normalized_name='no data')
    db_session.add(artist); db_session.commit()
    response = client.get(f'/api/v1/discovery/artist/{artist.id}', headers=headers())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['monthly_listeners'] is None and data['confidence_score'] is None
    assert data['missing_data'] and data['evidence'] == []


@pytest.mark.parametrize('route', ['/api/v1/predictions/1','/api/v1/competitive/competitors','/api/v1/banking/connections'])
def test_suspended_modules_never_return_fiction(client, route):
    assert client.get(route).status_code == 503
