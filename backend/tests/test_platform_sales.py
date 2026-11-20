"""Radar platform quotes, PDF evidence and explicit administrative activation."""

from datetime import date, timedelta
from io import BytesIO
import json
from decimal import Decimal
import pytest
from pypdf import PdfReader
from app.db.models.legal_contract import LegalBundle
from app.db.models.platform_sales import PlatformQuote
from app.db.models.subscription_request import SubscriptionRequest
from legal_test_data import TEST_PUBLISHER


@pytest.fixture
def commercial(db_session, actors):
    ws = actors[1][0]
    ws.legal_name = "TEST Customer Agency"
    ws.legal_address = "10 TEST Street"
    ws.legal_city = "Paris"
    ws.legal_postal_code = "75001"
    bundle = LegalBundle(
        version="TEST-sales-v1",
        content_hash="a" * 64,
        publisher=TEST_PUBLISHER,
        documents={"sales_terms": "TEST terms"},
        review_reference="TEST legal review",
        published_by=actors[0][2].id,
    )
    db_session.add(bundle)
    order = SubscriptionRequest(
        workspace_id=ws.id,
        requested_by=actors[0][0].id,
        kind="plan",
        requested_value="business",
        status="pending",
    )
    db_session.add(order)
    db_session.commit()
    return ws, order


