"""Real inbox persistence and first-open mail; no real email or broker calls."""

from datetime import datetime, timedelta
from uuid import UUID
from unittest.mock import AsyncMock
import asyncio
import pytest
from sqlalchemy.orm import Session
from app.db.models.contact_inquiry import ContactInquiry
from app.services.contact_acknowledgement import deliver_open_acknowledgement

BODY = {
    "name": "TEST Client",
    "email": "visitor@example.com",
    "company": "TEST Agency",
    "phone": "0102030405",
    "plan": "premium",
    "message": "TEST confidential request <script>unsafe()</script>",
    "privacy_notice_version": "2026-11-13",
}


def submit(client):
    response = client.post("/api/v1/contact", json=BODY)
    assert response.status_code == 200, response.text
    return response.json()["reference"]


@pytest.fixture
def queue(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.workers.contact_tasks.acknowledge_opened_request.delay",
        lambda id: calls.append(id),
    )
    return calls


@pytest.fixture
def mail(monkeypatch):
    monkeypatch.setattr(
        "app.services.contact_acknowledgement.availability", lambda: {"email": True}
    )
    from app.services.email_service import EmailService

    monkeypatch.setattr(EmailService, "is_configured", property(lambda self: True))
    send = AsyncMock(return_value={"id": "TEST-delivery-accepted"})
    monkeypatch.setattr(EmailService, "send_email", send)
    return send


def test_public_submission_is_committed_without_email_configuration(
    client, db_session, queue, mail, monkeypatch, caplog
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "contact_receiver_email", "")
    monkeypatch.setattr(settings, "resend_api_key", "")
    id = submit(client)
    row = db_session.get(ContactInquiry, UUID(id))
    assert row.message == BODY["message"] and row.email == BODY["email"]
    assert (
        row.status == "new"
        and row.opened_at is None
        and row.acknowledgement_status == "not_requested"
    )
    assert queue == []
    mail.assert_not_called()
    assert BODY["message"] not in caplog.text and BODY["email"] not in caplog.text
    assert client.get("/api/v1/contact/" + id).status_code == 404


def test_failed_persistence_never_reports_success_or_exposes_the_request(
    client, db_session, monkeypatch, caplog
):
    def fail(*args, **kwargs):
        raise RuntimeError("SECRET DATABASE DETAIL")

    monkeypatch.setattr(Session, "commit", fail)
    response = client.post("/api/v1/contact", json=BODY)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "CONTACT_UNAVAILABLE"
    assert "SECRET DATABASE DETAIL" not in response.text + caplog.text
    assert db_session.query(ContactInquiry).count() == 0


def test_only_superadmin_can_list_open_or_manage_an_inquiry(client, headers, queue):
    id = submit(client)
    for suffix, method in [
        ("", "GET"),
        ("/count", "GET"),
        ("/" + id, "GET"),
        ("/" + id + "/open", "POST"),
        ("/" + id, "PATCH"),
        ("/" + id + "/retry-acknowledgement", "POST"),
    ]:
        payload = {"status": "closed"} if method == "PATCH" else None
        assert (
            client.request(
                method, "/api/v1/admin/contact-requests" + suffix, json=payload
            ).status_code
            == 401
        )
        assert (
            client.request(
                method,
                "/api/v1/admin/contact-requests" + suffix,
                json=payload,
                headers=headers(0),
            ).status_code
            == 403
        )
    assert queue == []


def test_first_open_enqueues_once_and_read_close_reopen_never_repeat_email(
    client, headers, db_session, queue
):
    id = submit(client)
    admin = headers(2)
    root = "/api/v1/admin/contact-requests"
    listed = client.get(root, headers=admin).json()
    assert listed["new_count"] == 1 and listed["total"] == 1
    assert listed["items"][0]["id"] == id and "message" not in listed["items"][0]
    assert client.get(root + "/" + id, headers=admin).json()["status"] == "new"
    assert queue == []
    assert (
        client.patch(
            root + "/" + id, headers=admin, json={"status": "closed"}
        ).status_code
        == 409
    )
    opened = client.post(root + "/" + id + "/open", headers=admin)
    assert opened.status_code == 200, opened.text
    assert opened.json()["opened_at"] and opened.json()["opened_by"]
    assert (
        opened.json()["acknowledgement_status"] == "pending"
        and opened.json()["status"] == "opened"
    )
    assert queue == [id]
    assert client.post(root + "/" + id + "/open", headers=admin).status_code == 200
    assert (
        client.patch(
            root + "/" + id, headers=admin, json={"status": "closed"}
        ).status_code
        == 200
    )
    assert (
        client.post(root + "/" + id + "/open", headers=admin).json()["status"]
        == "closed"
    )
    assert (
        client.patch(
            root + "/" + id, headers=admin, json={"status": "opened"}
        ).status_code
        == 200
    )
    assert queue == [id]
    assert client.get(root + "/count", headers=admin).json()["new_count"] == 0


