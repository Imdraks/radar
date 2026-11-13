"""Invoice transitions and frozen parties. Manual payments are declarations, never bank confirmations."""

from datetime import datetime, date, timezone
from decimal import Decimal
from types import SimpleNamespace
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from app.services.billing_numbers import next_reference
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.billing import Invoice, InvoiceStatus, BillingClient
from app.db.models.workspace import Workspace

EMITTER_FIELDS = (
    "name",
    "legal_name",
    "billing_email",
    "legal_address",
    "legal_city",
    "legal_postal_code",
    "legal_country",
    "legal_phone",
    "legal_email",
    "siret",
    "vat_number",
    "forme_juridique",
    "capital_social",
    "rcs_city",
    "tva_franchise",
    "payment_info",
    "logo_drive_file_id",
)
CLIENT_FIELDS = (
    "name",
    "company_name",
    "email",
    "phone",
    "address_line1",
    "address_line2",
    "city",
    "postal_code",
    "country",
    "siret",
    "vat_number",
    "contact_first_name",
    "contact_last_name",
    "contact_email",
    "contact_phone",
    "contact_role",
)
PAYABLE = {InvoiceStatus.SENT, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE}


def audit(invoice, event, user_id, details=None):
    invoice.audit_log = [
        *(invoice.audit_log or []),
        {
            "event": event,
            "at": datetime.utcnow().isoformat(),
            "by": user_id,
            "details": details or {},
        },
    ]


def locked_invoice(db, invoice_id, workspace_id):
    invoice = (
        db.query(Invoice)
        .filter_by(id=invoice_id, workspace_id=workspace_id)
        .with_for_update()
        .first()
    )
    if invoice is None:
        raise HTTPException(404, "Facture non trouvée")
    return invoice


def require_draft(invoice):
    if invoice.status != InvoiceStatus.DRAFT or invoice.issued_at or invoice.sent_at:
        raise HTTPException(
            409,
            "Une facture émise est figée. Une correction nécessite un document rectificatif adapté.",
        )


def issue(db, invoice, user_id, email=None):
    if invoice.status == InvoiceStatus.SENT:
        return  # Idempotent; never recreate the original snapshot.
    require_draft(invoice)
    workspace = (
        db.query(Workspace).filter_by(id=invoice.workspace_id).with_for_update().first()
    )
    client = (
        db.query(BillingClient)
        .filter_by(id=invoice.client_id, workspace_id=invoice.workspace_id)
        .first()
        if invoice.client_id
        else None
    )
    required = (
        "legal_name",
        "legal_address",
        "legal_city",
        "legal_postal_code",
        "legal_country",
    )
    missing = [field for field in required if not getattr(workspace, field, None)]
    if workspace and (workspace.legal_country or "").lower() in {"france", "fr"}:
        if not re.fullmatch(r"\d{14}", workspace.siret or ""):
            missing.append("siret (14 chiffres)")
        if not str(workspace.forme_juridique or "").strip():
            missing.append("forme juridique déclarée de l’émetteur")
        declared_form = str(workspace.forme_juridique or "").strip().upper()
        if declared_form in {"SAS", "SASU", "SARL", "EURL", "SA", "SCA", "SNC"} and not str(workspace.capital_social or "").strip():
            missing.append("capital social déclaré de l’émetteur")
        if not workspace.tva_franchise and not workspace.vat_number:
            missing.append("vat_number ou franchise TVA")
    if client is None:
        missing.append("client")
    else:
        missing += [
            "client." + f
            for f in ("name", "address_line1", "city", "postal_code", "country")
            if not getattr(client, f, None)
        ]
    if workspace and workspace.tva_franchise and invoice.tax_rate != 0:
        raise HTTPException(
            422, "La franchise de TVA impose un taux nul avant émission"
        )
    legal = invoice.legal_details or {}
    for field in ("service_date", "customer_type", "early_payment_terms"):
        if not str(legal.get(field) or "").strip():
            missing.append(field)
    if (
        invoice.tax_rate == 0
        and not workspace.tva_franchise
        and not str(legal.get("vat_exemption_mention") or "").strip()
    ):
        missing.append(
            "mention TVA justifiant le taux nul, l’exonération ou l’autoliquidation"
        )
    if not invoice.due_date:
        missing.append("due_date")
    if legal.get("customer_type") == "professional":
        if legal.get("late_payment_basis") not in {
            "ecb_plus_10",
            "legal_interest_times_3",
        }:
            missing.append("late_payment_basis")
        if (
            client
            and (client.country or "").lower() in {"france", "fr"}
            and not re.fullmatch(r"\d{9}|\d{14}", client.siret or "")
        ):
            missing.append("client.siren_ou_siret")
    if not invoice.items:
        missing.append("lignes")
    labels = {
        "legal_name": "nom légal de l’émetteur",
        "legal_address": "adresse de l’émetteur",
        "legal_city": "ville de l’émetteur",
        "legal_postal_code": "code postal de l’émetteur",
        "legal_country": "pays de l’émetteur",
        "service_date": "date de prestation",
        "customer_type": "type de client",
        "early_payment_terms": "conditions d’escompte",
        "late_payment_basis": "formule de pénalités",
        "due_date": "échéance de paiement",
        "client.siren_ou_siret": "SIREN ou SIRET du client professionnel",
    }
    if missing:
        missing = [labels.get(field, field) for field in missing]
        raise HTTPException(
            422, "Émission impossible : compléter " + ", ".join(missing)
        )
    issued_at = datetime.utcnow()
    options = workspace.settings if isinstance(workspace.settings, dict) else {}
    billing_zone = options.get("billing_timezone", "Europe/Paris")
    try:
        issued_date = (
            issued_at.replace(tzinfo=timezone.utc)
            .astimezone(ZoneInfo(billing_zone))
            .date()
        )
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise HTTPException(422, "Le fuseau de facturation de l’espace est invalide")
    if invoice.total <= 0 or (invoice.due_date and invoice.due_date < issued_date):
        raise HTTPException(422, "Montant ou échéance invalide à la date d’émission")
    # Actual issuance determines the legal date and final series; it cannot be backdated.
    invoice.issue_date = issued_date
    invoice.reference = next_reference(
        db, invoice.workspace_id, "FAC", document_date=issued_date
    )
    invoice.issued_snapshot = {
        "version": 2,
        "billing_timezone": billing_zone,
        "emitter": {f: getattr(workspace, f, None) for f in EMITTER_FIELDS},
        "client": {f: getattr(client, f, None) for f in CLIENT_FIELDS},
    }
    invoice.issued_at = issued_at
    invoice.sent_at = invoice.issued_at
    invoice.sent_to_email = email or client.email
    invoice.status = InvoiceStatus.SENT
    audit(invoice, "issued", user_id, {"delivery": "manual_declaration"})


