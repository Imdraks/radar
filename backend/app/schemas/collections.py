"""
Schemas Pydantic pour le système de collectes refondé
- Collections API
- Opportunities API (lead_items)
- Dossiers API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator


# ================================================================
# ENUMS
# ================================================================

class CollectionTypeEnum(str, Enum):
    STANDARD = "STANDARD"
    AI = "AI"


class CollectionStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class LeadItemStatusEnum(str, Enum):
    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    CONTACTED = "CONTACTED"
    WON = "WON"
    LOST = "LOST"
    ARCHIVED = "ARCHIVED"


class DossierObjectiveEnum(str, Enum):
    SPONSOR = "SPONSOR"
    BOOKING = "BOOKING"
    PRESS = "PRESS"
    VENUE = "VENUE"
    SUPPLIER = "SUPPLIER"
    GRANT = "GRANT"


class DossierStateEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


# ================================================================
# COLLECTIONS SCHEMAS
# ================================================================

class StandardCollectionParams(BaseModel):
    """Paramètres pour collecte standard"""
    keywords: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    source_ids: Optional[List[str]] = None


class AICollectionParams(BaseModel):
    """Paramètres pour collecte IA"""
    objective: DossierObjectiveEnum
    entities: List[Dict[str, str]] = Field(..., min_items=1)  # [{name, type}]
    secondary_keywords: Optional[List[str]] = []
    timeframe_days: int = Field(30, ge=7, le=365)
    require_contact: bool = False
    region: Optional[str] = None
    city: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class CreateCollectionRequest(BaseModel):
    """Requête pour créer une collecte"""
    type: CollectionTypeEnum
    name: Optional[str] = None
    params: Dict[str, Any]  # StandardCollectionParams ou AICollectionParams

    @validator('params')
    def validate_params(cls, v, values):
        collection_type = values.get('type')
        if collection_type == CollectionTypeEnum.STANDARD:
            StandardCollectionParams(**v)
        elif collection_type == CollectionTypeEnum.AI:
            AICollectionParams(**v)
        return v


class CollectionStatsSchema(BaseModel):
    """Stats d'une collecte"""
    pages_fetched: int = 0
    results_count: int = 0
    results_new: int = 0
    errors_count: int = 0
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None


class CollectionLogSchema(BaseModel):
    """Log d'une collecte"""
    id: UUID
    ts: datetime
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    """Réponse collecte"""
    id: UUID
    type: str
    status: str
    name: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    stats: Optional[CollectionStatsSchema] = None
    error: Optional[str] = None
    created_at: datetime
    results_count: int = 0

    class Config:
        from_attributes = True


class CollectionDetailResponse(CollectionResponse):
    """Détail complet d'une collecte"""
    logs: List[CollectionLogSchema] = []
    sources_consulted: List[str] = []


