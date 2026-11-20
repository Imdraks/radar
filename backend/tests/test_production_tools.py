"""Real DB flows: reusable plans, scoped search and version-bound external decisions."""

from datetime import datetime, timedelta
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
import pytest
from app.db.models.agency import (
    Client,
    Project,
    Deliverable,
    Approval,
    ApprovalStatus,
    DeliverableStatus,
)
from app.db.models.production_tools import ProductionTemplate, DeliverableReview
from app.db.models.workspace import WorkspaceMember, WorkspaceRole
from app.db.models.discovery import DiscoveryArtist, DiscoverySnapshot


def project(db, workspace):
    client = Client(name="Private Client", workspace_id=workspace.id)
    db.add(client)
    db.flush()
    row = Project(
        name="Private Production", client_id=client.id, workspace_id=workspace.id
    )
    db.add(row)
    db.flush()
    item = Deliverable(
        project_id=row.id,
        name="Private Deliverable",
        link="https://example.com/version-1",
        notes="PRIVATE INTERNAL NOTES",
    )
    db.add(item)
    db.commit()
    return row, item


def grant(client, headers, item, query=""):
    response = client.post(
        f"/api/v1/workbench/deliverables/{item.id}/reviews" + query,
        headers=headers(),
        json={},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return data, parse_qs(urlsplit(data["url"]).fragment)["token"][0]


def test_template_instantiation_is_atomic_and_scoped(
    client, headers, actors, db_session
):
    data = {
        "name": "Film",
        "kind": "project",
        "definition": {
            "tasks": [{"title": "Brief", "day": -1}],
            "deliverables": [{"title": "Export", "day": 2}],
        },
    }
    result = client.post("/api/v1/workbench/templates", headers=headers(), json=data)
    assert result.status_code == 201, result.text
    id = result.json()["id"]
    assert client.get("/api/v1/workbench/templates", headers=headers(1)).json() == []
    assert (
        client.post(
            f"/api/v1/workbench/templates/{id}/instantiate",
            headers=headers(1),
            json={"name": "Other", "starts_at": "2026-11-20T12:00:00"},
        ).status_code
        == 404
    )
    made = client.post(
        f"/api/v1/workbench/templates/{id}/instantiate",
        headers=headers(),
        json={"name": "Real production", "starts_at": "2026-11-20T12:00:00"},
    )
    assert made.status_code == 201, made.text
    row = db_session.get(Project, made.json()["project_id"])
    assert row.workspace_id == actors[1][0].id
    assert row.tasks[0].due_date == datetime(2026, 11, 19, 12)
    assert row.deliverables[0].due_date == datetime(2026, 11, 22, 12)
    assert row.owner_id == actors[0][0].id
    assert (
        client.post(
            "/api/v1/workbench/templates",
            headers=headers(),
            json={**data, "kind": "event"},
        ).status_code
        == 403
    )


def test_search_never_crosses_workspace_or_plan(client, headers, actors, db_session):
    a, _ = project(db_session, actors[1][0])
    project(db_session, actors[1][1])
    db_session.add(
        WorkspaceMember(
            workspace_id=actors[1][1].id,
            user_id=actors[0][0].id,
            role=WorkspaceRole.MEMBER,
        )
    )
    db_session.commit()
    result = client.get("/api/v1/workbench/search?q=Private", headers=headers())
    assert result.status_code == 200, result.text
    data = result.json()
    assert len(data) == 2
    assert {r["kind"] for r in data} == {"project", "deliverable"}
    assert (
        client.get("/api/v1/workbench/search?q=%25%25", headers=headers()).json() == []
    )
    b = client.get(
        f"/api/v1/workbench/search?q=Private&workspace_id={actors[1][1].id}",
        headers=headers(),
    ).json()
    assert not {r["id"] for r in data} & {r["id"] for r in b}


def test_review_hash_only_no_internal_notes_and_single_decision(
    client, headers, actors, db_session
):
    _, item = project(db_session, actors[1][0])
    data, token = grant(client, headers, item)
    row = db_session.get(DeliverableReview, data["id"])
    assert row.token_hash != token and token not in str(row.snapshot)
    resolved = client.post("/api/v1/review/resolve", json={"token": token})
    assert resolved.status_code == 200, resolved.text
    assert "PRIVATE INTERNAL" not in resolved.text
    decision = client.post(
        "/api/v1/review/decide",
        json={"token": token, "decision": "approved", "name": "Declared Client"},
    )
    assert decision.status_code == 200, decision.text
    db_session.expire_all()
    assert db_session.get(Deliverable, item.id).status == DeliverableStatus.APPROVED
    assert db_session.get(Approval, row.approval_id).status == ApprovalStatus.APPROVED
    assert (
        client.post(
            "/api/v1/review/decide",
            json={
                "token": token,
                "decision": "changes",
                "name": "Someone else",
                "feedback": "No",
            },
        ).status_code
        == 409
    )
    assert (
        client.post("/api/v1/review/resolve", json={"token": token}).json()["status"]
        == "approved"
    )


def test_review_changes_expiry_revocation_and_content_version(
    client, headers, actors, db_session
):
    _, item = project(db_session, actors[1][0])
    data, token = grant(client, headers, item)
    assert (
        client.post(
            "/api/v1/review/decide",
            json={
                "token": token,
                "decision": "changes",
                "name": "Client",
                "feedback": "   ",
            },
        ).status_code
        == 422
    )
    item.link = "https://example.com/version-2"
    db_session.commit()
    assert (
        client.post("/api/v1/review/resolve", json={"token": token}).status_code == 409
    )
    second, token2 = grant(client, headers, item)
    assert (
        client.post("/api/v1/review/resolve", json={"token": token}).status_code == 410
    )
    assert (
        client.post(
            f"/api/v1/workbench/reviews/{second['id']}/revoke", headers=headers(1)
        ).status_code
        == 404
    )
    row = db_session.get(DeliverableReview, second["id"])
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert (
        client.post("/api/v1/review/resolve", json={"token": token2}).status_code == 410
    )
    third, token3 = grant(client, headers, item)
    r = client.post(
        "/api/v1/review/decide",
        json={
            "token": token3,
            "decision": "changes",
            "name": "Client",
            "feedback": "Changer le titre",
        },
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert (
        db_session.get(Deliverable, item.id).status
        == DeliverableStatus.CHANGES_REQUESTED
    )


def test_suspension_blocks_external_grants_and_viewers_cannot_write(
    client, headers, actors, db_session
):
    _, item = project(db_session, actors[1][0])
    data, token = grant(client, headers, item)
    assert (
        client.post(
            f"/api/v1/workbench/deliverables/{item.id}/reviews",
            headers=headers(3),
            json={},
        ).status_code
        == 403
    )
    actors[1][0].is_suspended = True
    db_session.commit()
    assert (
        client.post("/api/v1/review/resolve", json={"token": token}).status_code == 410
    )
    assert (
        client.get("/api/v1/workbench/search?q=Private", headers=headers()).status_code
        == 423
    )


def test_integration_status_never_infers_success_or_exposes_secrets(
    client, headers, actors, db_session, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "spotify_client_id", "TEST-SECRET-ID")
    monkeypatch.setattr(settings, "spotify_client_secret", "TEST-SECRET")
    monkeypatch.setattr("app.api.integration_status.cache_get", lambda key: None)
    assert client.get("/api/v1/integrations/status").status_code == 401
    response = client.get("/api/v1/integrations/status", headers=headers())
    assert response.status_code == 200, response.text
    assert response.json()["observations"] == []
    assert "spotify" not in {p["id"] for p in response.json()["providers"]}
    assert "TEST-SECRET" not in response.text
    actors[1][0].plan = "premium"
    db_session.commit()
    artist = DiscoveryArtist(
        workspace_id=actors[1][1].id,
        canonical_name="Secret Artist",
        normalized_name="secretartist",
    )
    db_session.add(artist)
    db_session.flush()
    db_session.add(
        DiscoverySnapshot(
            artist_id=artist.id,
            source="SPOTIFY",
            status="OK",
            fetched_at=datetime.utcnow(),
            ttl_expires_at=datetime.utcnow() + timedelta(hours=1),
            raw_payload={"secret": "HIDE-ME"},
        )
    )
    db_session.commit()
    response = client.get("/api/v1/integrations/status", headers=headers())
    spotify = next(p for p in response.json()["providers"] if p["id"] == "spotify")
    assert spotify["state"] == "configured_unverified"
    assert response.json()["observations"] == []
    assert "HIDE-ME" not in response.text


def test_event_template_respects_feature_and_dates(client, headers, actors, db_session):
    actors[1][0].plan = "premium"
    db_session.commit()
    response = client.post(
        "/api/v1/workbench/templates",
        headers=headers(),
        json={
            "name": "Concert",
            "kind": "event",
            "definition": {
                "tasks": [{"title": "Balance", "day": -1}],
                "deliverables": [],
            },
        },
    )
    assert response.status_code == 201, response.text
    id = response.json()["id"]
    url = f"/api/v1/workbench/templates/{id}/instantiate"
    assert (
        client.post(
            url,
            headers=headers(),
            json={"name": "Concert", "starts_at": "2026-11-20T12:00:00"},
        ).status_code
        == 422
    )
    assert db_session.query(Project).count() == 0
    response = client.post(
        url,
        headers=headers(),
        json={
            "name": "Concert",
            "starts_at": "2026-11-20T12:00:00",
            "ends_at": "2026-11-20T23:00:00",
        },
    )
    assert response.status_code == 201, response.text
    id = response.json()["project_id"]
    connection = client.get(
        f"/api/v1/workbench/projects/{id}/connections", headers=headers()
    ).json()
    assert connection["event_id"] == response.json()["event_id"]
    assert connection["client_id"] is None


def test_new_migration_refuses_losing_used_plans(engine):
    from test_migrations import load_migration
    from alembic.runtime.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    schema = "tools_" + uuid4().hex
    with engine.connect() as connection, connection.begin():
        connection.execute(text(f"CREATE SCHEMA {schema}"))
        connection.execute(text(f"SET LOCAL search_path TO {schema}"))
        for table in ["workspaces", "deliverables", "approvals"]:
            connection.execute(text(f"CREATE TABLE {table}(id integer primary key)"))
        migration = load_migration("066_production_tools.py")
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.downgrade()
            migration.upgrade()
            connection.execute(text("INSERT INTO workspaces VALUES(1)"))
            connection.execute(
                text(
                    "INSERT INTO production_templates(workspace_id,name,kind,definition,created_at) VALUES(1,'Saved plan','project','{}',now())"
                )
            )
            with pytest.raises(RuntimeError):
                migration.downgrade()
        connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))


def test_external_history_blocks_physical_deletion_and_deleted_workspaces(
    client, headers, actors, db_session
):
    parent, item = project(db_session, actors[1][0])
    data, token = grant(client, headers, item)
    assert (
        client.delete(
            f"/api/v1/agency/deliverables/{item.id}", headers=headers()
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/agency/projects/deliverables/{item.id}", headers=headers()
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/agency/projects/{parent.id}", headers=headers()
        ).status_code
        == 409
    )
    actors[1][0].deleted_at = datetime.utcnow()
    db_session.commit()
    assert (
        client.post("/api/v1/review/resolve", json={"token": token}).status_code == 410
    )


def test_review_reissues_reuse_pending_approval(client, headers, actors, db_session):
    _, item = project(db_session, actors[1][0])
    first, token = grant(client, headers, item)
    second, token2 = grant(client, headers, item)
    assert db_session.query(Approval).filter_by(deliverable_id=item.id).count() == 1
    assert (
        client.post("/api/v1/review/resolve", json={"token": token}).status_code == 410
    )
    assert (
        client.post("/api/v1/review/resolve", json={"token": token2}).status_code == 200
    )
