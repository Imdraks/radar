"""Platform commercial documents and manual contract review, never fictitious payment state."""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from io import BytesIO
from zoneinfo import ZoneInfo
from pypdf import PdfReader
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.api.deps import get_current_platform_admin
from app.api.platform_clients import company, log
from app.db import get_db
from app.db.models.user import User
from app.db.models.platform_sales import PlatformQuote, ExternalClientContract
from app.db.models.subscription_request import SubscriptionRequest
from app.db.models.legal_contract import LegalBundle, LegalAcceptance
from app.services.platform_quote_pdf import render_quote_pdf

router = APIRouter(prefix="/admin/clients", tags=["Platform commercial documents"])
CENT = Decimal("0.01")


class Line(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    description: str = Field(min_length=2, max_length=1000)
    quantity: Decimal = Field(gt=0, le=1000000, max_digits=12, decimal_places=3)
    unit_price: Decimal = Field(ge=0, le=100000000, max_digits=12, decimal_places=2)
    vat_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class QuoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    order_id: int | None = Field(default=None, gt=0)
    valid_until: date
    lines: list[Line] = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=3000)


class ContractInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    order_id: int = Field(gt=0)
    quote_id: int | None = Field(default=None, gt=0)
    reference: str = Field(min_length=3, max_length=200)
    signer: str = Field(min_length=2, max_length=255)
    signed_on: date


class ReviewInput(BaseModel):
    approved: bool
    reference: str = Field(min_length=10, max_length=1000)
    document_checked: bool


def serialize_quote(row):
    return dict(
        id=row.id,
        reference=row.reference,
        status=row.status,
        order_id=row.order_id,
        created_at=row.created_at,
        valid_until=row.valid_until,
        total_ht=str(row.total_ht),
        total_tax=str(row.total_tax),
        total_ttc=str(row.total_ttc),
        currency=row.currency,
        issued_at=row.issued_at,
        content_hash=row.content_hash,
    )


def serialize_contract(row):
    return dict(
        id=row.id,
        reference=row.reference,
        signer=row.signer,
        signed_on=row.signed_on,
        status=row.status,
        plan=row.plan,
        order_id=row.order_id,
        quote_id=row.quote_id,
        created_at=row.created_at,
        reviewed_at=row.reviewed_at,
        review_reference=row.review_reference,
        document_hash=row.document_hash,
    )


def quote(db, workspace_id, id, lock=False):
    query = db.query(PlatformQuote).filter_by(id=id, workspace_id=workspace_id)
    row = (query.with_for_update() if lock else query).first()
    if not row:
        raise HTTPException(404, "Devis introuvable pour cette entreprise.")
    return row