def create_quote(client, admin, ws, order):
    response = client.post(
        f"/api/v1/admin/clients/{ws.id}/quotes",
        headers=admin,
        json={
            "order_id": order.id,
            "valid_until": str(date.today() + timedelta(days=30)),
            "notes": "TEST annual service and verified payment conditions",
            "lines": [
                {
                    "description": "TEST service",
                    "quantity": "2",
                    "unit_price": "120.50",
                    "vat_rate": "20",
                },
                {
                    "description": "TEST setup",
                    "quantity": "1",
                    "unit_price": "30.25",
                    "vat_rate": "10",
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, admin, ws, order, pdf, quote_id=None):
    response = client.post(
        f"/api/v1/admin/clients/{ws.id}/contracts/external",
        headers=admin,
        data={
            "data": json.dumps(
                {
                    "order_id": order.id,
                    "quote_id": quote_id,
                    "reference": "TEST-signed-contract",
                    "signer": "TEST Customer Signer",
                    "signed_on": str(date.today()),
                }
            )
        },
        files={"file": ("signed-test.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_quote_totals_and_real_downloadable_pdf(
    client, headers, commercial, actors, db_session
):
    ws, order = commercial
    admin = headers(2)
    quote = create_quote(client, admin, ws, order)
    assert Decimal(quote["total_ht"]) == Decimal("271.25")
    assert Decimal(quote["total_tax"]) == Decimal("51.23")
    assert Decimal(quote["total_ttc"]) == Decimal("322.48")
    pdf = client.get(
        f'/api/v1/admin/clients/{ws.id}/quotes/{quote["id"]}/pdf', headers=admin
    )
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert pdf.headers["content-type"] == "application/pdf"
    assert quote["reference"] + ".pdf" in pdf.headers["content-disposition"]
    text = " ".join(
        page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages
    )
    assert (
        "TEST Customer Agency" in text and "322,48 EUR" in text and "Brouillon" in text
    )
    issued = client.post(
        f'/api/v1/admin/clients/{ws.id}/quotes/{quote["id"]}/issue', headers=admin
    )
    assert issued.status_code == 200, issued.text
    assert (
        issued.json()["status"] == "issued" and len(issued.json()["content_hash"]) == 64
    )
    assert (
        client.get(
            f'/api/v1/admin/clients/{actors[1][1].id}/quotes/{quote["id"]}/pdf',
            headers=admin,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f'/api/v1/admin/clients/{ws.id}/quotes/{quote["id"]}/pdf',
            headers=headers(0),
        ).status_code
        == 403
    )


def test_external_contract_requires_review_before_order_activation(
    client, headers, commercial, actors, db_session
):
    ws, order = commercial
    admin = headers(2)
    quote = create_quote(client, admin, ws, order)
    assert (
        client.post(
            f'/api/v1/admin/clients/{ws.id}/quotes/{quote["id"]}/issue', headers=admin
        ).status_code
        == 200
    )
    pdf = client.get(
        f'/api/v1/admin/clients/{ws.id}/quotes/{quote["id"]}/pdf', headers=admin
    ).content
    contract = upload(client, admin, ws, order, pdf, quote["id"])
    body = {
        "approve": True,
        "external_contract_id": contract["id"],
        "authorization_reference": "TEST administrative authorization",
    }
    assert (
        client.post(
            f"/api/v1/subscription/admin/requests/{order.id}/decision",
            headers=admin,
            json=body,
        ).status_code
        == 409
    )
    review = f'/api/v1/admin/clients/{ws.id}/contracts/external/{contract["id"]}/review'
    assert (
        client.post(
            review,
            headers=admin,
            json={
                "approved": True,
                "reference": "TEST manual review",
                "document_checked": False,
            },
        ).status_code
        == 422
    )
    reviewed = client.post(
        review,
        headers=admin,
        json={
            "approved": True,
            "reference": "TEST manual review",
            "document_checked": True,
        },
    )
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "validated"
    result = client.post(
        f"/api/v1/subscription/admin/requests/{order.id}/decision",
        headers=admin,
        json=body,
    )
    assert result.status_code == 200, result.text
    assert (
        result.json()["rights_activated"] is True
        and result.json()["payment_confirmed"] is False
    )
    assert result.json()["subscription"]["plan"] == "business"
    assert (
        client.post(
            f"/api/v1/subscription/admin/requests/{order.id}/decision",
            headers=admin,
            json=body,
        ).status_code
        == 409
    )
    download = client.get(
        f'/api/v1/admin/clients/{ws.id}/contracts/external/{contract["id"]}/pdf',
        headers=admin,
    )
    assert (
        download.content == pdf
        and "attachment" in download.headers["content-disposition"]
    )


def test_contract_cannot_authorize_another_company_or_order(
    client, headers, commercial, actors, db_session
):
    ws, order = commercial
    admin = headers(2)
    q = create_quote(client, admin, ws, order)
    pdf = client.get(
        f'/api/v1/admin/clients/{ws.id}/quotes/{q["id"]}/pdf', headers=admin
    ).content
    contract = upload(client, admin, ws, order, pdf)
    client.post(
        f'/api/v1/admin/clients/{ws.id}/contracts/external/{contract["id"]}/review',
        headers=admin,
        json={
            "approved": True,
            "reference": "TEST checked document",
            "document_checked": True,
        },
    )
    other = SubscriptionRequest(
        workspace_id=actors[1][1].id,
        requested_by=actors[0][1].id,
        kind="plan",
        requested_value="business",
        status="pending",
    )
    same_company = SubscriptionRequest(
        workspace_id=ws.id,
        requested_by=actors[0][0].id,
        kind="plan",
        requested_value="premium",
        status="pending",
    )
    db_session.add_all([other, same_company])
    db_session.commit()
    for target in [other, same_company]:
        assert (
            client.post(
                f"/api/v1/subscription/admin/requests/{target.id}/decision",
                headers=admin,
                json={
                    "approve": True,
                    "external_contract_id": contract["id"],
                    "authorization_reference": "TEST mismatch",
                },
            ).status_code
            == 409
        )


def test_addon_approval_is_commercial_only_not_paid_feature_grant(
    client, headers, commercial, db_session
):
    ws, order = commercial
    order.kind = "addon"
    order.requested_value = "TEST custom export"
    db_session.commit()
    admin = headers(2)
    q = create_quote(client, admin, ws, order)
    pdf = client.get(
        f'/api/v1/admin/clients/{ws.id}/quotes/{q["id"]}/pdf', headers=admin
    ).content
    contract = upload(client, admin, ws, order, pdf)
    client.post(
        f'/api/v1/admin/clients/{ws.id}/contracts/external/{contract["id"]}/review',
        headers=admin,
        json={
            "approved": True,
            "reference": "TEST reviewed addon",
            "document_checked": True,
        },
    )
    result = client.post(
        f"/api/v1/subscription/admin/requests/{order.id}/decision",
        headers=admin,
        json={
            "approve": True,
            "external_contract_id": contract["id"],
            "authorization_reference": "TEST addon agreement",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "commercial_approved"
    assert (
        result.json()["rights_activated"] is False
        and result.json()["payment_confirmed"] is False
    )
    assert result.json()["subscription"]["plan"] == "core"


def test_invalid_or_encrypted_pdf_is_not_accepted(client, headers, commercial):
    ws, order = commercial
    admin = headers(2)
    for invalid in [b"NOT A PDF", b"%PDF-1.4\nnot valid\n%%EOF"]:
        result = client.post(
            f"/api/v1/admin/clients/{ws.id}/contracts/external",
            headers=admin,
            data={
                "data": json.dumps(
                    {
                        "order_id": order.id,
                        "reference": "TEST invalid",
                        "signer": "TEST signer",
                        "signed_on": str(date.today()),
                    }
                )
            },
            files={"file": ("bad.pdf", invalid, "application/pdf")},
        )
        assert result.status_code == 422


def test_quotes_need_a_real_publisher_and_never_invent_prices(client, headers, actors):
    ws = actors[1][0]
    body = {
        "valid_until": str(date.today() + timedelta(days=5)),
        "lines": [
            {
                "description": "TEST offer",
                "quantity": "1",
                "unit_price": "100",
                "vat_rate": "20",
            }
        ],
    }
    assert (
        client.post(
            f"/api/v1/admin/clients/{ws.id}/quotes", headers=headers(2), json=body
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/admin/clients/{ws.id}/quotes", headers=headers(0), json=body
        ).status_code
        == 403
    )