def test_acknowledgement_is_sent_to_visitor_only_after_open_and_job_is_idempotent(
    client, headers, db_session, queue, mail
):
    id = submit(client)
    assert asyncio.run(deliver_open_acknowledgement(db_session, UUID(id)))["processed"]
    mail.assert_not_called()
    client.post("/api/v1/admin/contact-requests/" + id + "/open", headers=headers(2))
    asyncio.run(deliver_open_acknowledgement(db_session, UUID(id)))
    assert mail.await_count == 1
    args = mail.call_args.args
    assert args[0] == BODY["email"] and "ouverte" in args[1]
    assert "prochainement" in args[3] and BODY["message"] not in args[3]
    assert mail.call_args.kwargs["idempotency_key"] == "radar-contact-open-" + id
    asyncio.run(deliver_open_acknowledgement(db_session, UUID(id)))
    assert mail.await_count == 1
    row = db_session.get(ContactInquiry, UUID(id))
    db_session.refresh(row)
    assert row.acknowledgement_status == "sent" and row.acknowledgement_sent_at


def test_failed_acknowledgement_is_visible_and_retry_is_explicit(
    client, headers, db_session, queue, mail
):
    id = submit(client)
    admin = headers(2)
    root = "/api/v1/admin/contact-requests/" + id
    client.post(root + "/open", headers=admin)
    mail.return_value = {"error": "SECRET PROVIDER RESPONSE"}
    asyncio.run(deliver_open_acknowledgement(db_session, UUID(id)))
    failed = client.get(root, headers=admin)
    assert failed.json()["acknowledgement_status"] == "failed"
    assert "SECRET PROVIDER RESPONSE" not in failed.text
    client.post(root + "/open", headers=admin)
    assert queue == [id]
    assert (
        client.post(root + "/retry-acknowledgement", headers=admin).status_code == 429
    )
    row = db_session.get(ContactInquiry, UUID(id))
    db_session.refresh(row)
    row.acknowledgement_queued_at = datetime.utcnow() - timedelta(minutes=2)
    db_session.commit()
    assert (
        client.post(root + "/retry-acknowledgement", headers=admin).status_code == 202
    )
    assert queue == [id, id]
    mail.return_value = {"id": "TEST-accepted-retry"}
    asyncio.run(deliver_open_acknowledgement(db_session, UUID(id)))
    assert client.get(root, headers=admin).json()["acknowledgement_status"] == "sent"
    assert (
        client.post(root + "/retry-acknowledgement", headers=admin).status_code == 409
    )


def test_broker_failure_preserves_the_opened_request(
    client, headers, db_session, queue, monkeypatch
):
    id = submit(client)

    def fail(*args):
        raise RuntimeError("SECRET BROKER ERROR")

    monkeypatch.setattr(
        "app.workers.contact_tasks.acknowledge_opened_request.delay", fail
    )
    result = client.post(
        "/api/v1/admin/contact-requests/" + id + "/open", headers=headers(2)
    )
    assert result.status_code == 200
    assert (
        result.json()["status"] == "opened"
        and result.json()["acknowledgement_status"] == "failed"
    )
    assert result.json()["acknowledgement_error"] == "QUEUE_UNAVAILABLE"
    assert "SECRET BROKER ERROR" not in result.text


def test_smtp_and_unconfigured_mail_are_honest(
    client, headers, db_session, queue, mail, monkeypatch
):
    id = submit(client)
    client.post("/api/v1/admin/contact-requests/" + id + "/open", headers=headers(2))
    from app.services.email_service import EmailService

    monkeypatch.setattr(EmailService, "is_configured", property(lambda self: False))
    sent = []
    monkeypatch.setattr(
        "app.services.contact_acknowledgement.smtp_send",
        lambda *args: sent.append(args),
    )
    asyncio.run(deliver_open_acknowledgement(db_session, UUID(id)))
    assert sent[0][0] == BODY["email"]
    mail.assert_not_called()
    other = submit(client)
    client.post("/api/v1/admin/contact-requests/" + other + "/open", headers=headers(2))
    monkeypatch.setattr(
        "app.services.contact_acknowledgement.availability", lambda: {"email": False}
    )
    asyncio.run(deliver_open_acknowledgement(db_session, UUID(other)))
    result = client.get("/api/v1/admin/contact-requests/" + other, headers=headers(2))
    assert result.json()["acknowledgement_status"] == "failed"
    assert result.json()["acknowledgement_error"] == "EMAIL_NOT_CONFIGURED"
