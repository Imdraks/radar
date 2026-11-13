"""Issue a full credit using original fiscal amounts, not recalculated live company data."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from html import escape
from io import BytesIO
from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from decimal import Decimal
from app.db.models.billing import InvoiceStatus
from app.db.models.credit_note import CreditNote
from app.db.models.workspace import Workspace
from app.services.invoice_lifecycle import locked_invoice, audit
from app.services.billing_numbers import next_reference


def issue_full_credit(db: Session, workspace_id, invoice_id, user_id, reason, key):
    invoice = locked_invoice(db, invoice_id, workspace_id)
    workspace = db.query(Workspace).filter_by(id=workspace_id).with_for_update().one()
    existing = (
        db.query(CreditNote)
        .filter_by(workspace_id=workspace_id, idempotency_key=key)
        .first()
    )
    if existing:
        if existing.invoice_id != invoice_id or existing.reason != reason:
            raise HTTPException(409, "Cette clé a déjà servi pour une autre opération")
        return existing
    if (
        invoice.credited_at
        or db.query(CreditNote).filter_by(invoice_id=invoice_id).first()
    ):
        raise HTTPException(409, "Un avoir total existe déjà pour cette facture")
    if (
        invoice.status
        not in {
            InvoiceStatus.SENT,
            InvoiceStatus.PARTIAL,
            InvoiceStatus.PAID,
            InvoiceStatus.OVERDUE,
        }
        or not invoice.issued_at
    ):
        raise HTTPException(409, "Un avoir nécessite une facture réellement émise")
    if not invoice.issued_snapshot or not invoice.legal_details:
        raise HTTPException(
            409,
            "Facture historique : rapprocher l’original et les mentions avant une correction assistée",
        )
    now = datetime.utcnow()
    zone = invoice.issued_snapshot.get("billing_timezone", "Europe/Paris")
    issued_date = now.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(zone)).date()
    snapshot = {
        "version": 1,
        "original_reference": invoice.reference,
        "original_issue_date": invoice.issue_date.isoformat(),
        "parties": invoice.issued_snapshot,
        "legal_details": invoice.legal_details,
        "title": invoice.title,
        "tax_rate": str(invoice.tax_rate),
        "discount_percent": str(invoice.discount_percent),
        "discount_amount": str(invoice.discount_amount),
        "items": [
            {
                key: getattr(item, key)
                for key in (
                    "description",
                    "quantity",
                    "unit",
                    "unit_price",
                    "line_total",
                    "position",
                )
            }
            for item in invoice.items
        ],
        "amount_paid_at_issue": str(invoice.amount_paid or 0),
    }
    snapshot = jsonable_encoder(snapshot, custom_encoder={Decimal: str})
    note = CreditNote(
        workspace_id=workspace_id,
        invoice_id=invoice.id,
        reference=next_reference(db, workspace_id, "AVO", document_date=issued_date),
        idempotency_key=key,
        issue_date=issued_date,
        reason=reason,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        snapshot=snapshot,
        created_by=user_id,
        created_at=now,
    )
    db.add(note)
    invoice.credited_at = now
    db.flush()
    audit(
        invoice,
        "full_credit_issued",
        user_id,
        {
            "credit_note_id": note.id,
            "reference": note.reference,
            "total": str(note.total),
            "refund_executed": False,
        },
    )
    return note


def credit_pdf(note):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    output = BytesIO()
    story = []

    def paragraph(text, style="Normal"):
        return Paragraph(escape(str(text)), styles[style])

    snapshot = note.snapshot
    story += [
        paragraph("AVOIR TOTAL — " + note.reference, "Title"),
        paragraph("Date d’émission : " + note.issue_date.isoformat()),
        paragraph(
            "Facture d’origine : "
            + snapshot["original_reference"]
            + " du "
            + snapshot["original_issue_date"]
        ),
        Spacer(1, 12),
    ]
    emitter = snapshot["parties"]["emitter"]
    customer = snapshot["parties"]["client"]
    story.append(paragraph("Émetteur", "Heading2"))
    for key in (
        "legal_name",
        "forme_juridique",
        "capital_social",
        "legal_address",
        "legal_postal_code",
        "legal_city",
        "legal_country",
        "siret",
        "vat_number",
        "legal_email",
        "legal_phone",
    ):
        labels = {
            "legal_name": "Nom",
            "forme_juridique": "Forme juridique",
            "capital_social": "Capital social",
            "legal_address": "Adresse",
            "legal_postal_code": "Code postal",
            "legal_city": "Ville",
            "legal_country": "Pays",
            "siret": "SIRET",
            "vat_number": "TVA",
            "legal_email": "Email",
            "legal_phone": "Téléphone",
        }
        if emitter.get(key):
            story.append(paragraph(labels[key] + " : " + str(emitter[key])))
    if emitter.get("rcs_city"):
        story.append(
            paragraph(
                "RCS " + emitter["rcs_city"] + " " + str(emitter.get("siret") or "")[:9]
            )
        )
    story.append(paragraph("Client", "Heading2"))
    for key in (
        "name",
        "company_name",
        "address_line1",
        "address_line2",
        "postal_code",
        "city",
        "country",
        "siret",
        "vat_number",
    ):
        labels = {
            "name": "Nom",
            "company_name": "Société",
            "address_line1": "Adresse",
            "address_line2": "Complément",
            "postal_code": "Code postal",
            "city": "Ville",
            "country": "Pays",
            "siret": "SIREN / SIRET",
            "vat_number": "TVA",
        }
        if customer.get(key):
            story.append(paragraph(labels[key] + " : " + str(customer[key])))
    story += [paragraph("Motif : " + note.reason), Spacer(1, 12)]
    rows = [
        [
            paragraph("Prestation"),
            paragraph("Qté"),
            paragraph("PU HT"),
            paragraph("Total HT"),
        ]
    ]
    for item in snapshot["items"]:
        rows.append(
            [
                paragraph(item["description"]),
                paragraph(str(item["quantity"]) + " " + str(item.get("unit") or "")),
                paragraph(item["unit_price"]),
                paragraph(item["line_total"]),
            ]
        )
    table = Table(rows, colWidths=[260, 60, 80, 80], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f3ff")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [
        table,
        Spacer(1, 12),
        paragraph("Remise HT d’origine : " + snapshot["discount_amount"] + " EUR"),
        paragraph("Base HT avant remise : " + str(note.subtotal) + " EUR"),
        paragraph(
            "Total avoir HT après remise : "
            + str(note.subtotal - Decimal(snapshot["discount_amount"]))
            + " EUR"
        ),
        paragraph(
            "TVA " + snapshot["tax_rate"] + " % : " + str(note.tax_amount) + " EUR"
        ),
        paragraph("Montant de l’avoir TTC : " + str(note.total) + " EUR", "Heading2"),
    ]
    legal = snapshot["legal_details"]
    if emitter.get("tva_franchise"):
        story.append(paragraph("TVA non applicable, article 293 B du CGI."))
    if legal.get("vat_exemption_mention"):
        story.append(paragraph(legal["vat_exemption_mention"]))
    story += [
        paragraph(
            "Date de prestation d’origine : " + str(legal.get("service_date") or "")
        ),
        paragraph(
            "Cet avoir corrige intégralement la facture référencée. Les paiements historiques restent conservés. Un éventuel remboursement ou réemploi doit être traité et rapproché séparément ; aucun remboursement bancaire n’a été exécuté par Radar."
        ),
    ]
    SimpleDocTemplate(output).build(story)
    return output.getvalue()
