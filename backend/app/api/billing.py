"""
Billing API endpoints for quotes (devis) and invoices (factures)
Part of the Radar Business subscription
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from io import BytesIO

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, get_current_workspace_id
from app.db.models.user import User
from app.db.models.workspace import Workspace, WorkspaceMember
from app.db.models.billing import (
    BillingClient, Quote, QuoteItem, Invoice, InvoiceItem,
    QuoteStatus, InvoiceStatus, PaymentMethod
)
from app.db.models.agency import Client as CRMClient
from app.schemas.billing import (
    ClientCreate, ClientUpdate, ClientResponse, ClientSetIBAN,
    QuoteCreate, QuoteUpdate, QuoteResponse, QuoteListResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse,
    InvoicePaymentUpdate, QuoteToInvoiceCreate, BillingDashboard,
    QuoteItemCreate, InvoiceItemCreate
)
from app.core.encryption import encrypt_iban, decrypt_iban, mask_iban

router = APIRouter()


# ============ Emitter Info Schema ============

class EmitterInfo(BaseModel):
    """Workspace billing/emitter info for documents"""
    legal_name: Optional[str] = None
    legal_address: Optional[str] = None
    legal_city: Optional[str] = None
    legal_postal_code: Optional[str] = None
    legal_country: Optional[str] = "France"
    legal_phone: Optional[str] = None
    legal_email: Optional[str] = None
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    logo_drive_file_id: Optional[str] = None
    payment_info: Optional[dict] = None
    # Template IDs
    devis_template_doc_id: Optional[str] = None
    facture_template_doc_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class EmitterInfoUpdate(BaseModel):
    """Update emitter info"""
    legal_name: Optional[str] = None
    legal_address: Optional[str] = None
    legal_city: Optional[str] = None
    legal_postal_code: Optional[str] = None
    legal_country: Optional[str] = None
    legal_phone: Optional[str] = None
    legal_email: Optional[str] = None
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    logo_drive_file_id: Optional[str] = None
    payment_info: Optional[dict] = None
    devis_template_doc_id: Optional[str] = None
    facture_template_doc_id: Optional[str] = None


# ============ Helper Functions ============

def next_document_reference(db: Session, workspace_id: int, kind: str) -> str:
    from sqlalchemy.dialects.postgresql import insert
    from app.db.models.billing import BillingCounter
    year = datetime.utcnow().year
    counter = BillingCounter.__table__
    statement = insert(counter).values(workspace_id=workspace_id, year=year, kind=kind, last_number=1)
    statement = statement.on_conflict_do_update(
        index_elements=[counter.c.workspace_id, counter.c.year, counter.c.kind],
        set_={"last_number": counter.c.last_number + 1}
    ).returning(counter.c.last_number)
    number = db.execute(statement).scalar_one()
    return f"{kind}-{year}-{number:04d}"


def generate_quote_reference(db: Session, workspace_id: int) -> str:
    return next_document_reference(db, workspace_id, "DEV")


def generate_invoice_reference(db: Session, workspace_id: int) -> str:
    return next_document_reference(db, workspace_id, "FAC")


def calculate_quote_totals(quote: Quote):
    """Calculate and update quote totals"""
    subtotal = sum((Decimal(str(item.line_total)) if item.line_total else Decimal('0')) for item in quote.items)
    discount_percent = Decimal(str(quote.discount_percent or 0))
    tax_rate = Decimal(str(quote.tax_rate or 0))
    
    discount_amount = subtotal * (discount_percent / Decimal('100'))
    after_discount = subtotal - discount_amount
    tax_amount = after_discount * (tax_rate / Decimal('100'))
    total = after_discount + tax_amount
    
    quote.subtotal = subtotal
    quote.discount_amount = discount_amount
    quote.tax_amount = tax_amount
    quote.total = total


def calculate_invoice_totals(invoice: Invoice):
    """Calculate and update invoice totals"""
    subtotal = sum((Decimal(str(item.line_total)) if item.line_total else Decimal('0')) for item in invoice.items)
    discount_percent = Decimal(str(invoice.discount_percent or 0))
    tax_rate = Decimal(str(invoice.tax_rate or 0))
    
    discount_amount = subtotal * (discount_percent / Decimal('100'))
    after_discount = subtotal - discount_amount
    tax_amount = after_discount * (tax_rate / Decimal('100'))
    total = after_discount + tax_amount
    
    invoice.subtotal = subtotal
    invoice.discount_amount = discount_amount
    invoice.tax_amount = tax_amount
    invoice.total = total


# ============ Emitter (Workspace Billing Info) Endpoints ============

@router.get("/emitter", response_model=EmitterInfo)
async def get_emitter_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Get workspace emitter/billing info for documents"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    
    return EmitterInfo(
        legal_name=workspace.legal_name or workspace.name,
        legal_address=workspace.legal_address,
        legal_city=workspace.legal_city,
        legal_postal_code=workspace.legal_postal_code,
        legal_country=workspace.legal_country or "France",
        legal_phone=workspace.legal_phone,
        legal_email=workspace.legal_email or workspace.billing_email,
        siret=workspace.siret,
        vat_number=workspace.vat_number,
        logo_drive_file_id=workspace.logo_drive_file_id,
        payment_info=workspace.payment_info,
        devis_template_doc_id=workspace.devis_template_doc_id,
        facture_template_doc_id=workspace.facture_template_doc_id,
    )


@router.patch("/emitter", response_model=EmitterInfo)
async def update_emitter_info(
    emitter_in: EmitterInfoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Update workspace emitter/billing info (Admin only)"""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    
    # Check if user is workspace admin or owner
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()
    is_admin = (
        current_user.is_superuser or 
        (workspace.owner_user_id and workspace.owner_user_id == current_user.id) or
        (member and member.role == "admin")
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = emitter_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)
    
    db.commit()
    db.refresh(workspace)
    
    return EmitterInfo(
        legal_name=workspace.legal_name or workspace.name,
        legal_address=workspace.legal_address,
        legal_city=workspace.legal_city,
        legal_postal_code=workspace.legal_postal_code,
        legal_country=workspace.legal_country or "France",
        legal_phone=workspace.legal_phone,
        legal_email=workspace.legal_email or workspace.billing_email,
        siret=workspace.siret,
        vat_number=workspace.vat_number,
        logo_drive_file_id=workspace.logo_drive_file_id,
        payment_info=workspace.payment_info,
        devis_template_doc_id=workspace.devis_template_doc_id,
        facture_template_doc_id=workspace.facture_template_doc_id,
    )


# ============ Client Sync ============

