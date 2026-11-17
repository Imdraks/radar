"""Only an empty agency may be hard-deleted; business records are preserved."""
from datetime import datetime, timedelta
import pytest
from app.db.models.workspace import Workspace
from app.db.models.subscription_request import SubscriptionRequest
from app.db.models.billing import BillingCounter
from app.db.models.agency import Client, Project, ProjectStatus
from app.db.models.production_event import ProductionEvent


def test_empty_workspace_can_be_deleted_without_cross_tenant_changes(client, db_session, actors, headers):
    user = actors[0][0]
    empty = Workspace(name='TEST empty workspace', owner_user_id=user.id, plan='core', max_seats=3)
    db_session.add(empty); db_session.commit()
    wid = empty.id
    assert client.delete(f'/api/v1/workspaces/{wid}', headers=headers()).status_code == 204
    assert db_session.query(Workspace).filter_by(id=wid).first() is None
    assert db_session.query(Workspace).filter_by(id=actors[1][1].id).first() is not None


@pytest.mark.parametrize('data', ['subscription', 'billing_counter', 'event'])
def test_workspace_with_business_data_requires_controlled_retention(client, db_session, actors, headers, data):
    user, workspace = actors[0][0], actors[1][0]
    if data == 'subscription':
        row = SubscriptionRequest(workspace_id=workspace.id, requested_by=user.id, kind='plan', requested_value='business', status='pending')
    elif data == 'billing_counter':
        row = BillingCounter(workspace_id=workspace.id, year=2026, kind='invoice', last_number=1)
    else:
        customer = Client(name='TEST retained client', workspace_id=workspace.id)
        db_session.add(customer); db_session.flush()
        project = Project(name='TEST retained event', client_id=customer.id, workspace_id=workspace.id, status=ProjectStatus.ACTIVE)
        db_session.add(project); db_session.flush()
        row = ProductionEvent(workspace_id=workspace.id, project_id=project.id, name='TEST retained event', starts_at=datetime.utcnow(), ends_at=datetime.utcnow() + timedelta(hours=2))
    db_session.add(row); db_session.commit()
    assert client.delete(f'/api/v1/workspaces/{workspace.id}', headers=headers()).status_code == 409
    assert db_session.query(Workspace).filter_by(id=workspace.id).first() is not None
    assert db_session.query(type(row)).first() is not None


def test_another_agency_cannot_delete_workspace(client, actors, headers):
    assert client.delete(f'/api/v1/workspaces/{actors[1][0].id}', headers=headers(1)).status_code == 403
