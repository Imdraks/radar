"""Real PostgreSQL/API proofs for published terms, activation and tenant archive."""

import hashlib
import io
import json
from zipfile import ZipFile
import pytest
from app.api.legal_contracts import DOCUMENT_KEYS
from app.db.models.agency import Project, Client, AgencyTask
from app.db.models.legal_contract import LegalBundle, LegalAcceptance


def publish_test_bundle(client, headers, version="test-2026.1"):
    # Explicit fixtures only; no real company identity or signed legal advice is implied.
    from legal_test_data import TEST_PUBLISHER

    publisher = TEST_PUBLISHER
    body = {
        "version": version,
        "publisher": publisher,
        "documents": {
            key: ("TEST fixture — not a production agreement. " * 5)
            for key in DOCUMENT_KEYS
        },
        "review_reference": "TEST legal review",
        "reviewed_for_publication": True,
    }
    response = client.post(
        "/api/v1/legal-contracts/admin/publish", headers=headers(2), json=body
    )
    assert response.status_code == 201, response.text
    return response.json(), body


def accept_test_bundle(client, headers, workspace_id, bundle, index=0, plan="business"):
    response = client.post(
        f"/api/v1/legal-contracts/acceptances?workspace_id={workspace_id}",
        headers=headers(index),
        json={
            "bundle_id": bundle["id"],
            "content_hash": bundle["content_hash"],
            "accepted": True,
            "authorized_representative": True,
            "plan": plan,
            "commercial_reference": "TEST-OFFER-1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_publication_requires_operator_and_cannot_rewrite_a_version(
    client, headers, actors
):
    assert client.get("/api/v1/legal-contracts/current").status_code == 404
    bundle, body = publish_test_bundle(client, headers)
    assert (
        client.post(
            "/api/v1/legal-contracts/admin/publish", headers=headers(), json=body
        ).status_code
        == 403
    )
    assert (
        client.get("/api/v1/legal-contracts/current").json()["content_hash"]
        == bundle["content_hash"]
    )
    assert (
        client.post(
            "/api/v1/legal-contracts/admin/publish", headers=headers(2), json=body
        ).json()["id"]
        == bundle["id"]
    )
    body["documents"]["dpa"] += " Changed terms"
    assert (
        client.post(
            "/api/v1/legal-contracts/admin/publish", headers=headers(2), json=body
        ).status_code
        == 409
    )
    body["version"] = "new-version"
    body["documents"]["dpa"] += " [[missing_party]]"
    assert (
        client.post(
            "/api/v1/legal-contracts/admin/publish", headers=headers(2), json=body
        ).status_code
        == 422
    )


def test_acceptance_is_explicit_scoped_versioned_and_not_an_activation(
    client, headers, actors, db_session
):
    bundle, _ = publish_test_bundle(client, headers)
    path = f"/api/v1/legal-contracts/acceptances?workspace_id={actors[1][0].id}"
    body = {
        "bundle_id": bundle["id"],
        "content_hash": bundle["content_hash"],
        "accepted": True,
        "authorized_representative": True,
        "plan": "business",
        "commercial_reference": "TEST-OFFER-1",
    }
    assert client.post(path, json=body).status_code == 401
    assert client.post(path, headers=headers(1), json=body).status_code == 403
    assert client.post(path, headers=headers(3), json=body).status_code == 403
    assert (
        client.post(
            path, headers=headers(), json={**body, "accepted": False}
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, headers=headers(), json={**body, "content_hash": "0" * 64}
        ).status_code
        == 409
    )
    result = accept_test_bundle(client, headers, actors[1][0].id, bundle)
    assert result["rights_activated"] is False and result["payment_confirmed"] is False
    assert (
        client.get("/api/v1/subscription/current", headers=headers()).json()["plan"]
        == "core"
    )
    assert (
        accept_test_bundle(client, headers, actors[1][0].id, bundle)["id"]
        == result["id"]
    )
    publish_test_bundle(client, headers, "test-2026.2")
    assert client.post(path, headers=headers(), json=body).status_code == 409
    assert (
        client.get("/api/v1/legal-contracts/versions/" + str(bundle["id"])).json()[
            "content_hash"
        ]
        == bundle["content_hash"]
    )
    row = db_session.get(LegalAcceptance, result["id"])
    assert row.representative["email"] == actors[0][0].email


def test_operator_approval_requires_matching_workspace_and_plan_acceptance(
    client, headers, actors
):
    bundle, _ = publish_test_bundle(client, headers)
    entry = client.post(
        "/api/v1/subscription/change-plan", headers=headers(), json={"plan": "business"}
    ).json()["request_id"]
    path = f"/api/v1/subscription/admin/requests/{entry}/decision"
    decision = {
        "approve": True,
        "authorization_reference": "TEST verified commercial agreement",
    }
    assert client.post(path, headers=headers(2), json=decision).status_code == 409
    wrong = accept_test_bundle(client, headers, actors[1][1].id, bundle, index=1)
    assert (
        client.post(
            path,
            headers=headers(2),
            json={**decision, "contract_acceptance_id": wrong["id"]},
        ).status_code
        == 409
    )
    wrong_plan = accept_test_bundle(
        client, headers, actors[1][0].id, bundle, plan="premium"
    )
    assert (
        client.post(
            path,
            headers=headers(2),
            json={**decision, "contract_acceptance_id": wrong_plan["id"]},
        ).status_code
        == 409
    )
    right = accept_test_bundle(client, headers, actors[1][0].id, bundle)
    assert (
        client.post(
            path,
            headers=headers(2),
            json={**decision, "contract_acceptance_id": right["id"]},
        ).status_code
        == 200
    )


def test_workspace_archive_is_admin_only_and_contains_scoped_children_without_secrets(
    client, headers, actors, db_session
):
    for index, workspace in enumerate(actors[1]):
        workspace.settings = {"api_key": "NEVER_EXPORT_SETTING"}
        c = Client(workspace_id=workspace.id, name="CLIENT_" + str(index))
        db_session.add(c)
        db_session.flush()
        p = Project(
            workspace_id=workspace.id, client_id=c.id, name="PROJECT_" + str(index)
        )
        db_session.add(p)
        db_session.flush()
        db_session.add(AgencyTask(project_id=p.id, title="TASK_" + str(index)))
    actors[0][0].hashed_password = "NEVER_EXPORT_HASH"
    db_session.commit()
    path = f"/api/v1/privacy/workspace-export?workspace_id={actors[1][0].id}"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers(1)).status_code == 403
    assert client.get(path, headers=headers(3)).status_code == 403
    response = client.get(path, headers=headers())
    assert response.status_code == 200, (
        response.text[:300] if response.status_code != 200 else ""
    )
    assert response.headers["cache-control"] == "no-store"
    with ZipFile(io.BytesIO(response.content)) as z:
        manifest = json.loads(z.read("manifest.json"))
        for name, digest in manifest["sha256"].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == digest
        data = "".join(z.read(name).decode() for name in z.namelist())
        assert "PROJECT_0" in data and "TASK_0" in data
        assert "PROJECT_1" not in data and "TASK_1" not in data
        assert "NEVER_EXPORT_HASH" not in data and "NEVER_EXPORT_SETTING" not in data
        assert actors[0][1].email not in z.read("data/member_directory.json").decode()
        assert "accounts" in manifest["excluded_tables"]
        assert manifest["database_snapshot"] == "single PostgreSQL statement"
    assert (
        client.get("/api/v1/subscription/current", headers=headers()).json()["plan"]
        == "core"
    )


