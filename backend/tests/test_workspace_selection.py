"""A user authorized in two organizations must still use the selected one only."""

import pytest
from unittest.mock import AsyncMock
from app.db.models.workspace import WorkspaceMember, WorkspaceRole
from app.db.models.agency import Client, Project, ProjectStatus


@pytest.fixture
def collaborator(actors, db_session, monkeypatch):
    users, spaces = actors
    users[0].is_collaborator = True
    for ws in spaces:
        ws.plan = "business"
    db_session.add(
        WorkspaceMember(
            workspace_id=spaces[1].id, user_id=users[0].id, role=WorkspaceRole.ADMIN
        )
    )
    clients = []
    projects = []
    for label, ws in zip(["A", "B"], spaces):
        customer = Client(workspace_id=ws.id, name="TEST Customer " + label)
        db_session.add(customer)
        db_session.flush()
        project = Project(
            workspace_id=ws.id,
            client_id=customer.id,
            name="TEST Project " + label,
            status=ProjectStatus.ACTIVE,
        )
        db_session.add(project)
        db_session.flush()
        clients.append(customer)
        projects.append(project)
    db_session.commit()
    monkeypatch.setattr(
        "app.api.agency_projects.create_project_drive_structure_task", AsyncMock()
    )
    return users[0], spaces, clients, projects


def test_selected_workspace_survives_repeated_dependency_resolution(
    client, headers, collaborator
):
    _, spaces, _, projects = collaborator
    authorization = headers(0)
    for index in [1, 0, 1]:
        selected = spaces[index].id
        response = client.get(
            f"/api/v1/agency/projects?workspace_id={selected}", headers=authorization
        )
        assert response.status_code == 200, response.text
        assert [row["id"] for row in response.json()] == [projects[index].id]
        subscription = client.get(
            f"/api/v1/subscription/current?workspace_id={selected}",
            headers=authorization,
        )
        assert subscription.status_code == 200
        assert subscription.json()["workspace_id"] == selected


def test_project_from_a_cannot_be_opened_or_modified_in_b_context(
    client, headers, collaborator
):
    _, spaces, _, projects = collaborator
    authorization = headers(0)
    query = f"?workspace_id={spaces[1].id}"
    assert (
        client.get(
            f"/api/v1/agency/projects/{projects[0].id}" + query, headers=authorization
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/agency/projects/{projects[0].id}" + query,
            headers=authorization,
            json={"name": "TEST incorrect tenant"},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/agency/projects/{projects[1].id}" + query, headers=authorization
        ).status_code
        == 200
    )


def test_project_creation_in_b_is_persisted_in_b_only(
    client, headers, db_session, collaborator
):
    _, spaces, customers, _ = collaborator
    response = client.post(
        f"/api/v1/agency/projects?workspace_id={spaces[1].id}",
        headers=headers(0),
        json={"name": "TEST new project in B", "client_id": customers[1].id},
    )
    assert response.status_code == 200, response.text
    created = db_session.query(Project).filter_by(id=response.json()["id"]).one()
    assert created.workspace_id == spaces[1].id and created.client_id == customers[1].id
    assert (
        client.post(
            f"/api/v1/agency/projects?workspace_id={spaces[1].id}",
            headers=headers(0),
            json={"name": "TEST wrong client", "client_id": customers[0].id},
        ).status_code
        == 404
    )


def test_request_context_cannot_be_switched_by_a_nested_helper(
    db_session, collaborator
):
    from fastapi import HTTPException
    from app.api.deps import resolve_workspace_id

    user, spaces, _, _ = collaborator
    assert resolve_workspace_id(db_session, user, spaces[1].id) == spaces[1].id
    assert resolve_workspace_id(db_session, user) == spaces[1].id
    with pytest.raises(HTTPException) as refused:
        resolve_workspace_id(db_session, user, spaces[0].id)
    assert refused.value.status_code == 403
    assert db_session.info["workspace_id"] == spaces[1].id