class CollectionListResponse(BaseModel):
    """Liste paginée des collectes"""
    items: List[CollectionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ================================================================
# OPPORTUNITIES (LEAD_ITEMS) SCHEMAS
# ================================================================

class EvidenceSchema(BaseModel):
    """Evidence d'un champ"""
    field_key: str
    value: Optional[str] = None
    source_url: Optional[str] = None
    snippet: Optional[str] = None
    confidence: int = 100
    provenance: str

    class Config:
        from_attributes = True


class SourceDocumentSchema(BaseModel):
    """Document source"""
    id: UUID
    doc_type: str
    source_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OpportunityResponse(BaseModel):
    """Réponse opportunité"""
    id: UUID
    title: str
    description: Optional[str] = None
    organization_name: Optional[str] = None
    url_primary: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    published_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    budget_display: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_url: Optional[str] = None
    contact_name: Optional[str] = None
    has_contact: bool = False
    has_deadline: bool = False
    score_base: int = 0
    score_breakdown: Optional[Dict[str, Any]] = None
    status: str
    tags: Optional[List[str]] = None
    assigned_to: Optional[UUID] = None
    has_dossier: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpportunityDetailResponse(OpportunityResponse):
    """Détail complet d'une opportunité"""
    evidence: List[EvidenceSchema] = []
    source_documents: List[SourceDocumentSchema] = []
    metadata: Optional[Dict[str, Any]] = None


class OpportunityListResponse(BaseModel):
    """Liste paginée des opportunités"""
    items: List[OpportunityResponse]
    total: int
    page: int
    page_size: int
    pages: int
    # Stats pour filtres
    score_distribution: Optional[Dict[str, int]] = None  # {0-20: 5, 20-40: 10, ...}
    budget_distribution: Optional[Dict[str, int]] = None
    status_counts: Optional[Dict[str, int]] = None


class OpportunityFilters(BaseModel):
    """Filtres pour opportunités"""
    search: Optional[str] = None
    status: Optional[List[LeadItemStatusEnum]] = None
    score_min: Optional[int] = Field(None, ge=0, le=100)
    score_max: Optional[int] = Field(None, ge=0, le=100)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    deadline_from: Optional[datetime] = None
    deadline_to: Optional[datetime] = None
    region: Optional[str] = None
    city: Optional[str] = None
    source_name: Optional[str] = None
    has_contact: Optional[bool] = None
    has_deadline: Optional[bool] = None
    has_dossier: Optional[bool] = None
    tags: Optional[List[str]] = None
    assigned_to: Optional[UUID] = None


class UpdateOpportunityRequest(BaseModel):
    """Mise à jour d'une opportunité"""
    status: Optional[LeadItemStatusEnum] = None
    tags: Optional[List[str]] = None
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None


class BulkUpdateOpportunitiesRequest(BaseModel):
    """Mise à jour en masse"""
    ids: List[UUID]
    status: Optional[LeadItemStatusEnum] = None
    tags_add: Optional[List[str]] = None
    tags_remove: Optional[List[str]] = None
    assigned_to: Optional[UUID] = None


# ================================================================
# DOSSIERS SCHEMAS
# ================================================================

class ContactRankedSchema(BaseModel):
    """Contact classé"""
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    relevance_score: int = 0
    source_url: Optional[str] = None


class TimelineEventSchema(BaseModel):
    """Événement timeline"""
    date: Optional[datetime] = None
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None


class FactSchema(BaseModel):
    """Fait utile"""
    category: str
    content: str
    source_url: Optional[str] = None
    snippet: Optional[str] = None


class DossierResponse(BaseModel):
    """Réponse dossier"""
    id: UUID
    lead_item_id: UUID
    lead_item_title: Optional[str] = None
    lead_item_url: Optional[str] = None
    objective: str
    target_entities: Optional[List[Dict[str, Any]]] = None
    state: str
    quality_score: Optional[int] = None
    error_message: Optional[str] = None
    evidence_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DossierDetailResponse(BaseModel):
    """Détail complet d'un dossier"""
    id: UUID
    lead_item_id: UUID
    lead_item_title: Optional[str] = None
    lead_item_url: Optional[str] = None
    objective: str
    target_entities: Optional[List[Dict[str, Any]]] = None
    state: str
    sections: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    key_findings: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    quality_score: Optional[int] = None
    quality_breakdown: Optional[Dict[str, Any]] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidence: List[EvidenceSchema] = []
    source_documents: List[SourceDocumentSchema] = []

    class Config:
        from_attributes = True


class DossierListResponse(BaseModel):
    """Liste paginée des dossiers"""
    items: List[DossierResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DossierFilters(BaseModel):
    """Filtres pour dossiers"""
    search: Optional[str] = None
    objective: Optional[List[DossierObjectiveEnum]] = None
    state: Optional[List[DossierStateEnum]] = None
    score_quality_min: Optional[int] = Field(None, ge=0, le=100)
    confidence_min: Optional[int] = Field(None, ge=0, le=100)


class CreateDossierRequest(BaseModel):
    """Créer un dossier depuis une opportunité"""
    lead_item_id: Optional[UUID] = None
    objective: DossierObjectiveEnum
    target_entities: Optional[List[str]] = None
    title: Optional[str] = None
    source_url: Optional[str] = None
    source_text: Optional[str] = None


class DossierUpdateRequest(BaseModel):
    """Mise à jour d'un dossier"""
    target_entities: Optional[List[str]] = None
    sections: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    key_findings: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
