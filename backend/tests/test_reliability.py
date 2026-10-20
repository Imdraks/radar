from unittest.mock import patch
import pytest
from app.db.models.discovery import DiscoveryArtist, DiscoveryEnrichmentJob


def test_foreign_collaborator_cannot_be_assigned(client, db_session, actors, headers, monkeypatch):
    monkeypatch.setattr('app.api.agency_projects.create_project_drive_structure_task', lambda **kwargs: None)
    created = client.post('/api/v1/agency/projects', headers=headers(), json={'name':'Agency project'})
    assert created.status_code == 200
    response = client.post(f"/api/v1/agency/projects/{created.json()['id']}/tasks", headers=headers(), json={'title':'Task','assignee_id':actors[0][1].id})
    assert response.status_code == 422


def test_unavailable_event_source_is_an_error_not_a_demo(client, db_session, actors, headers):
    actors[1][0].plan = 'premium'; db_session.commit()
    with patch('app.db.models.artist_event.ArtistEvent.to_map_dict', side_effect=RuntimeError('provider data unavailable')):
        # No collected event exists: the response is explicitly empty, never generated.
        response = client.get('/api/v1/map/artist-events', headers=headers())
    assert response.status_code == 200, response.text
    assert response.json()['events'] == []
    assert response.json()['source'] == 'no_collected_events'


def test_transient_pipeline_failure_is_queued_for_bounded_retry(db_session, actors, monkeypatch):
    from app.workers.discovery_pipeline import run_enrichment_pipeline
    workspace = actors[1][0]
    artist = DiscoveryArtist(workspace_id=workspace.id, canonical_name='Artist', normalized_name='artist')
    db_session.add(artist); db_session.flush()
    job = DiscoveryEnrichmentJob(workspace_id=workspace.id, input_type='NAME',input_value='Artist', status='QUEUED')
    db_session.add(job); db_session.commit()
    monkeypatch.setattr('app.workers.discovery_pipeline.get_db', lambda: db_session)
    monkeypatch.setattr(db_session,'close',lambda: None)
    monkeypatch.setattr('app.workers.discovery_pipeline.step_match', lambda *args: artist.id)
    def timeout(*args): raise TimeoutError('provider timeout')
    monkeypatch.setattr('app.workers.discovery_pipeline.step_viberate', timeout)
    with pytest.raises(TimeoutError):
        run_enrichment_pipeline.run(str(job.id))
    db_session.refresh(job)
    assert job.status == 'QUEUED'
    assert job.error_code == 'TIMEOUT'
    assert run_enrichment_pipeline.max_retries == 3


def test_missing_observations_do_not_create_a_booking_fee():
    from app.workers.discovery_pipeline import estimate_fees
    assert estimate_fees(0,0,0) == (None,None)


def test_expired_subscription_does_not_authorize_paid_api(client, db_session, actors, headers):
    from datetime import datetime,timedelta
    workspace = actors[1][0]
    workspace.plan = 'business'
    workspace.plan_expires_at = datetime.utcnow()-timedelta(days=1)
    db_session.commit()
    assert client.get('/api/v1/billing/quotes', headers=headers()).status_code == 403
    assert 'invoices' not in client.get('/api/v1/subscription/current', headers=headers()).json()['available_features']


def test_legacy_project_without_direct_workspace_id_remains_accessible(client, db_session, actors, headers):
    from app.db.models.agency import Project,Client
    customer = Client(workspace_id=actors[1][0].id,name='Historical customer')
    db_session.add(customer);db_session.flush()
    project = Project(client_id=customer.id,name='Historical project',workspace_id=None)
    db_session.add(project);db_session.commit()
    response = client.get(f'/api/v1/agency/projects/{project.id}/detail',headers=headers())
    assert response.status_code == 200,response.text
    assert client.get(f'/api/v1/agency/projects/{project.id}/detail',headers=headers(1)).status_code == 404


def test_seat_limit_is_enforced_when_adding_a_member(client, db_session, actors, headers):
    workspace = actors[1][0]
    workspace.max_seats=2  # Owner and existing viewer already fill the contract.
    db_session.commit()
    response = client.post(f'/api/v1/workspaces/{workspace.id}/members',headers=headers(),json={'user_email':actors[0][1].email})
    assert response.status_code == 409,response.text
