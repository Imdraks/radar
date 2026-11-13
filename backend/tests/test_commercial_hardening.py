"""Regression tests from the commercial readiness audit; no external requests."""

from datetime import datetime
import json
import subprocess
from pathlib import Path
import pytest
from sqlalchemy import text
from app.db.models.billing import Invoice, InvoiceStatus
from test_billing import ready_to_issue


@pytest.fixture
def invoice(client, db_session, actors, headers):
    actors[1][0].plan = "business"
    db_session.commit()
    r = client.post(
        "/api/v1/billing/invoices",
        headers=headers(),
        json={
            "title": "TEST audited invoice",
            "items": [{"description": "Service", "quantity": "1", "unit_price": "100"}],
        },
    )
    assert r.status_code == 200, r.text
    i = r.json()
    ready_to_issue(db_session, actors[1][0], i["id"])
    return i


def test_sent_invoice_is_frozen_and_cannot_return_to_draft(
    client, db_session, actors, headers, invoice
):
    url = f"/api/v1/billing/invoices/{invoice['id']}"
    response = client.post(url + "/send", headers=headers())
    assert response.status_code == 200, response.text
    response = client.post(url + "/send", headers=headers())
    assert response.status_code == 200, response.text
    assert (
        client.patch(url, headers=headers(), json={"title": "Alteration"}).status_code
        == 409
    )
    assert (
        client.patch(url, headers=headers(), json={"status": "DRAFT"}).status_code
        == 409
    )
    assert (
        client.post(
            url + "/items",
            headers=headers(),
            json={"description": "Alteration", "unit_price": "500"},
        ).status_code
        == 409
    )
    assert (
        client.delete(
            url + f"/items/{invoice['items'][0]['id']}", headers=headers()
        ).status_code
        == 409
    )
    assert client.delete(url, headers=headers()).status_code == 400
    assert client.post(url + "/cancel", headers=headers()).status_code == 409
    assert client.post(
        url + "/payment", headers=headers(1), json={"amount_paid": "120"}
    ).status_code in (403, 404)
    saved = db_session.get(Invoice, invoice["id"])
    db_session.refresh(saved)
    assert saved.issued_snapshot["emitter"]["legal_name"] == "TEST — Agency"
    actors[1][0].legal_name = "Later changed"
    db_session.commit()
    assert client.get(url + "/pdf", headers=headers()).status_code == 200
    db_session.refresh(saved)
    assert saved.issued_snapshot["emitter"]["legal_name"] == "TEST — Agency"


@pytest.mark.parametrize(
    "action,payload", [("payment", {"amount_paid": "120"}), ("mark-paid", None)]
)
def test_draft_and_cancelled_invoices_cannot_receive_payments(
    client, headers, invoice, action, payload
):
    url = f"/api/v1/billing/invoices/{invoice['id']}"
    assert (
        client.post(url + "/" + action, headers=headers(), json=payload).status_code
        == 409
    )
    assert client.post(url + "/cancel", headers=headers()).status_code == 200
    assert (
        client.post(url + "/" + action, headers=headers(), json=payload).status_code
        == 409
    )


def test_partial_payments_are_monotonic_and_audited(
    client, db_session, headers, invoice
):
    url = f"/api/v1/billing/invoices/{invoice['id']}"
    response = client.post(url + "/send", headers=headers())
    assert response.status_code == 200, response.text
    assert (
        client.post(
            url + "/payment", headers=headers(), json={"amount_paid": "40"}
        ).json()["status"]
        == "PARTIAL"
    )
    assert (
        client.post(
            url + "/payment",
            headers=headers(),
            json={"amount_paid": "80", "expected_amount_paid": "0"},
        ).status_code
        == 409
    )
    for amount in ["0", "20", "121"]:
        assert (
            client.post(
                url + "/payment", headers=headers(), json={"amount_paid": amount}
            ).status_code
            == 422
        )
    assert (
        client.post(
            url + "/payment", headers=headers(), json={"amount_paid": "120"}
        ).json()["status"]
        == "PAID"
    )
    saved = db_session.get(Invoice, invoice["id"])
    db_session.refresh(saved)
    assert [row["event"] for row in saved.audit_log].count("payment_declared") == 2


def test_issuance_requires_identity_client_and_valid_totals(
    client, db_session, actors, headers, invoice
):
    url = f"/api/v1/billing/invoices/{invoice['id']}"
    actors[1][0].siret = None
    db_session.commit()
    assert client.post(url + "/send", headers=headers()).status_code == 422
    for change in [{"tax_rate": "-1"}, {"discount_percent": "101"}, {"title": None}]:
        assert client.patch(url, headers=headers(), json=change).status_code == 422


def test_legacy_issued_invoice_remains_frozen_without_fabricated_snapshot(
    client, db_session, headers, invoice
):
    saved = db_session.get(Invoice, invoice["id"])
    saved.status = InvoiceStatus.SENT
    db_session.commit()
    url = f"/api/v1/billing/invoices/{invoice['id']}"
    assert (
        client.patch(url, headers=headers(), json={"status": "DRAFT"}).status_code
        == 409
    )
    assert client.get(url + "/pdf", headers=headers()).status_code == 409