@router.post("/{workspace_id}/quotes", status_code=201)
def create_quote(
    workspace_id: int,
    data: QuoteInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    if data.valid_until < datetime.now(ZoneInfo("Europe/Paris")).date():
        raise HTTPException(422, "Choisissez une date de validité à venir.")
    publisher = db.query(LegalBundle).order_by(LegalBundle.id.desc()).first()
    if not publisher:
        raise HTTPException(
            409,
            "Publiez d’abord l’identité légale de Radar et son dossier contractuel dans Administration → Contrats.",
        )
    if (
        data.order_id
        and not db.query(SubscriptionRequest.id)
        .filter_by(id=data.order_id, workspace_id=ws.id)
        .first()
    ):
        raise HTTPException(404, "Commande introuvable pour cette entreprise.")
    owner = ws.owner
    lines = []
    ht = Decimal("0")
    tax = Decimal("0")
    for item in data.lines:
        subtotal = (item.quantity * item.unit_price).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        vat = (subtotal * item.vat_rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        ht += subtotal
        tax += vat
        lines.append(
            dict(
                description=item.description,
                quantity=str(item.quantity),
                unit_price=str(item.unit_price),
                vat_rate=str(item.vat_rate),
                total_ht=str(subtotal),
                tax=str(vat),
            )
        )
    if ht + tax > Decimal("99999999999999.99"):
        raise HTTPException(422, "Le total dépasse la limite technique du document.")
    row = PlatformQuote(
        workspace_id=ws.id,
        order_id=data.order_id,
        issuer=publisher.publisher,
        buyer={
            "name": ws.legal_name or ws.name,
            "address": ws.legal_address,
            "city": ws.legal_city,
            "postal_code": ws.legal_postal_code,
            "country": ws.legal_country,
            "siret": ws.siret,
            "email": ws.billing_email or owner.email,
        },
        lines=lines,
        total_ht=ht,
        total_tax=tax,
        total_ttc=ht + tax,
        valid_until=data.valid_until,
        notes=data.notes,
        created_by=admin.id,
        status="draft",
    )
    db.add(row)
    db.flush()
    log(
        db,
        admin,
        ws.id,
        "client.quote_created",
        {"quote_id": row.id, "reference": row.reference},
    )
    db.commit()
    return serialize_quote(row)


@router.get("/{workspace_id}/quotes/{quote_id}")
def get_quote(
    workspace_id: int,
    quote_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    company(db, workspace_id)
    row = quote(db, workspace_id, quote_id)
    return {
        **serialize_quote(row),
        "issuer": row.issuer,
        "buyer": row.buyer,
        "lines": row.lines,
        "notes": row.notes,
    }


@router.post("/{workspace_id}/quotes/{quote_id}/issue")
def issue_quote(
    workspace_id: int,
    quote_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    company(db, workspace_id)
    row = quote(db, workspace_id, quote_id, True)
    if row.status == "issued":
        return serialize_quote(row)
    if row.status != "draft":
        raise HTTPException(409, "Ce devis ne peut plus être émis.")
    if not row.buyer.get("address"):
        raise HTTPException(
            409,
            "Renseignez l’adresse légale du client puis créez un nouveau devis avec les coordonnées complètes.",
        )
    if len(row.notes.strip()) < 10:
        raise HTTPException(
            409, "Précisez la durée et les conditions de règlement avant l’émission."
        )
    if row.valid_until < datetime.now(ZoneInfo("Europe/Paris")).date():
        raise HTTPException(409, "La validité du devis est dépassée.")
    row.status = "issued"
    row.issued_at = datetime.utcnow()
    payload = {
        "reference": row.reference,
        "issuer": row.issuer,
        "buyer": row.buyer,
        "lines": row.lines,
        "valid_until": row.valid_until.isoformat(),
        "notes": row.notes,
        "total": str(row.total_ttc),
    }
    row.content_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    log(
        db,
        admin,
        workspace_id,
        "client.quote_issued",
        {"quote_id": row.id, "content_hash": row.content_hash},
    )
    db.commit()
    return serialize_quote(row)


@router.get("/{workspace_id}/quotes/{quote_id}/pdf")
def quote_pdf(
    workspace_id: int,
    quote_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    company(db, workspace_id)
    row = quote(db, workspace_id, quote_id)
    return Response(
        render_quote_pdf(row),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{row.reference}.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{workspace_id}/contracts/external", status_code=201)
async def upload_contract(
    workspace_id: int,
    data: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    ws = company(db, workspace_id, True)
    try:
        metadata = ContractInput.model_validate_json(data)
    except ValueError:
        raise HTTPException(
            422, "Vérifiez la référence, la commande, la date et le signataire."
        ) from None
    order = (
        db.query(SubscriptionRequest)
        .filter_by(id=metadata.order_id, workspace_id=ws.id)
        .first()
    )
    if not order:
        raise HTTPException(404, "Commande introuvable dans cette entreprise.")
    if metadata.signed_on > datetime.now(ZoneInfo("Europe/Paris")).date():
        raise HTTPException(422, "La date de signature ne peut pas être dans le futur.")
    if metadata.quote_id:
        linked = quote(db, ws.id, metadata.quote_id)
        if linked.order_id != order.id or linked.status != "issued":
            raise HTTPException(409, "Sélectionnez un devis émis pour cette commande.")
    document = await file.read(8 * 1024 * 1024 + 1)
    if len(document) > 8 * 1024 * 1024:
        raise HTTPException(413, "Le PDF dépasse 8 Mo.")
    if not document.startswith(b"%PDF-") or b"%%EOF" not in document[-2048:]:
        raise HTTPException(422, "Fournissez un document PDF complet.")
    try:
        reader = PdfReader(BytesIO(document), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 1000:
            raise ValueError("UNREADABLE_PDF")
    except Exception:
        raise HTTPException(
            422,
            "Le PDF n’est pas lisible ou est chiffré. Fournissez un PDF complet, non chiffré, de 1 à 1 000 pages.",
        ) from None
    row = ExternalClientContract(
        workspace_id=ws.id,
        order_id=order.id,
        quote_id=metadata.quote_id,
        plan=order.requested_value if order.kind == "plan" else None,
        reference=metadata.reference,
        signer=metadata.signer,
        signed_on=metadata.signed_on,
        document=document,
        document_hash=hashlib.sha256(document).hexdigest(),
        uploaded_by=admin.id,
        status="pending_review",
    )
    db.add(row)
    db.flush()
    log(
        db,
        admin,
        ws.id,
        "client.external_contract_uploaded",
        {"contract_id": row.id, "document_hash": row.document_hash},
    )
    db.commit()
    return serialize_contract(row)


@router.post("/{workspace_id}/contracts/external/{contract_id}/review")
def review_contract(
    workspace_id: int,
    contract_id: int,
    data: ReviewInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    company(db, workspace_id, True)
    row = (
        db.query(ExternalClientContract)
        .filter_by(id=contract_id, workspace_id=workspace_id)
        .with_for_update()
        .first()
    )
    if not row:
        raise HTTPException(404, "Contrat introuvable pour cette entreprise.")
    if row.status != "pending_review":
        raise HTTPException(
            409,
            "Ce document a déjà été contrôlé. Déposez une nouvelle version pour un nouveau contrôle.",
        )
    if data.approved and not data.document_checked:
        raise HTTPException(
            422, "Confirmez la lecture et le contrôle manuel du PDF signé."
        )
    row.status = "validated" if data.approved else "rejected"
    row.reviewed_by = admin.id
    row.reviewed_at = datetime.utcnow()
    row.review_reference = data.reference
    log(
        db,
        admin,
        workspace_id,
        "client.external_contract_reviewed",
        {
            "contract_id": row.id,
            "approved": data.approved,
            "document_hash": row.document_hash,
            "reference": data.reference,
        },
    )
    db.commit()
    return serialize_contract(row)


@router.get("/{workspace_id}/contracts/external/{contract_id}/pdf")
def contract_pdf(
    workspace_id: int,
    contract_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    company(db, workspace_id)
    row = (
        db.query(ExternalClientContract)
        .filter_by(id=contract_id, workspace_id=workspace_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Contrat introuvable.")
    return Response(
        row.document,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Radar-contrat-{row.id}.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )
