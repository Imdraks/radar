"""
Schemas for Entity, Brief, Contact, Collection system
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    TOPIC = "TOPIC"


class ObjectiveType(str, Enum):
    SPONSOR = "SPONSOR"
    BOOKING = "BOOKING"
    PRESS = "PRESS"
    VENUE = "VENUE"
    SUPPLIER = "SUPPLIER"
    GRANT = "GRANT"


class ContactType(str, Enum):
    EMAIL = "EMAIL"
    FORM = "FORM"
    BOOKING = "BOOKING"
    PRESS = "PRESS"
    AGENT = "AGENT"
    MANAGEMENT = "MANAGEMENT"
    SOCIAL = "SOCIAL"
    PHONE = "PHONE"


# ========================
# COLLECTION REQUEST
# ========================

class EntityInput(BaseModel):
    """Entity to search for"""
    name: str = Field(..., min_length=1, max_length=255)
    type: EntityType = EntityType.PERSON


class CollectRequest(BaseModel):
    """Request body for POST /collect"""
    objective: ObjectiveType
    entities: List[EntityInput] = Field(..., min_length=1, max_length=10)
    secondary_keywords: Optional[List[str]] = Field(default=[], max_length=20)
    
    # Filters
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    region: Optional[str] = None
    city: Optional[str] = None
    
    # Options
    timeframe_days: int = Field(default=30, ge=7, le=365)
    require_contact: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "objective": "BOOKING",
                "entities": [
                    {"name": "Théodora", "type": "PERSON"},
                    {"name": "Nayra", "type": "PERSON"}
                ],
                "secondary_keywords": ["rap", "concerts", "France"],
                "timeframe_days": 30,
                "require_contact": True
            }
        }


class CollectResponse(BaseModel):
    """Response from POST /collect"""
    run_id: UUID
    source_count: int
    task_ids: List[str]
    entities_created: List[UUID]
    message: str


# ========================
# COLLECTION RUN STATUS
# ========================

class SourceRunStatus(BaseModel):
    """Status of a single source run"""
    source_id: Optional[UUID]
    source_name: str
    status: str
    items_found: int = 0
    items_new: int = 0
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class CollectionRunResponse(BaseModel):
    """Response from GET /runs/{run_id}"""
    id: UUID
    status: str
    objective: ObjectiveType
    
    # Timing
    started_at: datetime
    finished_at: Optional[datetime]
    
    # Stats
    source_count: int
    sources_success: int
    sources_failed: int
    documents_new: int
    documents_updated: int
    documents_fetched: int = 0  # Alias for frontend compatibility
    contacts_found: int
    
    # Generated brief
    brief_id: Optional[UUID] = None
    error_message: Optional[str] = None
    
    # Details
    entities_requested: List[Dict[str, Any]]
    source_runs: List[SourceRunStatus]
    error_summary: Optional[str]


# ========================
# ENTITY
# ========================

class EntityBase(BaseModel):
    name: str
    entity_type: EntityType
    aliases: List[str] = []
    description: Optional[str] = None


class EntityCreate(EntityBase):
    pass


class EntityResponse(EntityBase):
    id: UUID
    normalized_name: str
    official_urls: List[Dict[str, str]] = []
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Stats
    document_count: Optional[int] = 0
    contact_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ========================
# CONTACT
# ========================

class ContactBase(BaseModel):
    contact_type: ContactType
    value: str
    label: Optional[str] = None


class ContactResponse(ContactBase):
    id: UUID
    entity_id: UUID
    source_url: Optional[str]
    source_name: Optional[str]
    reliability_score: int
    is_verified: bool
    first_seen_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class ContactRanked(BaseModel):
    """Contact with ranking info for brief"""
    type: str
    value: str
    label: Optional[str]
    reliability_score: float  # Changed to float to support 0-1 and 0-100 scores
    source: Optional[str]
    is_verified: bool = False


# ========================
# DOCUMENT
# ========================

class DocumentResponse(BaseModel):
    id: UUID
    entity_id: UUID
    source_name: str
    title: str
    url: Optional[str]
    snippet: Optional[str]
    published_at: Optional[datetime]
    fetched_at: datetime
    is_processed: bool

    class Config:
        from_attributes = True


# ========================
# BRIEF
# ========================

class TimelineEvent(BaseModel):
    """Event in brief timeline"""
    date: Optional[str]
    event_type: str
    description: str
    source: Optional[str]


class UsefulFact(BaseModel):
    """Fact extracted for brief"""
    fact: str
    source: Optional[str]
    category: Optional[str]


class SourceUsed(BaseModel):
    """Source info in brief"""
    name: str
    url: Optional[str]
    document_count: int


class BriefResponse(BaseModel):
    """Complete brief for an entity"""
    id: UUID
    entity_id: UUID
    entity_name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    
    objective: ObjectiveType
    timeframe_days: int
    
    # Content
    overview: Optional[str]
    contacts_ranked: List[ContactRanked] = []
    useful_facts: List[UsefulFact] = []
    timeline: List[TimelineEvent] = []
    sources_used: List[SourceUsed] = []
    
    # Quality
    document_count: int
    contact_count: int
    completeness_score: float
    
    generated_at: datetime

    class Config:
        from_attributes = True


# ========================
# OPPORTUNITY ENHANCED
# ========================

class OpportunityEnhanced(BaseModel):
    """Opportunity with brief data"""
    id: UUID
    title: str
    source_name: str
    category: Optional[str]
    status: str
    score: Optional[int]
    
    # Enhanced fields
    entity_id: Optional[UUID] = None
    brief_id: Optional[UUID] = None
    has_contacts: bool = False
    top_contact: Optional[ContactRanked] = None
    
    # Standard fields
    url_primary: Optional[str]
    published_at: Optional[datetime]
    deadline_at: Optional[datetime]
    organization: Optional[str]
    location_region: Optional[str]

    class Config:
        from_attributes = True
