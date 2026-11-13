"""Full-credit lifecycle, protected by the existing billing permissions at router registration."""

from typing import Annotated
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_workspace_id
from app.db.models.credit_note import CreditNote
from app.services.invoice_lifecycle import locked_invoice
from app.services.credit_notes import issue_full_credit, credit_pdf

router = APIRouter()


class IssueCredit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=5, max_length=2000)
    idempotency_key: str = Field(
        min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"
    )


def serialize(note):
    return {
        key: getattr(note, key)
        for key in (
            "id",
            "invoice_id",
            "reference",
            "issue_date",
            "reason",
            "subtotal",
            "tax_amount",
            "total",
            "snapshot",
            "created_at",
        )
    }


@router.post("/invoices/{invoice_id}/credit-notes", status_code=201)
def issue(
    invoice_id: int,
    data: IssueCredit,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id),
):
    note = issue_full_credit(
        db, workspace_id, invoice_id, user.id, data.reason, data.idempotency_key
    )
    db.commit()
    db.refresh(note)
    return serialize(note)


@router.get("/invoices/{invoice_id}/credit-notes")
def list_notes(
    invoice_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id),
):
    locked_invoice(db, invoice_id, workspace_id)
    return [
        serialize(row)
        for row in db.query(CreditNote).filter_by(
            workspace_id=workspace_id, invoice_id=invoice_id
        )
    ]


@router.get("/credit-notes/{note_id}/pdf")
def pdf(
    note_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id),
):
    note = db.query(CreditNote).filter_by(id=note_id, workspace_id=workspace_id).first()
    if not note:
        raise HTTPException(404, "Avoir introuvable")
    return Response(
        credit_pdf(note),
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{note.reference}.pdf"',
        },
    )


@router.get("/invoices/{invoice_id}/electronic-invoicing")
def readiness(
    invoice_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id),
):
    invoice = locked_invoice(db, invoice_id, workspace_id)
    return {
        "invoice_id": invoice.id,
        "provider_connected": False,
        "transmission_status": "not_transmitted",
        "ready_for_transmission": False,
        "invoice_issued": bool(invoice.issued_at),
        "has_frozen_parties": bool(invoice.issued_snapshot),
        "has_declared_legal_details": bool(invoice.legal_details),
        "fully_credited": bool(invoice.credited_at),
        "required_actions": [
            "Qualifier l’entreprise et les opérations concernées par la réforme.",
            "Choisir et contractualiser une plateforme agréée ; configurer son connecteur.",
            "Valider les données, taxes, formats structurés et destinataires avec le prestataire.",
            "Recetter l’envoi, les statuts, les reprises et la conservation des preuves.",
        ],
        "notice": "Aucune transmission ni confirmation de paiement n’est simulée.",
    }


@router.get("/invoices/{invoice_id}/exchange")
def export_exchange(
    invoice_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id),
):
    import json
    from app.db.models.workspace import Workspace
    from app.services.einvoice_exchange import exchange

    invoice = locked_invoice(db, invoice_id, workspace_id)
    workspace = db.query(Workspace).filter_by(id=workspace_id).one()
    data = exchange(invoice, workspace)
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'attachment; filename="{invoice.reference}-exchange.json"',
        },
    )
