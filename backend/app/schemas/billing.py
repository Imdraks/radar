"""
Billing schemas for quotes (devis) and invoices (factures)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator

from app.db.models.billing import QuoteStatus, InvoiceStatus, PaymentMethod


# ============ Client Schemas ============

class ClientBase(BaseModel):
    """Base client schema"""
    name: str = Field(..., max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Contact person
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_role: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "France"
    
    # Business info
    company_name: Optional[str] = None
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    
    # Banking (IBAN is handled separately for security)
    bic: Optional[str] = None
    bank_name: Optional[str] = None
    
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    """Create client schema"""
    pass


class ClientUpdate(BaseModel):
    """Update client schema"""
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Contact person
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_role: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Business info
    company_name: Optional[str] = None
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    
    # Banking (IBAN is handled separately for security)
    bic: Optional[str] = None
    bank_name: Optional[str] = None
    
    notes: Optional[str] = None


class ClientResponse(ClientBase):
    """Client response schema"""
    id: int
    crm_client_id: Optional[int] = None
    iban_masked: Optional[str] = None  # Only masked version for display
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientSetIBAN(BaseModel):
    """Schema for setting client IBAN (secure endpoint)"""
    iban: str = Field(..., min_length=15, max_length=34)


# ============ Quote Item Schemas ============

class QuoteItemBase(BaseModel):
    """Base quote item schema"""
    description: str = Field(..., max_length=500)
    quantity: Decimal = Decimal("1")
    unit: str = "unité"
    unit_price: Decimal


class QuoteItemCreate(QuoteItemBase):
    """Create quote item schema"""
    position: int = 0


class QuoteItemResponse(QuoteItemBase):
    """Quote item response schema"""
    id: int
    position: int
    line_total: Decimal

    class Config:
        from_attributes = True


# ============ Quote Schemas ============

class QuoteBase(BaseModel):
    """Base quote schema"""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    issue_date: date = Field(default_factory=date.today)
    validity_date: Optional[date] = None
    tax_rate: Decimal = Decimal("20.00")
    discount_percent: Decimal = Decimal("0")
    terms: Optional[str] = None
    notes: Optional[str] = None


class QuoteCreate(QuoteBase):
    """Create quote schema"""
    client_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    items: List[QuoteItemCreate] = Field(default_factory=list)


class QuoteUpdate(BaseModel):
    """Update quote schema"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    client_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    issue_date: Optional[date] = None
    validity_date: Optional[date] = None
    tax_rate: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[QuoteStatus] = None


class QuoteResponse(QuoteBase):
    """Quote response schema"""
    id: int
    workspace_id: int
    reference: str
    client_id: Optional[int]
    opportunity_id: Optional[int]
    status: QuoteStatus
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    invoice_id: Optional[int]
    # Drive integration
    drive_doc_id: Optional[str] = None
    drive_pdf_id: Optional[str] = None
    drive_web_view_link: Optional[str] = None
    drive_folder_id: Optional[str] = None
    # Audit
    audit_log: Optional[List[dict]] = []
    sent_at: Optional[datetime] = None
    sent_to_email: Optional[str] = None
    # Metadata
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    items: List[QuoteItemResponse] = []
    client: Optional[ClientResponse] = None

    @model_validator(mode='before')
    @classmethod
    def map_billing_client(cls, data):
        if hasattr(data, 'billing_client') and not hasattr(data, 'client'):
            data.__dict__['client'] = data.billing_client
        elif hasattr(data, '__dict__') and 'billing_client' in data.__dict__ and 'client' not in data.__dict__:
            data.__dict__['client'] = data.__dict__['billing_client']
        return data

    class Config:
        from_attributes = True


class QuoteListResponse(BaseModel):
    """Paginated quote list"""
    items: List[QuoteResponse]
    total: int
    page: int
    size: int


# ============ Invoice Item Schemas ============

class InvoiceItemBase(BaseModel):
    """Base invoice item schema"""
    description: str = Field(..., max_length=500)
    quantity: Decimal = Field(Decimal("1"), gt=0)
    unit: str = "unité"
    unit_price: Decimal = Field(..., ge=0)


class InvoiceItemCreate(InvoiceItemBase):
    """Create invoice item schema"""
    position: int = 0


class InvoiceItemResponse(InvoiceItemBase):
    """Invoice item response schema"""
    id: int
    position: int
    line_total: Decimal

    class Config:
        from_attributes = True


# ============ Invoice Schemas ============

class InvoiceBase(BaseModel):
    """Base invoice schema"""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    issue_date: date = Field(default_factory=date.today)
    due_date: Optional[date] = None
    tax_rate: Decimal = Decimal("20.00")
    discount_percent: Decimal = Decimal("0")
    terms: Optional[str] = None
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Create invoice schema"""
    client_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    items: List[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    """Update invoice schema"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    client_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    tax_rate: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class InvoicePaymentUpdate(BaseModel):
    """Update payment info"""
    amount_paid: Decimal = Field(ge=0)
    payment_method: Optional[PaymentMethod] = None
    paid_date: Optional[date] = None


class InvoiceResponse(InvoiceBase):
    """Invoice response schema"""
    id: int
    workspace_id: int
    reference: str
    client_id: Optional[int]
    opportunity_id: Optional[int]
    source_quote_id: Optional[int]
    status: InvoiceStatus
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    payment_method: Optional[PaymentMethod]
    paid_date: Optional[date]
    # Drive integration
    drive_doc_id: Optional[str] = None
    drive_pdf_id: Optional[str] = None
    drive_web_view_link: Optional[str] = None
    drive_folder_id: Optional[str] = None
    # Audit
    audit_log: Optional[List[dict]] = []
    sent_at: Optional[datetime] = None
    sent_to_email: Optional[str] = None
    # Metadata
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItemResponse] = []
    client: Optional[ClientResponse] = None

    @model_validator(mode='before')
    @classmethod
    def map_billing_client(cls, data):
        if hasattr(data, 'billing_client') and not hasattr(data, 'client'):
            data.__dict__['client'] = data.billing_client
        elif hasattr(data, '__dict__') and 'billing_client' in data.__dict__ and 'client' not in data.__dict__:
            data.__dict__['client'] = data.__dict__['billing_client']
        return data

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """Paginated invoice list"""
    items: List[InvoiceResponse]
    total: int
    page: int
    size: int


# ============ Conversion Schemas ============

class QuoteToInvoiceCreate(BaseModel):
    """Convert quote to invoice"""
    due_date: Optional[date] = None
    notes: Optional[str] = None


# ============ Dashboard Schemas ============

class BillingDashboard(BaseModel):
    """Billing dashboard stats"""
    quotes_draft: int
    quotes_sent: int
    quotes_accepted: int
    invoices_draft: int
    invoices_sent: int
    invoices_paid: int
    invoices_overdue: int
    total_quotes_amount: Decimal
    total_invoices_amount: Decimal
    total_paid: Decimal
    total_pending: Decimal