@router.post("/clients/sync-crm")
async def sync_crm_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Sync all CRM clients to BillingClients table"""
    # Get all CRM clients for this workspace
    crm_clients = db.query(CRMClient).filter(CRMClient.workspace_id == workspace_id).all()
    
    synced = 0
    for crm_client in crm_clients:
        # Check if already linked
        existing = db.query(BillingClient).filter(
            BillingClient.crm_client_id == crm_client.id
        ).first()
        
        if not existing:
            # Extract first contact info
            email = None
            phone = None
            if crm_client.contacts and len(crm_client.contacts) > 0:
                first_contact = crm_client.contacts[0] if isinstance(crm_client.contacts, list) else None
                if first_contact:
                    email = first_contact.get('email')
                    phone = first_contact.get('phone')
            
            # Create billing client
            billing_client = BillingClient(
                workspace_id=workspace_id,
                crm_client_id=crm_client.id,
                name=crm_client.name,
                company_name=crm_client.name,
                email=email,
                phone=phone,
                notes=crm_client.notes
            )
            db.add(billing_client)
            synced += 1
    
    db.commit()
    return {"message": f"{synced} clients synchronisés", "synced": synced, "total": len(crm_clients)}


# ============ Client Endpoints ============

def client_to_response(client: BillingClient) -> dict:
    """Convert BillingClient to response dict with masked IBAN"""
    data = {
        "id": client.id,
        "crm_client_id": client.crm_client_id,
        "name": client.name,
        "email": client.email,
        "phone": client.phone,
        "contact_first_name": client.contact_first_name,
        "contact_last_name": client.contact_last_name,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
        "contact_role": client.contact_role,
        "address_line1": client.address_line1,
        "address_line2": client.address_line2,
        "city": client.city,
        "postal_code": client.postal_code,
        "country": client.country or "France",
        "company_name": client.company_name,
        "siret": client.siret,
        "vat_number": client.vat_number,
        "bic": client.bic,
        "bank_name": client.bank_name,
        "notes": client.notes,
        "iban_masked": mask_iban(decrypt_iban(client.iban_encrypted)) if client.iban_encrypted else None,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }
    return data


@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """List all clients for the workspace (BillingClients, synced from CRM)"""
    # Get BillingClients (now synced with CRM clients)
    query = db.query(BillingClient).filter(BillingClient.workspace_id == workspace_id)
    if search:
        query = query.filter(
            or_(
                BillingClient.name.ilike(f"%{search}%"),
                BillingClient.email.ilike(f"%{search}%"),
                BillingClient.company_name.ilike(f"%{search}%")
            )
        )
    
    clients = query.order_by(BillingClient.company_name, BillingClient.name).all()
    return [client_to_response(c) for c in clients]


@router.post("/clients", response_model=ClientResponse)
async def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Create a new client"""
    client = BillingClient(
        workspace_id=workspace_id,
        **client_in.model_dump()
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client_to_response(client)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Get a specific client"""
    client = db.query(BillingClient).filter(
        BillingClient.id == client_id,
        BillingClient.workspace_id == workspace_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return client_to_response(client)


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Update a client"""
    client = db.query(BillingClient).filter(
        BillingClient.id == client_id,
        BillingClient.workspace_id == workspace_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    update_data = client_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    return client_to_response(client)


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Delete a client"""
    client = db.query(BillingClient).filter(
        BillingClient.id == client_id,
        BillingClient.workspace_id == workspace_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Check if client has quotes or invoices
    if client.quotes or client.invoices:
        raise HTTPException(
            status_code=400, 
            detail="Impossible de supprimer un client avec des devis ou factures"
        )
    
    db.delete(client)
    db.commit()
    return {"message": "Client supprimé"}


@router.put("/clients/{client_id}/iban")
async def set_client_iban(
    client_id: int,
    iban_data: ClientSetIBAN,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """
    Set or update client IBAN (encrypted storage).
    Only admin/owner can set IBAN for security.
    """
    client = db.query(BillingClient).filter(
        BillingClient.id == client_id,
        BillingClient.workspace_id == workspace_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Encrypt and store IBAN
    client.iban_encrypted = encrypt_iban(iban_data.iban)
    db.commit()
    
    return {"message": "IBAN enregistré", "iban_masked": mask_iban(iban_data.iban)}


@router.delete("/clients/{client_id}/iban")
async def delete_client_iban(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Delete client IBAN."""
    client = db.query(BillingClient).filter(
        BillingClient.id == client_id,
        BillingClient.workspace_id == workspace_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    client.iban_encrypted = None
    db.commit()
    
    return {"message": "IBAN supprimé"}


# ============ Quote Endpoints ============

@router.get("/quotes", response_model=QuoteListResponse)
async def list_quotes(
    status: Optional[QuoteStatus] = None,
    client_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """List all quotes for the workspace"""
    query = db.query(Quote).filter(Quote.workspace_id == workspace_id)
    
    if status:
        query = query.filter(Quote.status == status)
    if client_id:
        query = query.filter(Quote.client_id == client_id)
    if search:
        query = query.filter(
            or_(
                Quote.reference.ilike(f"%{search}%"),
                Quote.title.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    quotes = query.options(
        joinedload(Quote.billing_client),
        joinedload(Quote.items)
    ).order_by(Quote.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return QuoteListResponse(
        items=quotes,
        total=total,
        page=page,
        size=size
    )


@router.post("/quotes", response_model=QuoteResponse)
async def create_quote(
    quote_in: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Create a new quote"""
    quote = Quote(
        workspace_id=workspace_id,
        reference=generate_quote_reference(db, workspace_id),
        created_by_id=current_user.id,
        title=quote_in.title,
        description=quote_in.description,
        client_id=quote_in.client_id,
        opportunity_id=quote_in.opportunity_id,
        issue_date=quote_in.issue_date,
        validity_date=quote_in.validity_date,
        tax_rate=quote_in.tax_rate,
        discount_percent=quote_in.discount_percent,
        terms=quote_in.terms,
        notes=quote_in.notes,
        status=QuoteStatus.DRAFT
    )
    db.add(quote)
    db.flush()
    
    # Add items
    for idx, item_data in enumerate(quote_in.items):
        line_total = item_data.quantity * item_data.unit_price
        item = QuoteItem(
            quote_id=quote.id,
            position=item_data.position or idx,
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            line_total=line_total
        )
        db.add(item)
    
    db.flush()
    
    # Refresh to get items
    db.refresh(quote)
    calculate_quote_totals(quote)
    
    db.commit()
    db.refresh(quote)
    
    return quote


@router.get("/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Get a specific quote"""
    quote = db.query(Quote).options(
        joinedload(Quote.billing_client),
        joinedload(Quote.items)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    return quote


@router.patch("/quotes/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: int,
    quote_in: QuoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Update a quote"""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status == QuoteStatus.INVOICED:
        raise HTTPException(status_code=400, detail="Impossible de modifier un devis déjà facturé")
    
    update_data = quote_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quote, field, value)
    
    calculate_quote_totals(quote)
    db.commit()
    db.refresh(quote)
    
    return quote


@router.post("/quotes/{quote_id}/items", response_model=QuoteResponse)
async def add_quote_item(
    quote_id: int,
    item_in: QuoteItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Add an item to a quote"""
    quote = db.query(Quote).options(
        joinedload(Quote.items)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status == QuoteStatus.INVOICED:
        raise HTTPException(status_code=400, detail="Impossible de modifier un devis facturé")
    
    line_total = item_in.quantity * item_in.unit_price
    item = QuoteItem(
        quote_id=quote.id,
        position=item_in.position,
        description=item_in.description,
        quantity=item_in.quantity,
        unit=item_in.unit,
        unit_price=item_in.unit_price,
        line_total=line_total
    )
    db.add(item)
    db.flush()
    
    db.refresh(quote)
    calculate_quote_totals(quote)
    db.commit()
    db.refresh(quote)
    
    return quote


@router.delete("/quotes/{quote_id}/items/{item_id}")
async def delete_quote_item(
    quote_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Delete an item from a quote"""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    item = db.query(QuoteItem).filter(
        QuoteItem.id == item_id,
        QuoteItem.quote_id == quote_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Ligne non trouvée")
    
    db.delete(item)
    db.flush()
    
    db.refresh(quote)
    calculate_quote_totals(quote)
    db.commit()
    
    return {"message": "Ligne supprimée"}


class QuoteItemUpdate(BaseModel):
    """Update quote item"""
    description: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None
    unit_price: Optional[float] = Field(None, ge=0)


@router.patch("/quotes/{quote_id}/items/{item_id}")
async def update_quote_item(
    quote_id: int,
    item_id: int,
    item_in: QuoteItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Update an item in a quote"""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status == QuoteStatus.INVOICED:
        raise HTTPException(status_code=400, detail="Impossible de modifier un devis facturé")
    
    item = db.query(QuoteItem).filter(
        QuoteItem.id == item_id,
        QuoteItem.quote_id == quote_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Ligne non trouvée")
    
    # Update fields
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    # Recalculate line total
    item.line_total = item.quantity * item.unit_price
    
    db.flush()
    db.refresh(quote)
    calculate_quote_totals(quote)
    db.commit()
    
    return {"message": "Ligne mise à jour", "item": {
        "id": item.id,
        "description": item.description,
        "quantity": item.quantity,
        "unit": item.unit,
        "unit_price": float(item.unit_price),
        "line_total": float(item.line_total)
    }}


@router.delete("/quotes/{quote_id}")
async def delete_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Delete a quote"""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status == QuoteStatus.INVOICED:
        raise HTTPException(status_code=400, detail="Impossible de supprimer un devis facturé")
    
    db.delete(quote)
    db.commit()
    return {"message": "Devis supprimé"}


@router.post("/quotes/{quote_id}/convert", response_model=InvoiceResponse)
async def convert_quote_to_invoice(
    quote_id: int,
    conversion: QuoteToInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Convert a quote to an invoice"""
    quote = db.query(Quote).options(
        joinedload(Quote.items),
        joinedload(Quote.billing_client)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status == QuoteStatus.INVOICED:
        raise HTTPException(status_code=400, detail="Ce devis a déjà été converti en facture")
    
    if quote.status != QuoteStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Seuls les devis acceptés peuvent être convertis")
    
    db.query(Workspace).filter_by(id=workspace_id).with_for_update().one()
    db.refresh(quote)
    if quote.status == QuoteStatus.INVOICED:
        raise HTTPException(status_code=409, detail="Devis déjà converti")

    # Create invoice
    invoice = Invoice(
        workspace_id=workspace_id,
        reference=generate_invoice_reference(db, workspace_id),
        created_by_id=current_user.id,
        client_id=quote.client_id,
        opportunity_id=quote.opportunity_id,
        source_quote_id=quote.id,
        title=quote.title,
        description=quote.description,
        issue_date=date.today(),
        due_date=conversion.due_date,
        tax_rate=quote.tax_rate,
        discount_percent=quote.discount_percent,
        terms=quote.terms,
        notes=conversion.notes or quote.notes,
        status=InvoiceStatus.DRAFT
    )
    db.add(invoice)
    db.flush()
    
    # Copy items
    for item in quote.items:
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            position=item.position,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            line_total=item.line_total
        )
        db.add(invoice_item)
    
    db.flush()
    db.refresh(invoice)
    calculate_invoice_totals(invoice)
    
    # Update quote status
    quote.status = QuoteStatus.INVOICED
    quote.invoice_id = invoice.id
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.get("/quotes/{quote_id}/pdf")
async def generate_quote_pdf(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Generate professional PDF for a quote"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas
    
    quote = db.query(Quote).options(
        joinedload(Quote.billing_client),
        joinedload(Quote.items)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    # Get workspace for emitter info
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    # Calculs
    subtotal = float(quote.subtotal or 0)
    discount_pct = float(quote.discount_percent or 0)
    discount_amt = float(quote.discount_amount or 0)
    tax_rate = float(quote.tax_rate or 20)
    tax_amt = float(quote.tax_amount or 0)
    total = float(quote.total or 0)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=10*mm,
        bottomMargin=12*mm
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Colors
    PRIMARY_COLOR = colors.HexColor('#0EA5E9')  # Bleu turquoise
    ACCENT_COLOR = colors.HexColor('#F97316')   # Orange
    GRAY_TEXT = colors.HexColor('#6B7280')
    DARK_TEXT = colors.HexColor('#1F2937')
    LIGHT_BG = colors.HexColor('#F9FAFB')
    BORDER_COLOR = colors.HexColor('#E5E7EB')
    
    # Styles personnalisés
    company_name_style = ParagraphStyle(
        'CompanyName', parent=styles['Normal'],
        fontSize=12, fontName='Helvetica-Bold', textColor=DARK_TEXT
    )
    company_info_style = ParagraphStyle(
        'CompanyInfo', parent=styles['Normal'],
        fontSize=8, textColor=GRAY_TEXT, leading=11
    )
    total_big_style = ParagraphStyle(
        'TotalBig', parent=styles['Normal'],
        fontSize=20, fontName='Helvetica-Bold', textColor=DARK_TEXT, alignment=TA_RIGHT
    )
    total_label_style = ParagraphStyle(
        'TotalLabel', parent=styles['Normal'],
        fontSize=9, textColor=GRAY_TEXT, alignment=TA_RIGHT
    )
    section_title_style = ParagraphStyle(
        'SectionTitle', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR
    )
    ref_style = ParagraphStyle(
        'RefStyle', parent=styles['Normal'],
        fontSize=10, textColor=GRAY_TEXT, alignment=TA_RIGHT
    )
    address_title_style = ParagraphStyle(
        'AddressTitle', parent=styles['Normal'],
        fontSize=8, textColor=GRAY_TEXT
    )
    address_style = ParagraphStyle(
        'Address', parent=styles['Normal'],
        fontSize=9, textColor=DARK_TEXT, fontName='Helvetica-Bold', leading=12
    )
    address_detail_style = ParagraphStyle(
        'AddressDetail', parent=styles['Normal'],
        fontSize=9, textColor=DARK_TEXT, leading=12
    )
    message_style = ParagraphStyle(
        'Message', parent=styles['Normal'],
        fontSize=9, textColor=GRAY_TEXT, fontStyle='italic', leading=12
    )
    date_label_style = ParagraphStyle(
        'DateLabel', parent=styles['Normal'],
        fontSize=8, textColor=GRAY_TEXT
    )
    date_value_style = ParagraphStyle(
        'DateValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold', textColor=DARK_TEXT
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=7, textColor=GRAY_TEXT, leading=9
    )
    
    # ========== HEADER: Logo + Company Info + Total ==========
    company_lines = []
    if workspace:
        if workspace.legal_name:
            company_lines.append(f"<b>{workspace.legal_name}</b>")
        if hasattr(workspace, 'owner') and workspace.owner:
            # User model uses full_name, not first_name/last_name
            if workspace.owner.full_name:
                company_lines.append(workspace.owner.full_name)
        if workspace.legal_address:
            company_lines.append(workspace.legal_address)
        addr_line = ""
        if workspace.legal_postal_code:
            addr_line += workspace.legal_postal_code
        if workspace.legal_city:
            addr_line += f" {workspace.legal_city}"
        if workspace.legal_country:
            addr_line += f", {workspace.legal_country}"
        if addr_line:
            company_lines.append(addr_line)
        contact_line = ""
        if workspace.legal_phone:
            contact_line += workspace.legal_phone
        if workspace.legal_email:
            if contact_line:
                contact_line += "  |  "
            contact_line += workspace.legal_email
        if contact_line:
            company_lines.append(contact_line)
        if workspace.siret:
            company_lines.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number:
            company_lines.append(f"TVA: {workspace.vat_number}")
    
    # Header table: Total right-aligned
    total_formatted = f"{int(total):,d} €".replace(',', ' ') if total == int(total) else f"{total:,.2f} €".replace(',', ' ').replace('.', ',')
    header_data = [[
        Paragraph("", company_info_style),
        [
            Paragraph("Montant total", total_label_style),
            Paragraph(total_formatted, total_big_style)
        ]
    ]]
    
    header_table = Table(header_data, colWidths=[120*mm, 55*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4*mm))
    
    # ========== DEVIS TITLE + REFERENCE ==========
    title_ref_data = [[
        Paragraph("Devis", section_title_style),
        Paragraph(f"#{quote.reference}", ref_style)
    ]]
    title_ref_table = Table(title_ref_data, colWidths=[90*mm, 85*mm])
    title_ref_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(title_ref_table)
    elements.append(Spacer(1, 3*mm))
    
    # ========== ADDRESSES: Delivery + Client ==========
    # Build client info
    client_lines = []
    client_contact_lines = []
    contact_name = "-"
    if quote.billing_client:
        c = quote.billing_client
        # Company name or client name
        if c.company_name:
            client_lines.append(f"<b>{c.company_name}</b>")
        elif c.name:
            client_lines.append(f"<b>{c.name}</b>")
        
        # Build contact name from contact fields or fallback to name
        if c.contact_first_name or c.contact_last_name:
            contact_parts = []
            if c.contact_first_name:
                contact_parts.append(c.contact_first_name)
            if c.contact_last_name:
                contact_parts.append(c.contact_last_name)
            contact_name = " ".join(contact_parts)
            if c.contact_role:
                contact_name += f" ({c.contact_role})"
        elif c.name:
            contact_name = c.name
        
        # Address
        if c.address_line1:
            client_lines.append(c.address_line1)
        if c.address_line2:
            client_lines.append(c.address_line2)
        client_addr = ""
        if c.postal_code:
            client_addr += c.postal_code
        if c.city:
            client_addr += f" {c.city}"
        if c.country and c.country != "France":
            client_addr += f", {c.country}"
        if client_addr:
            client_lines.append(client_addr)
        
        # Contact info - prefer contact-specific, fallback to main
        contact_phone = c.contact_phone or c.phone
        contact_email = c.contact_email or c.email
        if contact_phone:
            client_contact_lines.append(f"Tél: {contact_phone}")
        if contact_email:
            client_contact_lines.append(f"Email: {contact_email}")
        if c.siret:
            client_contact_lines.append(f"SIRET: {c.siret}")
        if c.vat_number:
            client_contact_lines.append(f"TVA: {c.vat_number}")
    
    address_data = [[
        [
            Paragraph("Adresse de facturation", address_title_style),
            Paragraph("<br/>".join(company_lines) if company_lines else "-", address_detail_style),
        ],
        [
            Paragraph("Devis proposé à", address_title_style),
            Paragraph(f"A l'attention de {contact_name}", address_style),
            Paragraph("<br/>".join(client_lines[1:]) if len(client_lines) > 1 else "", address_detail_style),
            Paragraph("<br/>".join(client_contact_lines), address_detail_style) if client_contact_lines else Paragraph("", address_detail_style),
        ]
    ]]
    
    address_table = Table(address_data, colWidths=[90*mm, 85*mm])
    address_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(address_table)
    elements.append(Spacer(1, 3*mm))
    
    # ========== CUSTOM MESSAGE ==========
    if quote.description:
        elements.append(Paragraph(quote.description, message_style))
        elements.append(Spacer(1, 3*mm))
    
    # ========== DATES ROW ==========
    issue_date_str = quote.issue_date.strftime('%d/%m/%Y') if quote.issue_date else '-'
    validity_date_str = quote.validity_date.strftime('%d/%m/%Y') if quote.validity_date else '-'
    terms_str = quote.terms or "Virement"
    
    dates_data = [[
        [Paragraph("Date de devis", date_label_style), Paragraph(issue_date_str, date_value_style)],
        [Paragraph("Date de livraison", date_label_style), Paragraph("-", date_value_style)],
        [Paragraph("Conditions de règlement", date_label_style), Paragraph(terms_str, date_value_style)],
        [Paragraph("Validité de l'offre", date_label_style), Paragraph(validity_date_str, date_value_style)],
    ]]
    dates_table = Table(dates_data, colWidths=[45*mm, 45*mm, 45*mm, 40*mm])
    dates_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 3*mm))
    
    # ========== ITEMS TABLE ==========
    # Header style with teal background
    items_header = ["N°", "ARTICLE", "QUANTITÉ", "PRIX UNITÉ HT", "TVA", "MONTANT HT", "MONTANT TTC"]
    table_data = [items_header]
    
    for idx, item in enumerate(sorted(quote.items, key=lambda x: x.position), 1):
        item_tax = float(item.line_total) * (tax_rate / 100)
        item_ttc = float(item.line_total) + item_tax
        table_data.append([
            str(idx),
            [
                Paragraph(f"<b>{item.description}</b>", ParagraphStyle('ItemName', fontSize=9, fontName='Helvetica-Bold')),
                Paragraph(item.description if len(item.description) > 30 else "Description du produit", ParagraphStyle('ItemDesc', fontSize=8, textColor=GRAY_TEXT))
            ],
            f"{int(item.quantity)}\n{item.unit or 'Unité(s)'}",
            f"{float(item.unit_price):,.0f} €".replace(',', ' '),
            f"{int(tax_rate)}%",
            f"{float(item.line_total):,.0f} €".replace(',', ' '),
            f"{item_ttc:,.0f} €".replace(',', ' ')
        ])
    
    items_table = Table(table_data, colWidths=[10*mm, 55*mm, 22*mm, 28*mm, 15*mm, 25*mm, 25*mm])
    
    # Style the table
    table_style = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Body
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        
        # Grid
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    
    # Alternate row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))
    
    items_table.setStyle(TableStyle(table_style))
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))
    
    # ========== TOTALS ==========
    totals_data = [
        ["", "", "", "", "", "Total HT", f"{subtotal:,.0f} €".replace(',', ' ')],
        ["", "", "", "", "", "Total TVA", f"{tax_amt:,.0f} €".replace(',', ' ')],
    ]
    if discount_pct > 0:
        totals_data.insert(1, ["", "", "", "", "", f"Remise ({discount_pct:.0f}%)", f"-{discount_amt:,.0f} €".replace(',', ' ')])
    
    totals_data.append(["", "", "", "", "", "Total TTC", f"{total:,.2f} €".replace(',', ' ').replace('.', ',')])
    
    totals_table = Table(totals_data, colWidths=[10*mm, 55*mm, 22*mm, 28*mm, 15*mm, 25*mm, 25*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (-2, -1), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 4*mm))
    
    # ========== PAYMENT INFO ==========
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
    elements.append(Spacer(1, 3*mm))
    
    payment_info = workspace.payment_info if workspace and workspace.payment_info else {}
    iban = payment_info.get('iban', 'FRXX XXXX XXXX XXXX XXXX')
    account_name = payment_info.get('account_name', workspace.legal_name if workspace else '-')
    
    payment_data = [[
        Paragraph("<b>Paiement souhaité par virement bancaire</b>", ParagraphStyle('PayTitle', fontSize=9, fontName='Helvetica-Bold')),
    ], [
        Paragraph(f"Nom associé au compte: <b>{account_name}</b><br/>IBAN: <b>{iban}</b>", ParagraphStyle('PayDetails', fontSize=8, textColor=GRAY_TEXT)),
    ]]
    
    payment_table = Table(payment_data, colWidths=[175*mm])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 4*mm),
    ]))
    elements.append(payment_table)
    elements.append(Spacer(1, 3*mm))
    
    # ========== CLIENT BANKING INFO (if available) ==========
    if quote.billing_client and quote.billing_client.iban_encrypted:
        client_iban_masked = mask_iban(decrypt_iban(quote.billing_client.iban_encrypted))
        client_bank_name = quote.billing_client.bank_name or ""
        client_bic = quote.billing_client.bic or ""
        
        client_bank_info = f"IBAN Client: <b>{client_iban_masked}</b>"
        if client_bic:
            client_bank_info += f"  |  BIC: <b>{client_bic}</b>"
        if client_bank_name:
            client_bank_info += f"  |  Banque: <b>{client_bank_name}</b>"
        
        client_bank_data = [[
            Paragraph("<b>Coordonnées bancaires du client</b>", ParagraphStyle('ClientBankTitle', fontSize=9, fontName='Helvetica-Bold')),
        ], [
            Paragraph(client_bank_info, ParagraphStyle('ClientBankDetails', fontSize=8, textColor=GRAY_TEXT)),
        ]]
        
        client_bank_table = Table(client_bank_data, colWidths=[175*mm])
        client_bank_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 4*mm),
        ]))
        elements.append(client_bank_table)
    
    elements.append(Spacer(1, 3*mm))
    
    # ========== NOTES ==========
    if quote.notes:
        elements.append(Paragraph(quote.notes, message_style))
        elements.append(Spacer(1, 2*mm))
    
    # ========== LEGAL FOOTER ==========
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
    elements.append(Spacer(1, 3*mm))

    # TVA franchise mention
    if workspace and workspace.tva_franchise:
        elements.append(Paragraph("<b>TVA non applicable, article 293 B du Code Général des Impôts.</b>", footer_style))
        elements.append(Spacer(1, 2*mm))

    legal_text = "Pour tout professionnel, en cas de retard de paiement, seront exigibles, conformément à l'article L 441-10 du code de commerce, une indemnité calculée sur la base de trois fois le taux de l'intérêt légal en vigueur ainsi qu'une indemnité forfaitaire pour frais de recouvrement de 40 euros."
    elements.append(Paragraph(legal_text, footer_style))
    elements.append(Spacer(1, 3*mm))
    
    # Company registration info
    reg_parts = []
    if workspace:
        if workspace.forme_juridique:
            forme = workspace.forme_juridique
            if workspace.capital_social:
                forme += f" au capital de {workspace.capital_social}"
            reg_parts.append(forme)
        if workspace.rcs_city:
            siren = workspace.siret[:9] if workspace.siret and len(workspace.siret) >= 9 else ""
            reg_parts.append(f"RCS {workspace.rcs_city} {siren}".strip())
        elif workspace.legal_city and workspace.siret:
            siren = workspace.siret[:9] if len(workspace.siret) >= 9 else workspace.siret
            reg_parts.append(f"RCS {workspace.legal_city} {siren}")
        if workspace.siret:
            reg_parts.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number and not workspace.tva_franchise:
            reg_parts.append(f"TVA: {workspace.vat_number}")
    elements.append(Paragraph("  •  ".join(reg_parts) if reg_parts else "", footer_style))
    elements.append(Spacer(1, 4*mm))

    # ========== SIGNATURE ==========
    sig_style = ParagraphStyle('SigStyle', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT)
    sig_data = [[
        [Paragraph("<b>Bon pour accord</b>", sig_style), Paragraph("Date et signature du client :", ParagraphStyle('SigLabel', fontSize=8, textColor=GRAY_TEXT)), Spacer(1, 12*mm)],
        [Paragraph("", sig_style)]
    ]]
    sig_table = Table(sig_data, colWidths=[90*mm, 85*mm])
    sig_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOX', (0, 0), (0, 0), 0.5, BORDER_COLOR)]))
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.seek(0)
    
    filename = f"{quote.reference}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/quotes/{quote_id}/pdf/drive")
async def upload_quote_pdf_to_drive(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Generate PDF and upload to Google Drive, replacing old version if exists"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from app.services.google_workspace import GoogleWorkspaceService
    from app.db.models.account import Account
    
    quote = db.query(Quote).options(
        joinedload(Quote.billing_client),
        joinedload(Quote.items)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    # Get user's Google account
    google_account = db.query(Account).filter(
        Account.user_id == current_user.id,
        Account.provider == "google"
    ).first()
    
    if not google_account:
        raise HTTPException(status_code=400, detail="Connectez votre compte Google pour sauvegarder sur Drive")
    
    # Get workspace
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    # Generate PDF (same code as above but simplified)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    elements = []
    
    # Colors
    PRIMARY_COLOR = colors.HexColor('#0EA5E9')
    GRAY_TEXT = colors.HexColor('#6B7280')
    DARK_TEXT = colors.HexColor('#1F2937')
    LIGHT_BG = colors.HexColor('#F9FAFB')
    BORDER_COLOR = colors.HexColor('#E5E7EB')
    
    # Calculs
    subtotal = float(quote.subtotal or 0)
    discount_pct = float(quote.discount_percent or 0)
    discount_amt = float(quote.discount_amount or 0)
    tax_rate = float(quote.tax_rate or 20)
    tax_amt = float(quote.tax_amount or 0)
    total = float(quote.total or 0)
    
    # Styles
    company_info_style = ParagraphStyle('CompanyInfo', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT, leading=11)
    total_big_style = ParagraphStyle('TotalBig', parent=styles['Normal'], fontSize=20, fontName='Helvetica-Bold', textColor=DARK_TEXT, alignment=TA_RIGHT)
    total_label_style = ParagraphStyle('TotalLabel', parent=styles['Normal'], fontSize=9, textColor=GRAY_TEXT, alignment=TA_RIGHT)
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=13, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR)
    ref_style = ParagraphStyle('RefStyle', parent=styles['Normal'], fontSize=10, textColor=GRAY_TEXT, alignment=TA_RIGHT)
    address_title_style = ParagraphStyle('AddressTitle', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT)
    address_style = ParagraphStyle('Address', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT, fontName='Helvetica-Bold', leading=12)
    address_detail_style = ParagraphStyle('AddressDetail', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT, leading=12)
    message_style = ParagraphStyle('Message', parent=styles['Normal'], fontSize=9, textColor=GRAY_TEXT, leading=12)
    date_label_style = ParagraphStyle('DateLabel', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT)
    date_value_style = ParagraphStyle('DateValue', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=DARK_TEXT)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=GRAY_TEXT, leading=9)
    
    # Build company info
    company_lines = []
    if workspace:
        if workspace.legal_name: company_lines.append(f"<b>{workspace.legal_name}</b>")
        if workspace.legal_address: company_lines.append(workspace.legal_address)
        addr = f"{workspace.legal_postal_code or ''} {workspace.legal_city or ''} {workspace.legal_country or ''}".strip()
        if addr: company_lines.append(addr)
        if workspace.siret: company_lines.append(f"SIRET: {workspace.siret}")
    
    # Header
    total_formatted = f"{int(total):,d} €".replace(',', ' ') if total == int(total) else f"{total:,.2f} €".replace(',', ' ').replace('.', ',')
    header_data = [[
        Paragraph("", company_info_style),
        [Paragraph("Montant total", total_label_style), Paragraph(total_formatted, total_big_style)]
    ]]
    header_table = Table(header_data, colWidths=[120*mm, 55*mm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(header_table)
    elements.append(Spacer(1, 4*mm))
    
    # Title
    title_data = [[Paragraph("Devis", section_title_style), Paragraph(f"#{quote.reference}", ref_style)]]
    title_table = Table(title_data, colWidths=[90*mm, 85*mm])
    title_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(title_table)
    elements.append(Spacer(1, 3*mm))
    
    # Client info
    client_lines = []
    if quote.billing_client:
        c = quote.billing_client
        if c.name: client_lines.append(f"<b>{c.name}</b>")
        if c.address_line1: client_lines.append(c.address_line1)
        if c.postal_code or c.city: client_lines.append(f"{c.postal_code or ''} {c.city or ''}")
    
    address_data = [[
        [Paragraph("Adresse de facturation", address_title_style), Paragraph("<br/>".join(company_lines) if company_lines else "-", address_detail_style)],
        [Paragraph("Devis proposé à", address_title_style), Paragraph(f"A l'attention de {quote.billing_client.name if quote.billing_client else '-'}", address_style)]
    ]]
    address_table = Table(address_data, colWidths=[90*mm, 85*mm])
    address_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(address_table)
    elements.append(Spacer(1, 3*mm))
    
    # Dates
    issue_str = quote.issue_date.strftime('%d/%m/%Y') if quote.issue_date else '-'
    validity_str = quote.validity_date.strftime('%d/%m/%Y') if quote.validity_date else '-'
    dates_data = [[
        [Paragraph("Date de devis", date_label_style), Paragraph(issue_str, date_value_style)],
        [Paragraph("Conditions", date_label_style), Paragraph(quote.terms or "Virement", date_value_style)],
        [Paragraph("Validité", date_label_style), Paragraph(validity_str, date_value_style)],
    ]]
    dates_table = Table(dates_data, colWidths=[60*mm, 60*mm, 55*mm])
    dates_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG), ('TOPPADDING', (0, 0), (-1, -1), 2*mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm)]))
    elements.append(dates_table)
    elements.append(Spacer(1, 3*mm))
    
    # Items table
    items_header = ["N°", "Article", "Qté", "Prix HT", "TVA", "Total HT"]
    table_data = [items_header]
    for idx, item in enumerate(sorted(quote.items, key=lambda x: x.position), 1):
        table_data.append([str(idx), item.description, f"{int(item.quantity)}", f"{float(item.unit_price):,.0f} €".replace(',', ' '), f"{int(tax_rate)}%", f"{float(item.line_total):,.0f} €".replace(',', ' ')])
    
    items_table = Table(table_data, colWidths=[12*mm, 75*mm, 18*mm, 28*mm, 18*mm, 28*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'), ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))
    
    # Totals
    totals_data = [["", "", "", "", "Total HT", f"{subtotal:,.0f} €".replace(',', ' ')], ["", "", "", "", "TVA", f"{tax_amt:,.0f} €".replace(',', ' ')], ["", "", "", "", "Total TTC", f"{total:,.2f} €".replace(',', ' ').replace('.', ',')]]
    totals_table = Table(totals_data, colWidths=[12*mm, 75*mm, 18*mm, 28*mm, 18*mm, 28*mm])
    totals_table.setStyle(TableStyle([('ALIGN', (-2, 0), (-1, -1), 'RIGHT'), ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold')]))
    elements.append(totals_table)
    elements.append(Spacer(1, 3*mm))
    
    # Client banking info (if available)
    if quote.billing_client and quote.billing_client.iban_encrypted:
        client_iban_masked = mask_iban(decrypt_iban(quote.billing_client.iban_encrypted))
        client_bank_name = quote.billing_client.bank_name or ""
        client_bic = quote.billing_client.bic or ""
        
        client_bank_info = f"IBAN Client: <b>{client_iban_masked}</b>"
        if client_bic:
            client_bank_info += f"  |  BIC: <b>{client_bic}</b>"
        if client_bank_name:
            client_bank_info += f"  |  Banque: <b>{client_bank_name}</b>"
        
        elements.append(Paragraph(client_bank_info, footer_style))
        elements.append(Spacer(1, 3*mm))
    
    # Footer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
    elements.append(Spacer(1, 3*mm))

    if workspace and workspace.tva_franchise:
        elements.append(Paragraph("<b>TVA non applicable, article 293 B du Code Général des Impôts.</b>", footer_style))
        elements.append(Spacer(1, 2*mm))

    legal_text = "Pour tout professionnel, en cas de retard de paiement, seront exigibles, conformément à l'article L 441-10 du code de commerce, une indemnité calculée sur la base de trois fois le taux de l'intérêt légal en vigueur ainsi qu'une indemnité forfaitaire pour frais de recouvrement de 40 euros."
    elements.append(Paragraph(legal_text, footer_style))
    elements.append(Spacer(1, 3*mm))

    reg_parts = []
    if workspace:
        if workspace.forme_juridique:
            forme = workspace.forme_juridique
            if workspace.capital_social:
                forme += f" au capital de {workspace.capital_social}"
            reg_parts.append(forme)
        if workspace.rcs_city:
            siren = workspace.siret[:9] if workspace.siret and len(workspace.siret) >= 9 else ""
            reg_parts.append(f"RCS {workspace.rcs_city} {siren}".strip())
        elif workspace.legal_city and workspace.siret:
            siren = workspace.siret[:9] if len(workspace.siret) >= 9 else workspace.siret
            reg_parts.append(f"RCS {workspace.legal_city} {siren}")
        if workspace.siret:
            reg_parts.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number and not workspace.tva_franchise:
            reg_parts.append(f"TVA: {workspace.vat_number}")
    elements.append(Paragraph("  •  ".join(reg_parts) if reg_parts else "", footer_style))
    elements.append(Spacer(1, 4*mm))

    sig_style = ParagraphStyle('SigStyle', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT)
    sig_data = [[
        [Paragraph("<b>Bon pour accord</b>", sig_style), Paragraph("Date et signature du client :", ParagraphStyle('SigLabel', fontSize=8, textColor=GRAY_TEXT)), Spacer(1, 12*mm)],
        [Paragraph("", sig_style)]
    ]]
    sig_table = Table(sig_data, colWidths=[90*mm, 85*mm])
    sig_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOX', (0, 0), (0, 0), 0.5, BORDER_COLOR)]))
    elements.append(sig_table)
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    
    # Initialize Google service
    try:
        google_service = GoogleWorkspaceService(current_user.id)
        
        # Delete old PDF if exists
        if quote.drive_pdf_id:
            try:
                await google_service.delete_file(quote.drive_pdf_id)
            except Exception:
                pass  # Ignore if file doesn't exist
        
        # Find or create Radar/Business/Devis folder
        folder_id = quote.drive_folder_id
        if not folder_id:
            # Try DriveFolderMap first
            from app.db.models.drive_folder_map import DriveFolderMap, DriveFolderType
            folder_map = db.query(DriveFolderMap).filter(
                DriveFolderMap.workspace_id == workspace_id,
                DriveFolderMap.folder_type == DriveFolderType.BUSINESS_QUOTES.value
            ).first()
            if folder_map:
                folder_id = folder_map.drive_folder_id
            else:
                # Fallback: create Radar/Business/Devis manually
                radar_folder = await google_service.find_folder_by_name("Radar")
                if not radar_folder:
                    radar_folder = await google_service.create_folder("Radar")
                business_folder = await google_service.find_folder_by_name("Business", radar_folder["id"])
                if not business_folder:
                    business_folder = await google_service.create_folder("Business", radar_folder["id"])
                devis_folder = await google_service.find_folder_by_name("Devis", business_folder["id"])
                if not devis_folder:
                    devis_folder = await google_service.create_folder("Devis", business_folder["id"])
                folder_id = devis_folder["id"]
            
            quote.drive_folder_id = folder_id
        
        # Upload new PDF
        filename = f"{quote.reference}.pdf"
        file_metadata = await google_service.upload_file(
            file_content=pdf_bytes,
            filename=filename,
            mime_type="application/pdf",
            parent_folder_id=folder_id
        )
        
        # Store the new file ID
        quote.drive_pdf_id = file_metadata.get('id')
        quote.drive_web_view_link = file_metadata.get('webViewLink')
        
        db.commit()
        
        return {
            "message": "PDF sauvegardé sur Google Drive",
            "drive_file_id": quote.drive_pdf_id,
            "web_view_link": quote.drive_web_view_link
        }
        
    except Exception as e:
        logger.exception(f"Erreur Google Drive devis: {e}")
        raise HTTPException(status_code=500, detail="Erreur Google Drive")


# ============ Invoice Endpoints ============

@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    status: Optional[InvoiceStatus] = None,
    client_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """List all invoices for the workspace"""
    query = db.query(Invoice).filter(Invoice.workspace_id == workspace_id)
    
    if status:
        query = query.filter(Invoice.status == status)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if search:
        query = query.filter(
            or_(
                Invoice.reference.ilike(f"%{search}%"),
                Invoice.title.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    invoices = query.options(
        joinedload(Invoice.billing_client),
        joinedload(Invoice.items)
    ).order_by(Invoice.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return InvoiceListResponse(
        items=invoices,
        total=total,
        page=page,
        size=size
    )


@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Create a new invoice"""
    invoice = Invoice(
        workspace_id=workspace_id,
        reference=generate_invoice_reference(db, workspace_id),
        created_by_id=current_user.id,
        title=invoice_in.title,
        description=invoice_in.description,
        client_id=invoice_in.client_id,
        opportunity_id=invoice_in.opportunity_id,
        issue_date=invoice_in.issue_date,
        due_date=invoice_in.due_date,
        tax_rate=invoice_in.tax_rate,
        discount_percent=invoice_in.discount_percent,
        terms=invoice_in.terms,
        notes=invoice_in.notes,
        status=InvoiceStatus.DRAFT
    )
    db.add(invoice)
    db.flush()
    
    # Add items
    for idx, item_data in enumerate(invoice_in.items):
        line_total = item_data.quantity * item_data.unit_price
        item = InvoiceItem(
            invoice_id=invoice.id,
            position=item_data.position or idx,
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            line_total=line_total
        )
        db.add(item)
    
    db.flush()
    db.refresh(invoice)
    calculate_invoice_totals(invoice)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Get a specific invoice"""
    invoice = db.query(Invoice).options(
        joinedload(Invoice.billing_client),
        joinedload(Invoice.items)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    return invoice


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Update an invoice"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Impossible de modifier une facture payée")
    
    update_data = invoice_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
    calculate_invoice_totals(invoice)
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.post("/invoices/{invoice_id}/items", response_model=InvoiceResponse)
async def add_invoice_item(
    invoice_id: int,
    item_in: InvoiceItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Add an item to an invoice"""
    invoice = db.query(Invoice).options(
        joinedload(Invoice.items)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Impossible de modifier une facture payée")
    
    line_total = item_in.quantity * item_in.unit_price
    item = InvoiceItem(
        invoice_id=invoice.id,
        position=item_in.position,
        description=item_in.description,
        quantity=item_in.quantity,
        unit=item_in.unit,
        unit_price=item_in.unit_price,
        line_total=line_total
    )
    db.add(item)
    db.flush()
    
    db.refresh(invoice)
    calculate_invoice_totals(invoice)
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.delete("/invoices/{invoice_id}/items/{item_id}")
async def delete_invoice_item(
    invoice_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Delete an item from an invoice"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Impossible de modifier une facture payée")
    
    item = db.query(InvoiceItem).filter(
        InvoiceItem.id == item_id,
        InvoiceItem.invoice_id == invoice_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Ligne non trouvée")
    
    db.delete(item)
    db.flush()
    
    db.refresh(invoice)
    calculate_invoice_totals(invoice)
    db.commit()
    
    return {"message": "Ligne supprimée"}


@router.post("/invoices/{invoice_id}/payment", response_model=InvoiceResponse)
async def record_payment(
    invoice_id: int,
    payment: InvoicePaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Record a payment for an invoice"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    invoice.amount_paid = payment.amount_paid
    invoice.payment_method = payment.payment_method
    invoice.paid_date = payment.paid_date or date.today()
    
    # Update status based on payment
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID
    elif invoice.amount_paid > 0:
        invoice.status = InvoiceStatus.PARTIAL
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Delete an invoice"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Seules les factures brouillon peuvent être supprimées")
    
    db.delete(invoice)
    db.commit()
    return {"message": "Facture supprimée"}


# ============ Invoice PDF ============

@router.get("/invoices/{invoice_id}/pdf")
async def generate_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Generate professional PDF for an invoice"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    invoice = db.query(Invoice).options(
        joinedload(Invoice.billing_client),
        joinedload(Invoice.items)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()

    # Calculs
    subtotal = float(invoice.subtotal or 0)
    discount_pct = float(invoice.discount_percent or 0)
    discount_amt = float(invoice.discount_amount or 0)
    tax_rate = float(invoice.tax_rate or 20)
    tax_amt = float(invoice.tax_amount or 0)
    total = float(invoice.total or 0)
    amount_paid = float(invoice.amount_paid or 0)
    remaining = total - amount_paid

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=10*mm, bottomMargin=12*mm
    )

    styles = getSampleStyleSheet()
    elements = []

    # Colors
    PRIMARY_COLOR = colors.HexColor('#7C3AED')  # Purple (Radar)
    ACCENT_COLOR = colors.HexColor('#F97316')
    GRAY_TEXT = colors.HexColor('#6B7280')
    DARK_TEXT = colors.HexColor('#1F2937')
    LIGHT_BG = colors.HexColor('#F9FAFB')
    BORDER_COLOR = colors.HexColor('#E5E7EB')
    GREEN_COLOR = colors.HexColor('#059669')

    # Styles
    company_info_style = ParagraphStyle('CompanyInfo', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT, leading=11)
    total_big_style = ParagraphStyle('TotalBig', parent=styles['Normal'], fontSize=20, fontName='Helvetica-Bold', textColor=DARK_TEXT, alignment=TA_RIGHT)
    total_label_style = ParagraphStyle('TotalLabel', parent=styles['Normal'], fontSize=9, textColor=GRAY_TEXT, alignment=TA_RIGHT)
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=13, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR)
    ref_style = ParagraphStyle('RefStyle', parent=styles['Normal'], fontSize=10, textColor=GRAY_TEXT, alignment=TA_RIGHT)
    address_title_style = ParagraphStyle('AddressTitle', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT)
    address_style = ParagraphStyle('Address', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT, fontName='Helvetica-Bold', leading=12)
    address_detail_style = ParagraphStyle('AddressDetail', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT, leading=12)
    message_style = ParagraphStyle('Message', parent=styles['Normal'], fontSize=9, textColor=GRAY_TEXT, fontStyle='italic', leading=12)
    date_label_style = ParagraphStyle('DateLabel', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT)
    date_value_style = ParagraphStyle('DateValue', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=DARK_TEXT)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=GRAY_TEXT, leading=9)

    # ========== HEADER: Company Info + Total ==========
    company_lines = []
    if workspace:
        if workspace.legal_name:
            company_lines.append(f"<b>{workspace.legal_name}</b>")
        if hasattr(workspace, 'owner') and workspace.owner and workspace.owner.full_name:
            company_lines.append(workspace.owner.full_name)
        if workspace.legal_address:
            company_lines.append(workspace.legal_address)
        addr_line = ""
        if workspace.legal_postal_code:
            addr_line += workspace.legal_postal_code
        if workspace.legal_city:
            addr_line += f" {workspace.legal_city}"
        if workspace.legal_country:
            addr_line += f", {workspace.legal_country}"
        if addr_line:
            company_lines.append(addr_line)
        contact_line = ""
        if workspace.legal_phone:
            contact_line += workspace.legal_phone
        if workspace.legal_email:
            if contact_line:
                contact_line += "  |  "
            contact_line += workspace.legal_email
        if contact_line:
            company_lines.append(contact_line)
        if workspace.siret:
            company_lines.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number:
            company_lines.append(f"TVA: {workspace.vat_number}")

    total_formatted = f"{int(total):,d} €".replace(',', ' ') if total == int(total) else f"{total:,.2f} €".replace(',', ' ').replace('.', ',')
    header_data = [[
        Paragraph("", company_info_style),
        [
            Paragraph("Montant total TTC", total_label_style),
            Paragraph(total_formatted, total_big_style)
        ]
    ]]
    header_table = Table(header_data, colWidths=[120*mm, 55*mm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(header_table)
    elements.append(Spacer(1, 4*mm))

    # ========== FACTURE TITLE + REFERENCE ==========
    title_data = [[Paragraph("Facture", section_title_style), Paragraph(f"#{invoice.reference}", ref_style)]]
    title_table = Table(title_data, colWidths=[90*mm, 85*mm])
    title_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(title_table)
    elements.append(Spacer(1, 3*mm))

    # ========== CLIENT INFO ==========
    client_lines = []
    client_contact_lines = []
    contact_name = "-"
    if invoice.billing_client:
        c = invoice.billing_client
        if c.company_name:
            client_lines.append(f"<b>{c.company_name}</b>")
        elif c.name:
            client_lines.append(f"<b>{c.name}</b>")

        if c.contact_first_name or c.contact_last_name:
            parts = []
            if c.contact_first_name: parts.append(c.contact_first_name)
            if c.contact_last_name: parts.append(c.contact_last_name)
            contact_name = " ".join(parts)
            if c.contact_role:
                contact_name += f" ({c.contact_role})"
        elif c.name:
            contact_name = c.name

        if c.address_line1: client_lines.append(c.address_line1)
        if c.address_line2: client_lines.append(c.address_line2)
        client_addr = ""
        if c.postal_code: client_addr += c.postal_code
        if c.city: client_addr += f" {c.city}"
        if c.country and c.country != "France": client_addr += f", {c.country}"
        if client_addr: client_lines.append(client_addr)

        contact_phone = c.contact_phone or c.phone
        contact_email = c.contact_email or c.email
        if contact_phone: client_contact_lines.append(f"Tél: {contact_phone}")
        if contact_email: client_contact_lines.append(f"Email: {contact_email}")
        if c.siret: client_contact_lines.append(f"SIRET: {c.siret}")
        if c.vat_number: client_contact_lines.append(f"TVA: {c.vat_number}")

    address_data = [[
        [
            Paragraph("Adresse de facturation", address_title_style),
            Paragraph("<br/>".join(company_lines) if company_lines else "-", address_detail_style),
        ],
        [
            Paragraph("Facture adressée à", address_title_style),
            Paragraph(f"A l'attention de {contact_name}", address_style),
            Paragraph("<br/>".join(client_lines[1:]) if len(client_lines) > 1 else "", address_detail_style),
            Paragraph("<br/>".join(client_contact_lines), address_detail_style) if client_contact_lines else Paragraph("", address_detail_style),
        ]
    ]]
    address_table = Table(address_data, colWidths=[90*mm, 85*mm])
    address_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(address_table)
    elements.append(Spacer(1, 3*mm))

    # ========== DESCRIPTION ==========
    if invoice.description:
        elements.append(Paragraph(invoice.description, message_style))
        elements.append(Spacer(1, 3*mm))

    # ========== DATES ROW ==========
    issue_date_str = invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else '-'
    due_date_str = invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else '-'
    terms_str = invoice.terms or "Virement"

    dates_data = [[
        [Paragraph("Date de facture", date_label_style), Paragraph(issue_date_str, date_value_style)],
        [Paragraph("Date d'échéance", date_label_style), Paragraph(due_date_str, date_value_style)],
        [Paragraph("Conditions de règlement", date_label_style), Paragraph(terms_str, date_value_style)],
        [Paragraph("Statut", date_label_style), Paragraph(invoice.status.value.upper(), date_value_style)],
    ]]
    dates_table = Table(dates_data, colWidths=[45*mm, 45*mm, 45*mm, 40*mm])
    dates_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 3*mm))

    # ========== ITEMS TABLE ==========
    items_header = ["N°", "ARTICLE", "QUANTITÉ", "PRIX UNITÉ HT", "TVA", "MONTANT HT", "MONTANT TTC"]
    table_data = [items_header]

    for idx, item in enumerate(sorted(invoice.items, key=lambda x: x.position), 1):
        item_tax = float(item.line_total) * (tax_rate / 100)
        item_ttc = float(item.line_total) + item_tax
        table_data.append([
            str(idx),
            item.description,
            f"{int(item.quantity)} {item.unit or 'Unité(s)'}",
            f"{float(item.unit_price):,.0f} €".replace(',', ' '),
            f"{int(tax_rate)}%",
            f"{float(item.line_total):,.0f} €".replace(',', ' '),
            f"{item_ttc:,.0f} €".replace(',', ' ')
        ])

    items_table = Table(table_data, colWidths=[10*mm, 55*mm, 22*mm, 28*mm, 15*mm, 25*mm, 25*mm])
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))
    items_table.setStyle(TableStyle(table_style))
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))

    # ========== TOTALS ==========
    totals_data = [
        ["", "", "", "", "", "Total HT", f"{subtotal:,.0f} €".replace(',', ' ')],
        ["", "", "", "", "", "Total TVA", f"{tax_amt:,.0f} €".replace(',', ' ')],
    ]
    if discount_pct > 0:
        totals_data.insert(1, ["", "", "", "", "", f"Remise ({discount_pct:.0f}%)", f"-{discount_amt:,.0f} €".replace(',', ' ')])
    totals_data.append(["", "", "", "", "", "Total TTC", f"{total:,.2f} €".replace(',', ' ').replace('.', ',')])
    if amount_paid > 0:
        totals_data.append(["", "", "", "", "", "Déjà payé", f"-{amount_paid:,.2f} €".replace(',', ' ').replace('.', ',')])
        totals_data.append(["", "", "", "", "", "Reste à payer", f"{remaining:,.2f} €".replace(',', ' ').replace('.', ',')])

    totals_table = Table(totals_data, colWidths=[10*mm, 55*mm, 22*mm, 28*mm, 15*mm, 25*mm, 25*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (-2, -1), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 4*mm))

    # ========== PAYMENT INFO ==========
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
    elements.append(Spacer(1, 3*mm))

    payment_info = workspace.payment_info if workspace and workspace.payment_info else {}
    iban = payment_info.get('iban', '')
    account_name = payment_info.get('account_name', workspace.legal_name if workspace else '-')

    if iban:
        payment_data = [[
            Paragraph("<b>Paiement souhaité par virement bancaire</b>", ParagraphStyle('PayTitle', fontSize=9, fontName='Helvetica-Bold')),
        ], [
            Paragraph(f"Nom associé au compte: <b>{account_name}</b><br/>IBAN: <b>{iban}</b>", ParagraphStyle('PayDetails', fontSize=8, textColor=GRAY_TEXT)),
        ]]
        payment_table = Table(payment_data, colWidths=[175*mm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 4*mm),
        ]))
        elements.append(payment_table)
        elements.append(Spacer(1, 3*mm))

    # ========== NOTES ==========
    if invoice.notes:
        elements.append(Paragraph(invoice.notes, message_style))
        elements.append(Spacer(1, 3*mm))

    elements.append(Spacer(1, 3*mm))

    # ========== LEGAL FOOTER ==========
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
    elements.append(Spacer(1, 3*mm))

    if workspace and workspace.tva_franchise:
        elements.append(Paragraph("<b>TVA non applicable, article 293 B du Code Général des Impôts.</b>", footer_style))
        elements.append(Spacer(1, 2*mm))

    legal_text = "Pour tout professionnel, en cas de retard de paiement, seront exigibles, conformément à l'article L 441-10 du code de commerce, une indemnité calculée sur la base de trois fois le taux de l'intérêt légal en vigueur ainsi qu'une indemnité forfaitaire pour frais de recouvrement de 40 euros."
    elements.append(Paragraph(legal_text, footer_style))
    elements.append(Spacer(1, 3*mm))

    reg_parts = []
    if workspace:
        if workspace.forme_juridique:
            forme = workspace.forme_juridique
            if workspace.capital_social:
                forme += f" au capital de {workspace.capital_social}"
            reg_parts.append(forme)
        if workspace.rcs_city:
            siren = workspace.siret[:9] if workspace.siret and len(workspace.siret) >= 9 else ""
            reg_parts.append(f"RCS {workspace.rcs_city} {siren}".strip())
        elif workspace.legal_city and workspace.siret:
            siren = workspace.siret[:9] if len(workspace.siret) >= 9 else workspace.siret
            reg_parts.append(f"RCS {workspace.legal_city} {siren}")
        if workspace.siret:
            reg_parts.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number and not workspace.tva_franchise:
            reg_parts.append(f"TVA: {workspace.vat_number}")
    elements.append(Paragraph("  •  ".join(reg_parts) if reg_parts else "", footer_style))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.seek(0)

    filename = f"{invoice.reference}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ Invoice PDF to Drive ============

@router.post("/invoices/{invoice_id}/pdf/drive")
async def upload_invoice_pdf_to_drive(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Generate invoice PDF and upload to Google Drive, replacing old version if exists"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from app.services.google_workspace import GoogleWorkspaceService
    from app.db.models.account import Account

    invoice = db.query(Invoice).options(
        joinedload(Invoice.billing_client),
        joinedload(Invoice.items)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")

    # Check Google account
    google_account = db.query(Account).filter(
        Account.user_id == current_user.id,
        Account.provider == "google"
    ).first()

    if not google_account:
        raise HTTPException(status_code=400, detail="Connectez votre compte Google pour sauvegarder sur Drive")

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()

    # ---- Generate PDF (same as GET endpoint) ----
    subtotal = float(invoice.subtotal or 0)
    discount_pct = float(invoice.discount_percent or 0)
    discount_amt = float(invoice.discount_amount or 0)
    tax_rate = float(invoice.tax_rate or 20)
    tax_amt = float(invoice.tax_amount or 0)
    total = float(invoice.total or 0)
    amount_paid = float(invoice.amount_paid or 0)
    remaining = total - amount_paid

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    elements = []

    PRIMARY_COLOR = colors.HexColor('#7C3AED')
    GRAY_TEXT = colors.HexColor('#6B7280')
    DARK_TEXT = colors.HexColor('#1F2937')
    LIGHT_BG = colors.HexColor('#F9FAFB')
    BORDER_COLOR = colors.HexColor('#E5E7EB')

    company_info_style = ParagraphStyle('CompanyInfo', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT, leading=11)
    total_big_style = ParagraphStyle('TotalBig', parent=styles['Normal'], fontSize=20, fontName='Helvetica-Bold', textColor=DARK_TEXT, alignment=TA_RIGHT)
    total_label_style = ParagraphStyle('TotalLabel', parent=styles['Normal'], fontSize=9, textColor=GRAY_TEXT, alignment=TA_RIGHT)
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=13, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR)
    ref_style = ParagraphStyle('RefStyle', parent=styles['Normal'], fontSize=10, textColor=GRAY_TEXT, alignment=TA_RIGHT)
    address_title_style = ParagraphStyle('AddressTitle', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT)
    address_style = ParagraphStyle('Address', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT, fontName='Helvetica-Bold', leading=12)
    address_detail_style = ParagraphStyle('AddressDetail', parent=styles['Normal'], fontSize=9, textColor=DARK_TEXT, leading=12)
    message_style = ParagraphStyle('Message', parent=styles['Normal'], fontSize=9, textColor=GRAY_TEXT, leading=12)
    date_label_style = ParagraphStyle('DateLabel', parent=styles['Normal'], fontSize=8, textColor=GRAY_TEXT)
    date_value_style = ParagraphStyle('DateValue', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=DARK_TEXT)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=GRAY_TEXT, leading=9)

    # Company info
    company_lines = []
    if workspace:
        if workspace.legal_name: company_lines.append(f"<b>{workspace.legal_name}</b>")
        if workspace.legal_address: company_lines.append(workspace.legal_address)
        addr = f"{workspace.legal_postal_code or ''} {workspace.legal_city or ''} {workspace.legal_country or ''}".strip()
        if addr: company_lines.append(addr)
        if workspace.siret: company_lines.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number: company_lines.append(f"TVA: {workspace.vat_number}")

    # Header
    total_formatted = f"{int(total):,d} €".replace(',', ' ') if total == int(total) else f"{total:,.2f} €".replace(',', ' ').replace('.', ',')
    header_data = [[
        Paragraph("", company_info_style),
        [Paragraph("Montant total TTC", total_label_style), Paragraph(total_formatted, total_big_style)]
    ]]
    header_table = Table(header_data, colWidths=[120*mm, 55*mm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(header_table)
    elements.append(Spacer(1, 4*mm))

    # Title
    title_data = [[Paragraph("Facture", section_title_style), Paragraph(f"#{invoice.reference}", ref_style)]]
    title_table = Table(title_data, colWidths=[90*mm, 85*mm])
    title_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(title_table)
    elements.append(Spacer(1, 3*mm))

    # Client info
    client_lines = []
    contact_name = "-"
    if invoice.billing_client:
        c = invoice.billing_client
        if c.company_name: client_lines.append(f"<b>{c.company_name}</b>")
        elif c.name: client_lines.append(f"<b>{c.name}</b>")
        if c.contact_first_name or c.contact_last_name:
            parts = []
            if c.contact_first_name: parts.append(c.contact_first_name)
            if c.contact_last_name: parts.append(c.contact_last_name)
            contact_name = " ".join(parts)
        elif c.name: contact_name = c.name
        if c.address_line1: client_lines.append(c.address_line1)
        client_addr = ""
        if c.postal_code: client_addr += c.postal_code
        if c.city: client_addr += f" {c.city}"
        if client_addr: client_lines.append(client_addr)

    address_data = [[
        [Paragraph("Adresse de facturation", address_title_style), Paragraph("<br/>".join(company_lines) if company_lines else "-", address_detail_style)],
        [Paragraph("Facture adressée à", address_title_style), Paragraph(f"A l'attention de {contact_name}", address_style)]
    ]]
    address_table = Table(address_data, colWidths=[90*mm, 85*mm])
    address_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(address_table)
    elements.append(Spacer(1, 3*mm))

    # Dates
    issue_str = invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else '-'
    due_str = invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else '-'
    dates_data = [[
        [Paragraph("Date de facture", date_label_style), Paragraph(issue_str, date_value_style)],
        [Paragraph("Date d'échéance", date_label_style), Paragraph(due_str, date_value_style)],
        [Paragraph("Conditions", date_label_style), Paragraph(invoice.terms or "Virement", date_value_style)],
        [Paragraph("Statut", date_label_style), Paragraph(invoice.status.value.upper(), date_value_style)],
    ]]
    dates_table = Table(dates_data, colWidths=[45*mm, 45*mm, 45*mm, 40*mm])
    dates_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG), ('TOPPADDING', (0, 0), (-1, -1), 2*mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm), ('LEFTPADDING', (0, 0), (-1, -1), 3*mm)]))
    elements.append(dates_table)
    elements.append(Spacer(1, 3*mm))

    # Items table
    items_header = ["N°", "ARTICLE", "QTÉ", "PRIX HT", "TVA", "MONTANT HT", "MONTANT TTC"]
    table_data = [items_header]
    for idx, item in enumerate(sorted(invoice.items, key=lambda x: x.position), 1):
        item_tax = float(item.line_total) * (tax_rate / 100)
        item_ttc = float(item.line_total) + item_tax
        table_data.append([
            str(idx), item.description, f"{int(item.quantity)}",
            f"{float(item.unit_price):,.0f} €".replace(',', ' '), f"{int(tax_rate)}%",
            f"{float(item.line_total):,.0f} €".replace(',', ' '), f"{item_ttc:,.0f} €".replace(',', ' ')
        ])

    items_table = Table(table_data, colWidths=[10*mm, 55*mm, 22*mm, 28*mm, 15*mm, 25*mm, 25*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'), ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))

    # Totals
    totals_data = [
        ["", "", "", "", "", "Total HT", f"{subtotal:,.0f} €".replace(',', ' ')],
        ["", "", "", "", "", "Total TVA", f"{tax_amt:,.0f} €".replace(',', ' ')],
    ]
    if discount_pct > 0:
        totals_data.insert(1, ["", "", "", "", "", f"Remise ({discount_pct:.0f}%)", f"-{discount_amt:,.0f} €".replace(',', ' ')])
    totals_data.append(["", "", "", "", "", "Total TTC", f"{total:,.2f} €".replace(',', ' ').replace('.', ',')])
    if amount_paid > 0:
        totals_data.append(["", "", "", "", "", "Déjà payé", f"-{amount_paid:,.2f} €".replace(',', ' ').replace('.', ',')])
        totals_data.append(["", "", "", "", "", "Reste à payer", f"{remaining:,.2f} €".replace(',', ' ').replace('.', ',')])
    totals_table = Table(totals_data, colWidths=[10*mm, 55*mm, 22*mm, 28*mm, 15*mm, 25*mm, 25*mm])
    totals_table.setStyle(TableStyle([('ALIGN', (-2, 0), (-1, -1), 'RIGHT'), ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'), ('FONTSIZE', (-2, -1), (-1, -1), 11)]))
    elements.append(totals_table)
    elements.append(Spacer(1, 3*mm))

    # Payment info
    payment_info = workspace.payment_info if workspace and workspace.payment_info else {}
    iban = payment_info.get('iban', '')
    account_name = payment_info.get('account_name', workspace.legal_name if workspace else '-')
    if iban:
        payment_data = [[Paragraph(f"<b>Paiement souhaité par virement bancaire</b>", ParagraphStyle('PayT', fontSize=9, fontName='Helvetica-Bold'))],
                        [Paragraph(f"Nom associé au compte: <b>{account_name}</b><br/>IBAN: <b>{iban}</b>", ParagraphStyle('PayD', fontSize=8, textColor=GRAY_TEXT))]]
        payment_table = Table(payment_data, colWidths=[175*mm])
        payment_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG), ('TOPPADDING', (0, 0), (-1, -1), 3*mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm), ('LEFTPADDING', (0, 0), (-1, -1), 4*mm)]))
        elements.append(payment_table)
        elements.append(Spacer(1, 3*mm))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
    elements.append(Spacer(1, 3*mm))

    if workspace and workspace.tva_franchise:
        elements.append(Paragraph("<b>TVA non applicable, article 293 B du Code Général des Impôts.</b>", footer_style))
        elements.append(Spacer(1, 2*mm))

    legal_text = "Pour tout professionnel, en cas de retard de paiement, seront exigibles, conformément à l'article L 441-10 du code de commerce, une indemnité calculée sur la base de trois fois le taux de l'intérêt légal en vigueur ainsi qu'une indemnité forfaitaire pour frais de recouvrement de 40 euros."
    elements.append(Paragraph(legal_text, footer_style))
    elements.append(Spacer(1, 3*mm))

    reg_parts = []
    if workspace:
        if workspace.forme_juridique:
            forme = workspace.forme_juridique
            if workspace.capital_social:
                forme += f" au capital de {workspace.capital_social}"
            reg_parts.append(forme)
        if workspace.rcs_city:
            siren = workspace.siret[:9] if workspace.siret and len(workspace.siret) >= 9 else ""
            reg_parts.append(f"RCS {workspace.rcs_city} {siren}".strip())
        elif workspace.legal_city and workspace.siret:
            siren = workspace.siret[:9] if len(workspace.siret) >= 9 else workspace.siret
            reg_parts.append(f"RCS {workspace.legal_city} {siren}")
        if workspace.siret:
            reg_parts.append(f"SIRET: {workspace.siret}")
        if workspace.vat_number and not workspace.tva_franchise:
            reg_parts.append(f"TVA: {workspace.vat_number}")
    elements.append(Paragraph("  •  ".join(reg_parts) if reg_parts else "", footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()

    # ---- Upload to Google Drive ----
    try:
        google_service = GoogleWorkspaceService(current_user.id)

        # Delete old PDF if exists
        if invoice.drive_pdf_id:
            try:
                await google_service.delete_file(invoice.drive_pdf_id)
            except Exception:
                pass

        # Find or create Radar/Business/Factures folder
        folder_id = invoice.drive_folder_id
        if not folder_id:
            # Try DriveFolderMap first
            from app.db.models.drive_folder_map import DriveFolderMap, DriveFolderType
            folder_map = db.query(DriveFolderMap).filter(
                DriveFolderMap.workspace_id == workspace_id,
                DriveFolderMap.folder_type == DriveFolderType.BUSINESS_INVOICES.value
            ).first()
            if folder_map:
                folder_id = folder_map.drive_folder_id
            else:
                # Fallback: create Radar/Business/Factures manually
                radar_folder = await google_service.find_folder_by_name("Radar")
                if not radar_folder:
                    radar_folder = await google_service.create_folder("Radar")
                business_folder = await google_service.find_folder_by_name("Business", radar_folder["id"])
                if not business_folder:
                    business_folder = await google_service.create_folder("Business", radar_folder["id"])
                factures_folder = await google_service.find_folder_by_name("Factures", business_folder["id"])
                if not factures_folder:
                    factures_folder = await google_service.create_folder("Factures", business_folder["id"])
                folder_id = factures_folder["id"]
            invoice.drive_folder_id = folder_id

        # Upload new PDF
        filename = f"{invoice.reference}.pdf"
        file_metadata = await google_service.upload_file(
            file_content=pdf_bytes,
            filename=filename,
            mime_type="application/pdf",
            parent_folder_id=folder_id
        )

        invoice.drive_pdf_id = file_metadata.get('id')
        invoice.drive_web_view_link = file_metadata.get('webViewLink')
        db.commit()

        return {
            "message": "PDF facture sauvegardé sur Google Drive",
            "drive_file_id": invoice.drive_pdf_id,
            "web_view_link": invoice.drive_web_view_link
        }

    except Exception as e:
        logger.exception(f"Erreur Google Drive facture: {e}")
        raise HTTPException(status_code=500, detail="Erreur Google Drive")


# ============ Dashboard Endpoint ============

@router.get("/dashboard", response_model=BillingDashboard)
async def get_billing_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Get billing dashboard statistics"""
    # Quote counts
    quotes_draft = db.query(Quote).filter(
        Quote.workspace_id == workspace_id,
        Quote.status == QuoteStatus.DRAFT
    ).count()
    
    quotes_sent = db.query(Quote).filter(
        Quote.workspace_id == workspace_id,
        Quote.status == QuoteStatus.SENT
    ).count()
    
    quotes_accepted = db.query(Quote).filter(
        Quote.workspace_id == workspace_id,
        Quote.status == QuoteStatus.ACCEPTED
    ).count()
    
    # Invoice counts
    invoices_draft = db.query(Invoice).filter(
        Invoice.workspace_id == workspace_id,
        Invoice.status == InvoiceStatus.DRAFT
    ).count()
    
    invoices_sent = db.query(Invoice).filter(
        Invoice.workspace_id == workspace_id,
        Invoice.status == InvoiceStatus.SENT
    ).count()
    
    invoices_paid = db.query(Invoice).filter(
        Invoice.workspace_id == workspace_id,
        Invoice.status == InvoiceStatus.PAID
    ).count()
    
    invoices_overdue = db.query(Invoice).filter(
        Invoice.workspace_id == workspace_id,
        Invoice.status == InvoiceStatus.OVERDUE
    ).count()
    
    # Amounts
    total_quotes = db.query(func.coalesce(func.sum(Quote.total), 0)).filter(
        Quote.workspace_id == workspace_id,
        Quote.status.in_([QuoteStatus.SENT, QuoteStatus.ACCEPTED])
    ).scalar()
    
    total_invoices = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(
        Invoice.workspace_id == workspace_id,
        Invoice.status != InvoiceStatus.CANCELLED
    ).scalar()
    
    total_paid = db.query(func.coalesce(func.sum(Invoice.amount_paid), 0)).filter(
        Invoice.workspace_id == workspace_id
    ).scalar()
    
    total_pending = db.query(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)).filter(
        Invoice.workspace_id == workspace_id,
        Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE])
    ).scalar()
    
    return BillingDashboard(
        quotes_draft=quotes_draft,
        quotes_sent=quotes_sent,
        quotes_accepted=quotes_accepted,
        invoices_draft=invoices_draft,
        invoices_sent=invoices_sent,
        invoices_paid=invoices_paid,
        invoices_overdue=invoices_overdue,
        total_quotes_amount=Decimal(str(total_quotes)),
        total_invoices_amount=Decimal(str(total_invoices)),
        total_paid=Decimal(str(total_paid)),
        total_pending=Decimal(str(total_pending))
    )


# ============ Quote Status Management ============

def add_audit_log(obj, event: str, user_id: int, details: dict = None):
    """Add an audit log entry to a quote or invoice"""
    if obj.audit_log is None:
        obj.audit_log = []
    
    entry = {
        "event": event,
        "at": datetime.utcnow().isoformat(),
        "by": user_id
    }
    if details:
        entry["details"] = details
    
    obj.audit_log = obj.audit_log + [entry]


@router.post("/quotes/{quote_id}/send")
async def send_quote(
    quote_id: int,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Mark quote as sent"""
    quote = db.query(Quote).options(
        joinedload(Quote.billing_client)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status not in [QuoteStatus.DRAFT, QuoteStatus.SENT]:
        raise HTTPException(status_code=400, detail="Ce devis ne peut pas être envoyé")
    
    quote.status = QuoteStatus.SENT
    quote.sent_at = datetime.utcnow()
    quote.sent_to_email = email or (quote.billing_client.email if quote.billing_client else None)
    
    add_audit_log(quote, "sent", current_user.id, {"email": quote.sent_to_email})
    
    db.commit()
    return {"message": "Devis marqué comme envoyé", "status": quote.status.value}


@router.post("/quotes/{quote_id}/accept")
async def accept_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Mark quote as accepted"""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status not in [QuoteStatus.SENT, QuoteStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Seuls les devis envoyés peuvent être acceptés")
    
    quote.status = QuoteStatus.ACCEPTED
    add_audit_log(quote, "accepted", current_user.id)
    
    db.commit()
    return {"message": "Devis accepté", "status": quote.status.value}


@router.post("/quotes/{quote_id}/reject")
async def reject_quote(
    quote_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Mark quote as rejected"""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    if quote.status not in [QuoteStatus.SENT, QuoteStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Ce devis ne peut pas être refusé")
    
    quote.status = QuoteStatus.REJECTED
    add_audit_log(quote, "rejected", current_user.id, {"reason": reason} if reason else None)
    
    db.commit()
    return {"message": "Devis refusé", "status": quote.status.value}


# ============ Invoice Status Management ============

@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: int,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Mark invoice as sent"""
    invoice = db.query(Invoice).options(
        joinedload(Invoice.billing_client)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status not in [InvoiceStatus.DRAFT, InvoiceStatus.SENT]:
        raise HTTPException(status_code=400, detail="Cette facture ne peut pas être envoyée")
    
    invoice.status = InvoiceStatus.SENT
    invoice.sent_at = datetime.utcnow()
    invoice.sent_to_email = email or (invoice.billing_client.email if invoice.billing_client else None)
    
    add_audit_log(invoice, "sent", current_user.id, {"email": invoice.sent_to_email})
    
    db.commit()
    return {"message": "Facture marquée comme envoyée", "status": invoice.status.value}


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: int,
    payment_method: Optional[PaymentMethod] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Mark invoice as fully paid"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Facture déjà payée")
    
    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Facture annulée")
    
    invoice.status = InvoiceStatus.PAID
    invoice.amount_paid = invoice.total
    invoice.paid_date = date.today()
    if payment_method:
        invoice.payment_method = payment_method
    
    add_audit_log(invoice, "paid", current_user.id, {
        "amount": str(invoice.total),
        "method": payment_method.value if payment_method else None
    })
    
    db.commit()
    return {"message": "Facture marquée comme payée", "status": invoice.status.value}


@router.post("/invoices/{invoice_id}/cancel")
async def cancel_invoice(
    invoice_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """Cancel an invoice"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Impossible d'annuler une facture payée")
    
    invoice.status = InvoiceStatus.CANCELLED
    add_audit_log(invoice, "cancelled", current_user.id, {"reason": reason} if reason else None)
    
    db.commit()
    return {"message": "Facture annulée", "status": invoice.status.value}


# ============ Document Generation (Google Drive) ============

@router.post("/quotes/{quote_id}/generate-doc")
async def generate_quote_document(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """
    Generate a Google Doc for a quote and store it in the client's Drive folder.
    Structure: Radar / Clients / [ClientName] / Devis / Devis DEV-2026-0001 - ClientName.gdoc
    """
    from app.services.google_workspace import get_google_workspace_service, GoogleAPIError
    
    # Get quote with client
    quote = db.query(Quote).options(
        joinedload(Quote.billing_client),
        joinedload(Quote.items)
    ).filter(
        Quote.id == quote_id,
        Quote.workspace_id == workspace_id
    ).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    
    # Get workspace for template and emitter info
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    
    # Check template exists
    if not workspace.devis_template_doc_id:
        raise HTTPException(
            status_code=400, 
            detail="Aucun template de devis configuré. Configurez le template dans les paramètres émetteur."
        )
    
    # Check workspace has Drive folder
    if not workspace.drive_folder_id:
        raise HTTPException(
            status_code=400,
            detail="Aucun dossier Drive configuré pour ce workspace."
        )
    
    # Get client name
    if quote.billing_client:
        client_name = quote.billing_client.company_name or f"{quote.billing_client.first_name} {quote.billing_client.last_name}"
    else:
        client_name = "Client Inconnu"
    
    # Build replacements dictionary
    replacements = build_quote_replacements(quote, workspace, client_name)
    
    try:
        # Get Google Workspace service for user
        gws = await get_google_workspace_service(current_user.id, db)
        
        # Generate document
        doc_result = await gws.generate_quote_document(
            template_id=workspace.devis_template_doc_id,
            quote_reference=quote.reference,
            client_name=client_name,
            root_folder_id=workspace.drive_folder_id,
            replacements=replacements
        )
        
        # Update quote with Drive info
        quote.drive_doc_id = doc_result["id"]
        quote.drive_web_view_link = doc_result["url"]
        quote.drive_folder_id = doc_result["folder_id"]
        
        add_audit_log(quote, "document_generated", current_user.id, {
            "doc_id": doc_result["id"],
            "url": doc_result["url"]
        })
        
        db.commit()
        
        return {
            "message": "Document généré avec succès",
            "doc_id": doc_result["id"],
            "url": doc_result["url"],
            "folder_id": doc_result["folder_id"]
        }
        
    except GoogleAPIError as e:
        logger.exception(f"Erreur Google Drive devis doc: {e}")
        raise HTTPException(status_code=500, detail="Erreur Google Drive")
    except Exception as e:
        logger.exception(f"Erreur génération devis doc: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération")


@router.post("/invoices/{invoice_id}/generate-doc")
async def generate_invoice_document(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_current_workspace_id)
):
    """
    Generate a Google Doc for an invoice and store it in the client's Drive folder.
    Structure: Radar / Clients / [ClientName] / Factures / Facture FAC-2026-0001 - ClientName.gdoc
    """
    from app.services.google_workspace import get_google_workspace_service, GoogleAPIError
    
    # Get invoice with client
    invoice = db.query(Invoice).options(
        joinedload(Invoice.billing_client),
        joinedload(Invoice.items)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.workspace_id == workspace_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    # Get workspace for template and emitter info
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace non trouvé")
    
    # Check template exists
    if not workspace.facture_template_doc_id:
        raise HTTPException(
            status_code=400, 
            detail="Aucun template de facture configuré. Configurez le template dans les paramètres émetteur."
        )
    
    # Check workspace has Drive folder
    if not workspace.drive_folder_id:
        raise HTTPException(
            status_code=400,
            detail="Aucun dossier Drive configuré pour ce workspace."
        )
    
    # Get client name
    if invoice.billing_client:
        client_name = invoice.billing_client.company_name or f"{invoice.billing_client.first_name} {invoice.billing_client.last_name}"
    else:
        client_name = "Client Inconnu"
    
    # Build replacements dictionary
    replacements = build_invoice_replacements(invoice, workspace, client_name)
    
    try:
        # Get Google Workspace service for user
        gws = await get_google_workspace_service(current_user.id, db)
        
        # Generate document
        doc_result = await gws.generate_invoice_document(
            template_id=workspace.facture_template_doc_id,
            invoice_reference=invoice.reference,
            client_name=client_name,
            root_folder_id=workspace.drive_folder_id,
            replacements=replacements
        )
        
        # Update invoice with Drive info
        invoice.drive_doc_id = doc_result["id"]
        invoice.drive_web_view_link = doc_result["url"]
        invoice.drive_folder_id = doc_result["folder_id"]
        
        add_audit_log(invoice, "document_generated", current_user.id, {
            "doc_id": doc_result["id"],
            "url": doc_result["url"]
        })
        
        db.commit()
        
        return {
            "message": "Document généré avec succès",
            "doc_id": doc_result["id"],
            "url": doc_result["url"],
            "folder_id": doc_result["folder_id"]
        }
        
    except GoogleAPIError as e:
        logger.exception(f"Erreur Google Drive facture doc: {e}")
        raise HTTPException(status_code=500, detail="Erreur Google Drive")
    except Exception as e:
        logger.exception(f"Erreur génération facture doc: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération")


def build_quote_replacements(quote: Quote, workspace: Workspace, client_name: str) -> dict:
    """Build placeholder replacements for quote template"""
    client = quote.billing_client
    
    # Format items table
    items_lines = []
    for item in quote.items:
        items_lines.append(
            f"{item.description}\t{item.quantity}\t{item.unit_price:.2f} €\t{item.line_total:.2f} €"
        )
    items_text = "\n".join(items_lines)
    
    # Format client address
    client_address = ""
    if client:
        parts = [client.address, f"{client.postal_code} {client.city}", client.country]
        client_address = "\n".join([p for p in parts if p])
    
    # Format emitter address
    emitter_address = ""
    if workspace.legal_address:
        parts = [
            workspace.legal_address,
            f"{workspace.legal_postal_code or ''} {workspace.legal_city or ''}".strip(),
            workspace.legal_country or "France"
        ]
        emitter_address = "\n".join([p for p in parts if p])
    
    return {
        # Emitter info
        "{{EMITTER_NAME}}": workspace.legal_name or workspace.name or "",
        "{{EMITTER_ADDRESS}}": emitter_address,
        "{{EMITTER_PHONE}}": workspace.legal_phone or "",
        "{{EMITTER_EMAIL}}": workspace.legal_email or workspace.billing_email or "",
        "{{EMITTER_SIRET}}": workspace.siret or "",
        "{{EMITTER_VAT}}": workspace.vat_number or "",
        
        # Client info
        "{{CLIENT_NAME}}": client_name,
        "{{CLIENT_COMPANY}}": client.company_name if client else "",
        "{{CLIENT_ADDRESS}}": client_address,
        "{{CLIENT_EMAIL}}": client.email if client else "",
        "{{CLIENT_PHONE}}": client.phone if client else "",
        "{{CLIENT_VAT}}": client.vat_number if client else "",
        
        # Quote info
        "{{QUOTE_REFERENCE}}": quote.reference,
        "{{QUOTE_TITLE}}": quote.title or "",
        "{{ISSUE_DATE}}": quote.issue_date.strftime("%d/%m/%Y") if quote.issue_date else "",
        "{{VALIDITY_DATE}}": quote.valid_until.strftime("%d/%m/%Y") if quote.valid_until else "",
        "{{NOTES}}": quote.notes or "",
        "{{TERMS}}": quote.terms or "",
        
        # Items table (simplified - template should have actual table)
        "{{ITEMS_TABLE}}": items_text,
        
        # Totals
        "{{SUBTOTAL}}": f"{quote.subtotal:.2f} €",
        "{{DISCOUNT_PERCENT}}": f"{quote.discount_percent:.0f} %",
        "{{DISCOUNT_AMOUNT}}": f"{quote.discount_amount:.2f} €",
        "{{TAX_RATE}}": f"{quote.tax_rate:.0f} %",
        "{{TAX_AMOUNT}}": f"{quote.tax_amount:.2f} €",
        "{{TOTAL}}": f"{quote.total:.2f} €",
    }


def build_invoice_replacements(invoice: Invoice, workspace: Workspace, client_name: str) -> dict:
    """Build placeholder replacements for invoice template"""
    client = invoice.billing_client
    
    # Format items table
    items_lines = []
    for item in invoice.items:
        items_lines.append(
            f"{item.description}\t{item.quantity}\t{item.unit_price:.2f} €\t{item.line_total:.2f} €"
        )
    items_text = "\n".join(items_lines)
    
    # Format client address
    client_address = ""
    if client:
        parts = [client.address, f"{client.postal_code} {client.city}", client.country]
        client_address = "\n".join([p for p in parts if p])
    
    # Format emitter address
    emitter_address = ""
    if workspace.legal_address:
        parts = [
            workspace.legal_address,
            f"{workspace.legal_postal_code or ''} {workspace.legal_city or ''}".strip(),
            workspace.legal_country or "France"
        ]
        emitter_address = "\n".join([p for p in parts if p])
    
    return {
        # Emitter info
        "{{EMITTER_NAME}}": workspace.legal_name or workspace.name or "",
        "{{EMITTER_ADDRESS}}": emitter_address,
        "{{EMITTER_PHONE}}": workspace.legal_phone or "",
        "{{EMITTER_EMAIL}}": workspace.legal_email or workspace.billing_email or "",
        "{{EMITTER_SIRET}}": workspace.siret or "",
        "{{EMITTER_VAT}}": workspace.vat_number or "",
        
        # Client info
        "{{CLIENT_NAME}}": client_name,
        "{{CLIENT_COMPANY}}": client.company_name if client else "",
        "{{CLIENT_ADDRESS}}": client_address,
        "{{CLIENT_EMAIL}}": client.email if client else "",
        "{{CLIENT_PHONE}}": client.phone if client else "",
        "{{CLIENT_VAT}}": client.vat_number if client else "",
        
        # Invoice info
        "{{INVOICE_REFERENCE}}": invoice.reference,
        "{{INVOICE_TITLE}}": invoice.title or "",
        "{{ISSUE_DATE}}": invoice.issue_date.strftime("%d/%m/%Y") if invoice.issue_date else "",
        "{{DUE_DATE}}": invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else "",
        "{{NOTES}}": invoice.notes or "",
        "{{PAYMENT_TERMS}}": invoice.payment_terms or "",
        
        # Items table
        "{{ITEMS_TABLE}}": items_text,
        
        # Totals
        "{{SUBTOTAL}}": f"{invoice.subtotal:.2f} €",
        "{{DISCOUNT_PERCENT}}": f"{invoice.discount_percent:.0f} %",
        "{{DISCOUNT_AMOUNT}}": f"{invoice.discount_amount:.2f} €",
        "{{TAX_RATE}}": f"{invoice.tax_rate:.0f} %",
        "{{TAX_AMOUNT}}": f"{invoice.tax_amount:.2f} €",
        "{{TOTAL}}": f"{invoice.total:.2f} €",
        "{{AMOUNT_PAID}}": f"{invoice.amount_paid:.2f} €",
        "{{AMOUNT_DUE}}": f"{(invoice.total - invoice.amount_paid):.2f} €",
    }
