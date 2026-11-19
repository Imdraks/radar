"""Platform/company boundaries, lifecycle preservation and honest invitation delivery."""

from datetime import datetime, timedelta
import asyncio
import re
import pytest
from app.db.models.client_admin import ClientInvitation
from app.db.models.user import User
from app.db.models.workspace import Workspace
from app.core.security import verify_password


def test_platform_clients_require_real_superuser(client, headers, actors):
    assert client.get("/api/v1/admin/clients").status_code == 401
    assert client.get("/api/v1/admin/clients", headers=headers(0)).status_code == 403
    response = client.get("/api/v1/admin/clients", headers=headers(2))
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert {r["id"] for r in response.json()["items"]} == {w.id for w in actors[1]}
    assert (
        client.get("/api/v1/admin/clients?q=Agency%201", headers=headers(2)).json()[
            "total"
        ]
        == 1
    )


def test_suspension_blocks_members_but_preserves_other_companies(
    client, headers, actors, db_session
):
    ws = actors[1][0]
    before = db_session.query(Workspace).count()
    admin = headers(2)
    assert (
        client.post(
            f"/api/v1/admin/clients/{ws.id}/suspension",
            headers=admin,
            json={"suspended": True, "reason": "TEST contractual pause"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={ws.id}", headers=headers(0)
        ).status_code
        == 423
    )
    assert (
        client.get(f"/api/v1/workspaces/{ws.id}", headers=headers(3)).status_code == 423
    )
    assert (
        client.get(f"/api/v1/workspaces/{ws.id}", headers=headers(1)).status_code == 403
    )
    assert (
        client.get(f"/api/v1/admin/clients/{ws.id}", headers=admin).status_code == 200
    )
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={actors[1][1].id}",
            headers=headers(1),
        ).status_code
        == 200
    )
    assert db_session.query(Workspace).count() == before
    assert (
        client.post(
            f"/api/v1/admin/clients/{ws.id}/suspension",
            headers=admin,
            json={"suspended": False, "reason": "TEST resolved"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={ws.id}", headers=headers(0)
        ).status_code
        == 200
    )


@pytest.fixture
def invitation_queue(monkeypatch):
    calls = []
    monkeypatch.setattr("app.api.platform_clients.validate_configuration", lambda: None)
    monkeypatch.setattr(
        "app.workers.client_tasks.send_client_invitation.delay",
        lambda value: calls.append(value),
    )
    return calls


def test_new_owner_receives_queued_invitation_without_exposed_password(
    client, headers, db_session, invitation_queue
):
    response = client.post(
        "/api/v1/admin/clients",
        headers=headers(2),
        json={
            "name": "TEST client",
            "owner_email": "new-owner@example.com",
            "owner_name": "TEST Owner",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert "password" not in response.text
    assert invitation_queue == [payload["invitation"]["id"]]
    user = db_session.query(User).filter_by(email="new-owner@example.com").one()
    assert user.must_change_password and user.security_setup_pending
    assert user.hashed_password is None
    assert not user.is_superuser
    assert payload["invitation"]["status"] == "pending"


def test_existing_owner_keeps_account_security(
    client, headers, actors, db_session, invitation_queue
):
    owner = actors[0][0]
    owner.email = "existing-owner@example.com"
    owner.hashed_password = "TEST EXISTING HASH"
    owner.two_factor_enabled = True
    db_session.commit()
    response = client.post(
        "/api/v1/admin/clients",
        headers=headers(2),
        json={
            "name": "TEST second company",
            "owner_email": owner.email,
            "owner_name": "Must not replace name",
        },
    )
    assert response.status_code == 201, response.text
    db_session.refresh(owner)
    assert owner.hashed_password == "TEST EXISTING HASH" and owner.two_factor_enabled
    assert not owner.must_change_password
    assert owner.full_name == "User 0"
    assert response.json()["invitation"]["kind"] == "workspace_access"


def test_failed_delivery_does_not_create_usable_credential(
    client, headers, db_session, invitation_queue, monkeypatch
):
    from app.services.client_provisioning import deliver_invitation

    created = client.post(
        "/api/v1/admin/clients",
        headers=headers(2),
        json={
            "name": "TEST failed email",
            "owner_email": "failed@example.com",
            "owner_name": "TEST Owner",
        },
    ).json()
    row = db_session.query(ClientInvitation).filter_by(workspace_id=created["id"]).one()
    monkeypatch.setattr(
        "app.services.client_provisioning.validate_configuration", lambda: None
    )
    from app.core.config import settings

    monkeypatch.setattr(settings, "resend_api_key", "test-delivery-only")

    async def failed(*args, **kwargs):
        raise RuntimeError("DO NOT EXPOSE PROVIDER ERROR")

    monkeypatch.setattr(
        "app.services.client_provisioning.EmailService.send_email", failed
    )
    asyncio.run(deliver_invitation(db_session, row.id))
    db_session.refresh(row)
    assert row.status == "failed" and row.error_code == "DELIVERY_FAILED"
    assert db_session.get(User, row.user_id).hashed_password is None
    detail = client.get(
        f'/api/v1/admin/clients/{created["id"]}', headers=headers(2)
    ).json()
    assert "DO NOT EXPOSE" not in str(detail)


def test_delivered_temporary_password_is_hashed_and_expires(
    client, headers, db_session, invitation_queue, monkeypatch
):
    from app.services.client_provisioning import deliver_invitation

    created = client.post(
        "/api/v1/admin/clients",
        headers=headers(2),
        json={
            "name": "TEST email",
            "owner_email": "sent@example.com",
            "owner_name": "TEST Owner",
        },
    ).json()
    row = db_session.query(ClientInvitation).filter_by(workspace_id=created["id"]).one()
    monkeypatch.setattr(
        "app.services.client_provisioning.validate_configuration", lambda: None
    )
    from app.core.config import settings

    monkeypatch.setattr(settings, "resend_api_key", "test-delivery-only")
    captured = []

    async def sent(*args, **kwargs):
        captured.append(args[-1])
        return {"id": "TEST-mail-id"}

    monkeypatch.setattr(
        "app.services.client_provisioning.EmailService.send_email", sent
    )
    asyncio.run(deliver_invitation(db_session, row.id))
    user = db_session.get(User, row.user_id)
    secret = re.search(r"Mot de passe temporaire : (\S+)", captured[0]).group(1)
    assert verify_password(secret, user.hashed_password)
    assert user.must_change_password
    assert (
        datetime.utcnow() + timedelta(hours=23)
        < user.temporary_password_expires_at
        < datetime.utcnow() + timedelta(hours=25)
    )
    assert row.status == "sent"
    asyncio.run(deliver_invitation(db_session, row.id))
    assert len(captured) == 1  # Broker redelivery is idempotent.
    assert secret not in str(
        client.get(f'/api/v1/admin/clients/{created["id"]}', headers=headers(2)).json()
    )


def test_first_login_requires_new_password_then_allows_optional_security_later(
    client, headers, actors, db_session
):
    from app.core.security import get_password_hash

    user = actors[0][0]
    user.email = "temporary@example.com"
    user.hashed_password = get_password_hash("Temporary!Strong2026")
    user.must_change_password = True
    user.security_setup_pending = True
    user.temporary_password_expires_at = datetime.utcnow() + timedelta(hours=24)
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Temporary!Strong2026"},
    )
    assert login.status_code == 200, login.text
    auth = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert (
        client.get("/api/v1/auth/me", headers=auth).json()["must_change_password"]
        is True
    )
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={actors[1][0].id}", headers=auth
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/account/setup/complete",
            headers=auth,
            json={"security": "later"},
        ).status_code
        == 403
    )
    changed = client.post(
        "/api/v1/auth/password/change",
        headers=auth,
        json={
            "current_password": "Temporary!Strong2026",
            "new_password": "My-New-Private!2026",
            "confirm_password": "My-New-Private!2026",
        },
    )
    assert changed.status_code == 200, changed.text
    auth = {"Authorization": "Bearer " + changed.json()["access_token"]}
    me = client.get("/api/v1/auth/me", headers=auth).json()
    assert me["must_change_password"] is False and me["security_setup_pending"] is True
    assert (
        client.post(
            "/api/v1/auth/account/setup/complete",
            headers=auth,
            json={"security": "configured"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/auth/account/setup/complete",
            headers=auth,
            json={"security": "later"},
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/auth/me", headers=auth).json()["security_setup_pending"]
        is False
    )
    assert (
        client.get(
            f"/api/v1/agency/projects?workspace_id={actors[1][0].id}", headers=auth
        ).status_code
        == 200
    )


def test_expired_temporary_password_cannot_log_in(client, actors, db_session):
    from app.core.security import get_password_hash

    user = actors[0][0]
    user.email = "expired-temp@example.com"
    user.hashed_password = get_password_hash("Temporary!Strong2026")
    user.must_change_password = True
    user.temporary_password_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Temporary!Strong2026"},
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_resend_is_scoped_and_rate_limited_without_exposing_password(
    client, headers, actors, db_session, invitation_queue
):
    created = client.post(
        "/api/v1/admin/clients",
        headers=headers(2),
        json={
            "name": "TEST resend",
            "owner_email": "resend@example.com",
            "owner_name": "TEST Owner",
        },
    ).json()
    row = db_session.query(ClientInvitation).filter_by(workspace_id=created["id"]).one()
    endpoint = f'/api/v1/admin/clients/{created["id"]}/invitations/{row.user_id}/resend'
    assert client.post(endpoint, headers=headers(2)).status_code == 429
    assert (
        client.post(
            f"/api/v1/admin/clients/{actors[1][1].id}/invitations/{row.user_id}/resend",
            headers=headers(2),
        ).status_code
        == 404
    )
    row.created_at = datetime.utcnow() - timedelta(minutes=2)
    db_session.commit()
    response = client.post(endpoint, headers=headers(2))
    assert response.status_code == 202, response.text
    db_session.refresh(row)
    assert row.status == "superseded"
    assert len(invitation_queue) == 2
    assert "password" not in response.text


def test_capacity_and_owner_transfer_preserve_members_and_global_roles(
    client, headers, actors, db_session
):
    from app.db.models.workspace import WorkspaceMember

    ws = actors[1][0]
    previous = ws.owner_user_id
    target = db_session.query(WorkspaceMember).filter_by(workspace_id=ws.id).first()
    new_owner = db_session.get(User, target.user_id)
    role = new_owner.role
    assert (
        client.post(
            f"/api/v1/admin/clients/{ws.id}/capacity",
            headers=headers(2),
            json={"max_seats": 1, "authorization_reference": "TEST seat authorization"},
        ).status_code
        == 409
    )
    result = client.post(
        f"/api/v1/admin/clients/{ws.id}/owner",
        headers=headers(2),
        json={"user_id": new_owner.id},
    )
    assert result.status_code == 200, result.text
    db_session.refresh(ws)
    db_session.refresh(new_owner)
    assert ws.owner_user_id == new_owner.id and new_owner.role == role
    assert (
        db_session.query(WorkspaceMember)
        .filter_by(workspace_id=ws.id, user_id=previous)
        .one()
        .role.value
        == "admin"
    )
    assert (
        client.post(
            f"/api/v1/admin/clients/{ws.id}/owner",
            headers=headers(2),
            json={"user_id": actors[0][1].id},
        ).status_code
        == 409
    )