def test_archive_size_limit_never_returns_a_partial_success(
    client, headers, actors, monkeypatch
):
    monkeypatch.setattr("app.services.workspace_export.MAX_ROWS", 0)
    response = client.get(
        f"/api/v1/privacy/workspace-export?workspace_id={actors[1][0].id}",
        headers=headers(),
    )
    assert response.status_code == 413


def test_export_policy_requires_schema_review(monkeypatch):
    from app.services import workspace_export as export
    from fastapi import HTTPException

    monkeypatch.setitem(export.POLICY["tables"]["workspaces"], "columns", [])
    with pytest.raises(HTTPException) as error:
        export.validate_policy()
    assert error.value.status_code == 503


def test_structured_credentials_are_removed_from_json_and_links():
    from app.services.workspace_export import scrub

    data = scrub(
        {
            "nested": {
                "Authorization": "NEVER",
                "apiKey": "NEVER",
                "credentials": "NEVER",
                "access_key": "NEVER",
                "amount": "12.30",
            },
            "url": "https://user:pass@example.com/file?token=NEVER&name=contract#secret",
        }
    )
    raw = json.dumps(data)
    assert "NEVER" not in raw and "user:pass" not in raw and "#secret" not in raw
    assert data["nested"]["amount"] == "12.30"


def test_retention_inventory_is_scoped_read_only_and_does_not_invent_a_duration(
    client, headers, actors, db_session
):
    db_session.add(Client(workspace_id=actors[1][0].id, name="Own contact"))
    db_session.add(Client(workspace_id=actors[1][1].id, name="Other contact"))
    db_session.commit()
    path = f"/api/v1/privacy/retention-inventory?workspace_id={actors[1][0].id}"
    assert client.get(path, headers=headers(1)).status_code == 403
    assert client.get(path, headers=headers(3)).status_code == 403
    response = client.get(path, headers=headers())
    assert response.status_code == 200, response.text
    assert response.json()["automatic_erasure_enabled"] is False
    assert response.headers["cache-control"] == "no-store"
    assert db_session.query(Client).count() == 2


def test_workspace_export_excludes_mixed_tenant_relations(
    client, headers, actors, db_session
):
    from app.db.models.agency import Deal

    c0 = Client(workspace_id=actors[1][0].id, name="OWN")
    c1 = Client(workspace_id=actors[1][1].id, name="OTHER")
    db_session.add_all([c0, c1])
    db_session.flush()
    p0 = Project(workspace_id=actors[1][0].id, client_id=c0.id, name="OWN PROJECT")
    d1 = Deal(client_id=c1.id, title="OTHER DEAL")
    db_session.add_all([p0, d1])
    db_session.flush()
    # An imported inconsistent row must not leak through an OR(project, deal) ownership rule.
    db_session.add(
        AgencyTask(project_id=p0.id, deal_id=d1.id, title="NEVER MIXED TENANT TASK")
    )
    db_session.commit()
    response = client.get(
        f"/api/v1/privacy/workspace-export?workspace_id={actors[1][0].id}",
        headers=headers(),
    )
    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as z:
        assert (
            "NEVER MIXED TENANT TASK" not in z.read("data/agency_tasks.json").decode()
        )


def test_publication_requires_the_verified_configured_identity(
    client, headers, actors, monkeypatch
):
    from app.core.config import settings

    _, body = publish_test_bundle(client, headers)
    body["version"] = "test-mismatch"
    body["publisher"]["name"] = "Different publisher"
    assert (
        client.post(
            "/api/v1/legal-contracts/admin/publish", headers=headers(2), json=body
        ).status_code
        == 409
    )
    monkeypatch.setattr(settings, "legal_publisher_fingerprint", "")
    assert (
        client.post(
            "/api/v1/legal-contracts/admin/publish", headers=headers(2), json=body
        ).status_code
        == 503
    )