def test_first_administrator_requires_operator_secret(client, monkeypatch):
    from app.api.auth import settings

    body = {
        "email": "audit-owner@example.com",
        "full_name": "TEST operator",
        "password": "Disposable-Test-123!",
    }
    assert client.post("/api/v1/auth/setup", json=body).status_code == 403
    monkeypatch.setattr(settings, "bootstrap_token", "test-bootstrap-token")
    assert client.get("/api/v1/auth/setup-check").json()["setup_enabled"] is True
    assert (
        client.post(
            "/api/v1/auth/setup",
            json=body,
            headers={"X-Radar-Bootstrap-Token": "wrong"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/setup",
            json=body,
            headers={"X-Radar-Bootstrap-Token": "test-bootstrap-token"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/setup",
            json=body,
            headers={"X-Radar-Bootstrap-Token": "test-bootstrap-token"},
        ).status_code
        == 403
    )


def test_query_token_no_longer_authenticates_websocket(client, actors):
    from app.core.security import create_access_token
    from starlette.websockets import WebSocketDisconnect

    token = create_access_token({"sub": str(actors[0][0].id)})
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/notifications?token={token}"):
            pass


def test_deploy_propagates_background_failure():
    root = Path(__file__).resolve().parents[2]
    script = 'source "$1"; (exit 23) & spinner $! TEST'
    r = subprocess.run(
        ["bash", "-c", script, "audit", str(root / "deploy.sh")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 23 and "✓" not in r.stdout


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({}, None),
        ({"deezer_fans": 500}, "deezer"),
        ({"monthly_listeners": 1000}, "spotify"),
    ],
)
def test_artist_history_records_only_observed_providers(
    monkeypatch, db_session, actors, payload, expected
):
    from app.db.models.discovery import (
        DiscoveryArtist,
        DiscoverySnapshot,
        DiscoveryEnrichmentJob,
    )
    from app.db.models.artist_snapshot import ArtistSnapshot
    from app.workers import discovery_pipeline as pipeline

    artist = DiscoveryArtist(
        workspace_id=actors[1][0].id,
        canonical_name="TEST provenance",
        normalized_name="test provenance",
    )
    db_session.add(artist)
    db_session.flush()
    job = DiscoveryEnrichmentJob(
        workspace_id=actors[1][0].id,
        artist_id=artist.id,
        input_type="NAME",
        input_value="TEST provenance",
    )
    db_session.add(job)
    db_session.add(
        DiscoverySnapshot(
            artist_id=artist.id,
            source="SPOTIFY",
            status="OK",
            raw_payload=payload,
            ttl_expires_at=datetime(2099, 1, 1),
        )
    )
    db_session.flush()
    monkeypatch.setattr(
        pipeline,
        "step_social",
        lambda *args: {
            k: {"value": None, "status": "unavailable"}
            for k in ["instagram", "tiktok", "youtube"]
        },
    )
    pipeline.step_compute(db_session, job, False, bool(payload))
    snapshot = db_session.query(ArtistSnapshot).one()
    assert snapshot.sources_used == expected
    assert snapshot.source_quality_score is None


@pytest.mark.asyncio
async def test_legacy_scan_does_not_shortcut_to_static_artist_numbers(monkeypatch):
    from unittest.mock import AsyncMock
    from app.intelligence import web_artist_scanner as module

    scanner = module.WebArtistScanner()
    scanner.session = object()  # No HTTP session is opened in this test.

    def forbidden_catalog(name):
        raise AssertionError("Static catalog must not enter a live scan")

    monkeypatch.setattr(module, "get_known_artist", forbidden_catalog)
    names = [
        "viberate",
        "wikipedia",
        "spotify_web",
        "youtube",
        "discogs",
        "songkick",
        "bandsintown",
        "ticketmaster",
        "fnac_spectacles",
        "google",
    ]
    for name in names:
        monkeypatch.setattr(scanner, "_scan_" + name, AsyncMock(return_value=None))
    result = await scanner.scan_artist("SCH", force_refresh=False)
    assert result.spotify_monthly_listeners == 0
    assert result.sources_scanned == []
    assert "Base de données artistes FR" not in result.sources_scanned


def test_vat_exempt_issuer_cannot_issue_taxed_invoice(
    client, db_session, actors, headers, invoice
):
    actors[1][0].tva_franchise = True
    db_session.commit()
    url = f"/api/v1/billing/invoices/{invoice['id']}"
    assert client.post(url + "/send", headers=headers()).status_code == 422
    updated = client.patch(url, headers=headers(), json={"tax_rate": "0"})
    assert updated.status_code == 200
    assert updated.json()["total"] == "100.00"
    assert client.post(url + "/send", headers=headers()).status_code == 200


def test_draft_invoice_numbers_do_not_create_gaps_in_issued_series(
    client, headers, invoice, db_session, actors
):
    first = client.post(
        "/api/v1/billing/invoices",
        headers=headers(),
        json={"title": "TEST removed draft"},
    )
    assert first.status_code == 200
    assert first.json()["reference"].startswith("BROUILLON-")
    assert (
        client.delete(
            f"/api/v1/billing/invoices/{first.json()['id']}", headers=headers()
        ).status_code
        == 200
    )
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    assert invoice["reference"].startswith("BROUILLON-")
    assert client.post(path + "/send", headers=headers()).status_code == 200
    emitted = client.get(path, headers=headers()).json()
    assert emitted["reference"].endswith("-0001")
    assert emitted["reference"].startswith("FAC-")


def test_issue_requires_legal_information_without_consuming_a_final_number(
    client, headers, invoice
):
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    assert (
        client.patch(path, headers=headers(), json={"legal_details": None}).status_code
        == 200
    )
    response = client.post(path + "/send", headers=headers())
    assert response.status_code == 422
    assert (
        client.get(path, headers=headers()).json()["reference"].startswith("BROUILLON-")
    )


def test_late_collection_fee_is_never_asserted_against_a_consumer(
    client, headers, invoice
):
    from app.services.invoice_lifecycle import invoice_legal_text
    from types import SimpleNamespace

    details = {
        "service_date": "2026-11-13",
        "customer_type": "consumer",
        "early_payment_terms": "Sans escompte",
    }
    value = invoice_legal_text(SimpleNamespace(legal_details=details))
    assert "40 euros" not in value
    details = {
        **details,
        "customer_type": "professional",
        "late_payment_basis": "ecb_plus_10",
    }
    assert "40 euros" in invoice_legal_text(SimpleNamespace(legal_details=details))


@pytest.mark.parametrize("registered_city", [None, "Lyon"])
def test_invoice_pdf_only_uses_declared_rcs(
    client, headers, invoice, db_session, actors, monkeypatch, registered_city
):
    from reportlab.platypus import Paragraph as OriginalParagraph
    import reportlab.platypus

    rendered = []

    def paragraph(value, *args, **kwargs):
        rendered.append(str(value))
        return OriginalParagraph(value, *args, **kwargs)

    monkeypatch.setattr(reportlab.platypus, "Paragraph", paragraph)
    actors[1][0].rcs_city = registered_city
    db_session.commit()
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    assert client.post(path + "/send", headers=headers()).status_code == 200
    assert client.get(path + "/pdf", headers=headers()).status_code == 200
    text = "\n".join(rendered)
    assert "RCS Paris" not in text
    if registered_city:
        assert "RCS Lyon" in text


def test_issuance_date_is_actual_local_date_and_reference_uses_its_year(
    client, headers, invoice, db_session, actors, monkeypatch
):
    from datetime import datetime as RealDate
    from app.services import invoice_lifecycle as lifecycle

    class FrozenDate(RealDate):
        @classmethod
        def utcnow(cls):
            return RealDate(2026, 12, 31, 23, 30)

    monkeypatch.setattr(lifecycle, "datetime", FrozenDate)
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    assert (
        client.patch(
            path,
            headers=headers(),
            json={"issue_date": "2026-01-01", "due_date": "2027-01-31"},
        ).status_code
        == 200
    )
    assert client.post(path + "/send", headers=headers()).status_code == 200
    result = client.get(path, headers=headers()).json()
    assert result["issue_date"] == "2027-01-01"
    assert result["reference"].startswith("FAC-2027-")


def test_zero_vat_without_franchise_requires_an_explicit_legal_mention(
    client, headers, invoice
):
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    assert (
        client.patch(path, headers=headers(), json={"tax_rate": "0"}).status_code == 200
    )
    assert client.post(path + "/send", headers=headers()).status_code == 422
    details = {
        "service_date": "2026-11-13",
        "customer_type": "professional",
        "early_payment_terms": "Aucun escompte",
        "late_payment_basis": "ecb_plus_10",
        "vat_exemption_mention": "TEST — motif légal à vérifier dans la recette",
    }
    assert (
        client.patch(
            path, headers=headers(), json={"legal_details": details}
        ).status_code
        == 200
    )
    assert client.post(path + "/send", headers=headers()).status_code == 200


def test_issuer_legal_form_and_company_capital_must_be_declared(
    client, headers, invoice, db_session, actors
):
    ws = actors[1][0]
    path = f"/api/v1/billing/invoices/{invoice['id']}"
    ws.forme_juridique = None
    db_session.commit()
    assert client.post(path + "/send", headers=headers()).status_code == 422
    response = client.patch("/api/v1/billing/emitter", headers=headers(), json={"forme_juridique": "SAS", "capital_social": ""})
    assert response.status_code == 200
    assert response.json()["forme_juridique"] == "SAS"
    assert client.post(path + "/send", headers=headers()).status_code == 422
    assert client.patch("/api/v1/billing/emitter", headers=headers(), json={"capital_social": "1000 EUR"}).status_code == 200
    assert client.post(path + "/send", headers=headers()).status_code == 200
