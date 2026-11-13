"""Invoice transitions and frozen parties. Manual payments are declarations, never bank confirmations."""

from datetime import datetime, date
from decimal import Decimal
from types import SimpleNamespace
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
    workspace = db.query(Workspace).filter_by(id=invoice.workspace_id).first()
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
    if not invoice.items:
        missing.append("lignes")
    if missing:
        raise HTTPException(
            422, "Émission impossible : compléter " + ", ".join(missing)
        )
    if invoice.total <= 0 or (
        invoice.due_date and invoice.due_date < invoice.issue_date
    ):
        raise HTTPException(422, "Montant ou échéance invalide")
    invoice.issued_snapshot = {
        "version": 1,
        "emitter": {f: getattr(workspace, f, None) for f in EMITTER_FIELDS},
        "client": {f: getattr(client, f, None) for f in CLIENT_FIELDS},
    }
    invoice.issued_at = datetime.utcnow()
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
