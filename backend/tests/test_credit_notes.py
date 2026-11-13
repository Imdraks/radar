"""Full-credit documents preserve historical amounts, references, payments and tenant boundaries."""

from decimal import Decimal
from test_commercial_hardening import invoice
from app.db.models.billing import Invoice


def test_full_credit_is_immutable_idempotent_and_does_not_refund(
    client, headers, invoice, actors, db_session
):
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    body = {
        "reason": "TEST correction intégrale de la prestation",
        "idempotency_key": "TEST-credit-idempotency-01",
    }
    assert (
        client.post(path + "/credit-notes", headers=headers(), json=body).status_code
        == 409
    )
    assert client.post(path + "/send", headers=headers()).status_code == 200
    assert (
        client.post(
            path + "/payment", headers=headers(), json={"amount_paid": "20"}
        ).status_code
        == 200
    )
    original = client.get(path, headers=headers()).json()
    actors[1][0].legal_name = "Changed issuer after original emission"
    db_session.commit()
    response = client.post(path + "/credit-notes", headers=headers(), json=body)
    assert response.status_code == 201, response.text
    note = response.json()
    assert note["reference"].startswith("AVO-")
    assert Decimal(str(note["total"])) == Decimal("120")
    assert note["snapshot"]["original_reference"] == original["reference"]
    assert note["snapshot"]["original_issue_date"] == original["issue_date"]
    assert note["snapshot"]["parties"]["emitter"]["legal_name"] == "TEST — Agency"
    assert note["snapshot"]["amount_paid_at_issue"] == "20.00"
    replay = client.post(path + "/credit-notes", headers=headers(), json=body)
    assert replay.status_code == 201 and replay.json()["id"] == note["id"]
    assert (
        client.post(
            path + "/credit-notes",
            headers=headers(),
            json={**body, "idempotency_key": "TEST-other-key"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/credit-notes",
            headers=headers(),
            json={**body, "reason": "Changed correction reason"},
        ).status_code
        == 409
    )
    current = client.get(path, headers=headers()).json()
    assert (
        current["reference"] == original["reference"]
        and current["status"] == original["status"]
    )
    assert (
        Decimal(str(current["amount_paid"])) == Decimal("20") and current["credited_at"]
    )
    assert (
        client.post(
            path + "/payment", headers=headers(), json={"amount_paid": "40"}
        ).status_code
        == 409
    )
    assert client.post(path + "/mark-paid", headers=headers()).status_code == 409
    assert client.post(path + "/cancel", headers=headers()).status_code == 409
    pdf = client.get(
        f"/api/v1/billing/credit-notes/{note['id']}/pdf", headers=headers()
    )
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    actors[1][1].plan = "business"
    db_session.commit()
    assert (
        client.get(
            f"/api/v1/billing/credit-notes/{note['id']}/pdf", headers=headers(1)
        ).status_code
        == 404
    )
    assert (
        client.post(path + "/credit-notes", headers=headers(3), json=body).status_code
        == 403
    )
    dashboard = client.get("/api/v1/billing/dashboard", headers=headers()).json()
    assert Decimal(str(dashboard["total_pending"])) == 0
    assert Decimal(str(dashboard["total_invoices_amount"])) == 0
    assert Decimal(str(dashboard["total_paid"])) == 20
    assert Decimal(str(dashboard["payments_on_credited_invoices"])) == 20
    assert dashboard["credited_invoices_count"] == 1
    assert len(client.get(path + "/credit-notes", headers=headers()).json()) == 1


def test_exchange_is_frozen_precise_and_never_claims_transmission(
    client, headers, invoice, actors, db_session
):
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    assert client.get(path + "/exchange", headers=headers()).status_code == 409
    readiness = client.get(path + "/electronic-invoicing", headers=headers()).json()
    assert readiness["ready_for_transmission"] is False
    assert client.post(path + "/send", headers=headers()).status_code == 200
    actors[1][0].legal_name = "Later changed company name"
    db_session.commit()
    r = client.get(path + "/exchange", headers=headers())
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    data = r.json()
    assert (
        data["transmission_status"] == "not_transmitted"
        and data["regulated_format"] is False
    )
    assert data["issuer"]["legal_name"] == "TEST — Agency"
    assert data["amounts"]["total"] == "120.00"
    assert len(data["sha256"]) == 64
    assert "payment_info" not in data["issuer"]
    assert client.get(path + "/exchange", headers=headers(1)).status_code == 403


def test_billing_totals_do_not_treat_drafts_as_issued_revenue(client, headers, invoice):
    result = client.get("/api/v1/billing/dashboard", headers=headers())
    assert result.status_code == 200
    assert Decimal(str(result.json()["total_invoices_amount"])) == 0
    assert result.json()["invoices_draft"] == 1
