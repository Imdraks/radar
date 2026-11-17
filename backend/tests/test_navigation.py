"""The product navigation and contextual links follow actual workspace entitlements."""
from datetime import datetime, timedelta
import pytest


@pytest.mark.parametrize('plan', ['core', 'premium', 'business'])
def test_navigation_has_one_entry_per_workflow(client, actors, db_session, headers, plan):
    workspace = actors[1][0]
    workspace.plan = plan
    db_session.commit()
    response = client.get('/api/v1/subscription/navigation', headers=headers())
    assert response.status_code == 200
    items = [item for section in response.json()['sections'].values() for item in section]
    roots = {item['path']: item for item in items}
    assert len(roots) == len(items)
    assert not {'/comparison', '/pipeline', '/factures', '/map', '/analytics', '/intelligence', '/shortlist', '/scoring'} & roots.keys()
    assert {'/today', '/projects', '/production', '/assets', '/agency-calendar'} <= roots.keys()
    if plan == 'core':
        assert not {'/discovery', '/events', '/clients', '/devis'} & roots.keys()
    else:
        assert [link['path'] for link in roots['/discovery']['context_links']] == ['/discovery', '/comparison']
        assert [link['path'] for link in roots['/events']['context_links']] == ['/events', '/map']
    if plan == 'business':
        assert [link['path'] for link in roots['/clients']['context_links']] == ['/clients', '/pipeline']
        assert [link['path'] for link in roots['/devis']['context_links']] == ['/devis', '/factures']
    else:
        assert not {'/clients', '/devis'} & roots.keys()


def test_expired_plan_hides_paid_contextual_links(client, actors, db_session, headers):
    workspace = actors[1][0]
    workspace.plan = 'business'
    workspace.plan_expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()
    response = client.get('/api/v1/subscription/navigation', headers=headers())
    assert response.status_code == 200
    items = [item for section in response.json()['sections'].values() for item in section]
    assert all(not item['context_links'] for item in items)
    assert not {'/clients', '/discovery', '/events', '/devis'} & {item['path'] for item in items}


def test_navigation_keeps_workspace_and_role_checks(client, actors, headers):
    assert client.get('/api/v1/subscription/navigation').status_code == 401
    other = actors[1][1].id
    assert client.get(f'/api/v1/subscription/navigation?workspace_id={other}', headers=headers()).status_code == 403
    response = client.get('/api/v1/subscription/navigation', headers=headers(3))
    assert response.status_code == 200
    items = [item for section in response.json()['sections'].values() for item in section]
    assert '/workspace/settings' not in {item['path'] for item in items}
