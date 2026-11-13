from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from app.db.models.privacy import PrivacyRequest


def test_rights_are_authenticated_not_subscription_gated_and_do_not_delete(
    client, actors, headers, db_session
):
    assert (
        client.post("/api/v1/privacy/requests", json={"kind": "erasure"}).status_code
        == 401
    )
    result = client.post(
        "/api/v1/privacy/requests", headers=headers(3), json={"kind": "erasure"}
    )
    assert result.status_code == 201, result.text
    assert result.json()["status"] == "received"
    db_session.refresh(actors[0][3])
    assert actors[0][3].is_active is True
    assert (
        client.get("/api/v1/privacy/requests", headers=headers(3)).headers[
            "cache-control"
        ]
        == "no-store"
    )
    assert client.get("/api/v1/privacy/requests", headers=headers()).json() == []
    assert (
        client.post(
            "/api/v1/privacy/requests",
            headers=headers(),
            json={"kind": "access", "status": "answered", "user_id": actors[0][1].id},
        ).status_code
        == 422
    )


def test_workspace_rights_require_membership_and_administration(
    client, actors, headers
):
    other = actors[1][1].id
    own = actors[1][0].id
    for kind in ["access", "switching", "cancellation"]:
        assert (
            client.post(
                f"/api/v1/privacy/requests?workspace_id={other}",
                headers=headers(),
                json={"kind": kind, "scope": "workspace"},
            ).status_code
            == 403
        )
    assert (
        client.post(
            f"/api/v1/privacy/requests?workspace_id={own}",
            headers=headers(3),
            json={"kind": "switching", "scope": "workspace"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/privacy/requests?workspace_id={own}",
            headers=headers(),
            json={"kind": "switching", "scope": "workspace"},
        ).status_code
        == 201
    )


def test_response_uses_calendar_month_and_leap_year(
    client, headers, actors, monkeypatch
):
    import app.api.privacy as module

    class FrozenDate(datetime):
        @classmethod
        def utcnow(cls):
            return datetime(2028, 1, 31, 12, 0, 0)

    monkeypatch.setattr(module, "datetime", FrozenDate)
    result = client.post(
        "/api/v1/privacy/requests", headers=headers(), json={"kind": "access"}
    )
    assert result.status_code == 201, result.text
    assert result.json()["response_due_at"] == "2028-02-29T12:00:00"
    assert result.json()["created_at"] == "2028-01-31T12:00:00"


def test_only_platform_operator_can_answer_and_response_is_traceable(
    client, headers, actors, db_session
):
    result = client.post(
        "/api/v1/privacy/requests",
        headers=headers(),
        json={"kind": "rectification", "details": "TEST — corriger mon nom"},
    )
    request_id = result.json()["id"]
    assert (
        client.get("/api/v1/privacy/admin/requests", headers=headers()).status_code
        == 403
    )
    payload = {
        "status": "answered",
        "response": "TEST — réponse de recette disponible dans le compte",
        "reference": "TEST-case-123",
    }
    assert (
        client.post(
            f"/api/v1/privacy/admin/requests/{request_id}/respond",
            headers=headers(),
            json=payload,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/privacy/admin/requests/{request_id}/respond",
            headers=headers(2),
            json=payload,
        ).status_code
        == 200
    )
    row = db_session.get(PrivacyRequest, request_id)
    db_session.refresh(row)
    assert row.audit_log[-1]["by"] == actors[0][2].id
    assert row.audit_log[-1]["reference"] == "TEST-case-123"
    assert (
        client.get("/api/v1/privacy/requests", headers=headers()).json()[0]["response"]
        == payload["response"]
    )
    assert client.get("/api/v1/privacy/requests", headers=headers(1)).json() == []
    assert (
        client.post(
            f"/api/v1/privacy/admin/requests/{request_id}/respond",
            headers=headers(2),
            json=payload,
        ).status_code
        == 409
    )
    assert client.get("/api/v1/privacy/admin/requests", headers=headers(2)).json() == []


def test_partial_account_export_excludes_credentials_and_other_people(
    client, headers, actors, db_session
):
    actors[0][0].two_factor_secret = "TEST-private-2fa"
    actors[0][0].hashed_password = "TEST-private-hash"
    db_session.commit()
    client.post(
        "/api/v1/privacy/requests",
        headers=headers(),
        json={"kind": "access", "details": "my-private-case"},
    )
    client.post(
        "/api/v1/privacy/requests",
        headers=headers(1),
        json={"kind": "access", "details": "foreign-private-case"},
    )
    response = client.get("/api/v1/privacy/account-export", headers=headers())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["scope"] == "account_identity_and_own_requests"
    for secret in [
        "TEST-private-2fa",
        "TEST-private-hash",
        "foreign-private-case",
        actors[0][1].email,
        "hashed_password",
        "two_factor_secret",
        "access_token",
    ]:
        assert secret not in response.text
    assert "my-private-case" in response.text
    assert response.json()["coverage_note"]


@pytest.fixture
def contact_delivery(monkeypatch):
    from app.api.contact import settings
    from app.services.email_service import EmailService

    monkeypatch.setattr(settings, "contact_receiver_email", "test-operator@example.com")
    monkeypatch.setattr(EmailService, "is_configured", property(lambda self: True))
    send = AsyncMock(return_value={"id": "test-delivery-id"})
    monkeypatch.setattr(EmailService, "send_email", send)
    return send


def test_contact_information_version_and_minimization(client, contact_delivery, caplog):
    body = {
        "name": "TEST contact",
        "email": "test-contact@example.com",
        "message": "Demande de démonstration professionnelle",
    }
    assert client.post("/api/v1/contact", json=body).status_code == 422
    body["privacy_notice_version"] = "2026-11-13"
    assert (
        client.post("/api/v1/contact", json={**body, "phone": "x" * 41}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/contact", json={**body, "name": "TEST\r\nInjected"}
        ).status_code
        == 422
    )
    result = client.post("/api/v1/contact", json=body)
    assert result.status_code == 200, result.text
    assert "Notice présentée : 2026-11-13" in contact_delivery.call_args.kwargs["text"]
    assert "test-contact@example.com" not in caplog.text


def test_contact_never_reports_unconfirmed_delivery(client, contact_delivery, caplog):
    body = {
        "name": "TEST contact",
        "email": "test-contact@example.com",
        "message": "TEST request",
        "privacy_notice_version": "2026-11-13",
    }
    for reply in [{"error": "TEST-sensitive-provider-response"}, {}]:
        contact_delivery.return_value = reply
        assert client.post("/api/v1/contact", json=body).status_code == 500
    assert "TEST-sensitive-provider-response" not in caplog.text


def test_unconfigured_contact_channel_is_explicit(
    client, contact_delivery, monkeypatch
):
    from app.api.contact import settings

    monkeypatch.setattr(settings, "contact_receiver_email", "")
    assert (
        client.post(
            "/api/v1/contact",
            json={
                "name": "TEST name",
                "email": "test@example.com",
                "message": "TEST request",
                "privacy_notice_version": "2026-11-13",
            },
        ).status_code
        == 503
    )
    contact_delivery.assert_not_called()