def set_payment(
    invoice, amount, user_id, method=None, paid_date=None, expected_amount=None
):
    if invoice.status not in PAYABLE:
        raise HTTPException(
            409, "Seule une facture émise et non annulée peut recevoir un paiement"
        )
    if expected_amount is not None and expected_amount != (invoice.amount_paid or 0):
        raise HTTPException(
            409, "Un paiement a été déclaré entre-temps. Actualisez la facture."
        )
    amount = Decimal(str(amount))
    if amount <= 0 or amount > invoice.total or amount < (invoice.amount_paid or 0):
        raise HTTPException(
            422,
            "Le cumul déclaré doit augmenter, rester positif et ne pas dépasser le total",
        )
    previous = str(invoice.amount_paid or 0)
    invoice.amount_paid = amount
    invoice.payment_method = method
    invoice.paid_date = paid_date or date.today()
    invoice.status = (
        InvoiceStatus.PAID if amount == invoice.total else InvoiceStatus.PARTIAL
    )
    audit(
        invoice,
        "payment_declared",
        user_id,
        {
            "previous_amount": previous,
            "cumulative_amount": str(amount),
            "confirmation": "manual",
        },
    )


def transition(db, invoice, target, user_id, email=None):
    if target == InvoiceStatus.SENT:
        issue(db, invoice, user_id, email)
    elif target == InvoiceStatus.CANCELLED:
        # Issued invoices need a credit/correction flow. Never erase their economic effect here.
        require_draft(invoice)
        invoice.status = target
        audit(invoice, "draft_cancelled", user_id)
    elif target == InvoiceStatus.OVERDUE:
        if (
            invoice.status not in PAYABLE
            or not invoice.due_date
            or invoice.due_date >= date.today()
        ):
            raise HTTPException(409, "Cette facture ne peut pas être marquée en retard")
        invoice.status = target
        audit(invoice, "overdue", user_id)
    elif target != invoice.status:
        raise HTTPException(
            409, "Transition interdite ; utiliser les actions dédiées de facturation"
        )


def frozen_parties(invoice, workspace):
    if (
        invoice.status == InvoiceStatus.DRAFT
        and not invoice.issued_at
        and not invoice.sent_at
    ):
        return workspace, invoice.billing_client
    snapshot = invoice.issued_snapshot
    if not snapshot:
        raise HTTPException(
            409,
            "Document historique sans photographie à l’émission : consulter son original conservé.",
        )
    return SimpleNamespace(**snapshot["emitter"]), SimpleNamespace(**snapshot["client"])


def invoice_legal_text(invoice):
    details = invoice.legal_details or {}
    if not details:
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                409,
                "Consulter l’original de cette facture historique, sans conditions reconstituées",
            )
        return "Brouillon : renseigner les informations de prestation et de paiement avant émission."
    lines = [
        "Date de prestation : " + str(details.get("service_date") or "à renseigner"),
        "Escompte : " + str(details.get("early_payment_terms") or "à renseigner"),
    ]
    if details.get("vat_exemption_mention"):
        lines.append("Mention TVA : " + details["vat_exemption_mention"])
    if details.get("customer_type") == "professional":
        basis = {
            "ecb_plus_10": "taux de refinancement de la BCE applicable au premier jour du semestre concerné, majoré de 10 points",
            "legal_interest_times_3": "trois fois le taux de l’intérêt légal",
        }.get(details.get("late_payment_basis"), "taux contractuel à renseigner")
        lines += [
            "Pénalités de retard : "
            + basis
            + ", exigibles sans rappel après l’échéance.",
            "Indemnité forfaitaire légale pour frais de recouvrement : 40 euros, applicable au client professionnel en retard de paiement.",
        ]
    return "<br/>".join(escape(line) for line in lines)
