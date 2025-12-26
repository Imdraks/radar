"""
Entity, Document, Extract, Brief, Contact models for enriched collection system
"""
import uuid
import hashlib
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Enum, ForeignKey,
    Integer, Numeric, JSON, Index, UniqueConstraint, Float
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class EntityType(str, PyEnum):
    """Type of entity being tracked"""
    PERSON = "PERSON"           # Artiste, personnalité, contact
    ORGANIZATION = "ORGANIZATION"  # Entreprise, label, festival, salle
    TOPIC = "TOPIC"             # Sujet, événement, thématique


class ObjectiveType(str, PyEnum):
    """Collection objective types"""
    SPONSOR = "SPONSOR"              # Sponsor/partenariat
    BOOKING = "BOOKING"              # Booking artiste
    PRESS = "PRESS"                  # Presse/média
    VENUE = "VENUE"                  # Lieu/salle
    SUPPLIER = "SUPPLIER"            # Prestataires (son, sécu, vidéo…)
    GRANT = "GRANT"                  # Subventions/appels à projets


class ContactType(str, PyEnum):
    """Types of contact information"""
    EMAIL = "EMAIL"
    FORM = "FORM"
    BOOKING = "BOOKING"
    PRESS = "PRESS"
    AGENT = "AGENT"
    MANAGEMENT = "MANAGEMENT"
    SOCIAL = "SOCIAL"
    PHONE = "PHONE"
    AI_FOUND = "AI_FOUND"  # Found by AI Collection


class Entity(Base):
    """
    Represents a person, organization, or topic being researched.
    Central entity that links all collected information.
    """
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core identity
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True)  # lowercase, stripped
    entity_type = Column(Enum(EntityType), nullable=False, index=True)
    
    # Aliases and variations (for matching)
    aliases = Column(ARRAY(String), default=list)
    
    # Official presence
    official_urls = Column(JSON, default=list)  # [{url, type: website|instagram|twitter|...}]
    
    # Metadata
    description = Column(Text, nullable=True)
    image_url = Column(String(2000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="entity", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="entity", cascade="all, delete-orphan")
    briefs = relationship("Brief", back_populates="entity", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_entities_name_type', 'normalized_name', 'entity_type'),
    )

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a name for matching"""
        return name.lower().strip()

    def __repr__(self):
        return f"<Entity {self.name} ({self.entity_type})>"


class Document(Base):
    """
    A collected document/article about an entity.
    Deduplicated by fingerprint.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Entity link
    entity_id = Column(UUID(as_uuid=True), ForeignKey('entities.id'), nullable=False, index=True)
    
    # Source info
    source_config_id = Column(UUID(as_uuid=True), ForeignKey('source_configs.id'), nullable=True)
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(2000), nullable=True)
    
    # Content
    title = Column(String(500), nullable=False)
    url = Column(String(2000), nullable=True, index=True)
    snippet = Column(Text, nullable=True)
    full_content = Column(Text, nullable=True)
    
    # Deduplication
    fingerprint = Column(String(64), unique=True, nullable=False, index=True)
    
    # Dates
    published_at = Column(DateTime, nullable=True, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    entity = relationship("Entity", back_populates="documents")
    source_config = relationship("SourceConfig")
    extracts = relationship("Extract", back_populates="document", cascade="all, delete-orphan")

    @staticmethod
    def compute_fingerprint(title: str, url: str = None, published_date: datetime = None) -> str:
        """
        Compute unique fingerprint for deduplication.
        fingerprint = sha256(normalized_title + canonical_url + published_date)
        """
        normalized_title = title.lower().strip() if title else ""
        canonical_url = url.lower().strip().rstrip('/') if url else ""
        date_str = published_date.isoformat() if published_date else ""
        
        content = f"{normalized_title}|{canonical_url}|{date_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def __repr__(self):
        return f"<Document {self.title[:50]}>"


class Extract(Base):
    """
    Extracted intelligence from a document.
    Contains parsed contacts, events, entities found.
    """
    __tablename__ = "extracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Document link
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False, index=True)
    
    # Extracted content
    summary = Column(Text, nullable=True)
    
    # Contacts found (embedded for quick access)
    contacts_found = Column(JSON, default=list)
    # [{type, value, context, reliability_score}]
    
    # Other entities mentioned
    entities_found = Column(JSON, default=list)
    # [{name, type, context}]
    
    # Event signals (timeline events)
    event_signals = Column(JSON, default=list)
    # [{type, date, description, relevance_score}]
    
    # Classification
    opportunity_type = Column(Enum(ObjectiveType), nullable=True)
    confidence = Column(Float, default=0.0)  # 0-1 confidence score
    
    # Raw LLM response for debugging
    raw_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="extracts")

    def __repr__(self):
        return f"<Extract doc={self.document_id}>"


class Contact(Base):
    """
    Verified/scored contact information for an entity.
    Aggregated from multiple extracts.
    """
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Entity link
    entity_id = Column(UUID(as_uuid=True), ForeignKey('entities.id'), nullable=False, index=True)
    
    # Contact info
    contact_type = Column(Enum(ContactType), nullable=False)
    value = Column(String(500), nullable=False)
    label = Column(String(255), nullable=True)  # "Booking France", "Press Contact", etc.
    
    # Source tracking
    source_url = Column(String(2000), nullable=True)
    source_name = Column(String(255), nullable=True)
    
    # Reliability scoring
    reliability_score = Column(Integer, default=0)
    # +3 domaine officiel
    # +2 page contact/presse/booking
    # +1 mention média sérieux
    # -3 source douteuse
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    entity = relationship("Entity", back_populates="contacts")

    __table_args__ = (
        UniqueConstraint('entity_id', 'contact_type', 'value', name='uq_entity_contact'),
        Index('ix_contacts_reliability', 'entity_id', 'reliability_score'),
    )

    def __repr__(self):
        return f"<Contact {self.contact_type}: {self.value}>"


class Brief(Base):
    """
    Generated intelligence brief for an entity.
    Synthesizes all collected information.
    """
    __tablename__ = "briefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Entity link
    entity_id = Column(UUID(as_uuid=True), ForeignKey('entities.id'), nullable=False, index=True)
    
    # Collection context
    objective = Column(Enum(ObjectiveType), nullable=False)
    timeframe_days = Column(Integer, default=30)
    
    # Generated content
    overview = Column(Text, nullable=True)  # Summary paragraph
    
    # Ranked contacts (ordered by reliability)
    contacts_ranked = Column(JSON, default=list)
    # [{type, value, label, reliability_score, source}]
    
    # Useful facts
    useful_facts = Column(JSON, default=list)
    # [{fact, source, category}]
    
    # Timeline of events
    timeline = Column(JSON, default=list)
    # [{date, event_type, description, source}]
    
    # Sources used
    sources_used = Column(JSON, default=list)
    # [{name, url, document_count}]
    
    # Quality metrics
    document_count = Column(Integer, default=0)
    contact_count = Column(Integer, default=0)
    completeness_score = Column(Float, default=0.0)  # 0-1
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # For cache invalidation
    
    # Relationships
    entity = relationship("Entity", back_populates="briefs")

    def __repr__(self):
        return f"<Brief entity={self.entity_id} obj={self.objective}>"


class CollectionRun(Base):
    """
    A collection run encompassing multiple sources.
    Higher-level than IngestionRun (which is per-source).
    """
    __tablename__ = "collection_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request context
    objective = Column(Enum(ObjectiveType), nullable=False)
    entities_requested = Column(JSON, default=list)  # [{name, type}]
    secondary_keywords = Column(ARRAY(String), default=list)
    timeframe_days = Column(Integer, default=30)
    require_contact = Column(Boolean, default=False)
    
    # Filters applied
    budget_min = Column(Numeric(15, 2), nullable=True)
    budget_max = Column(Numeric(15, 2), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(20), default="PENDING")  # PENDING, RUNNING, SUCCESS, PARTIAL, FAILED
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    
    # Stats
    source_count = Column(Integer, default=0)
    sources_success = Column(Integer, default=0)
    sources_failed = Column(Integer, default=0)
    documents_new = Column(Integer, default=0)
    documents_updated = Column(Integer, default=0)
    contacts_found = Column(Integer, default=0)
    
    # Generated brief
    brief_id = Column(UUID(as_uuid=True), ForeignKey('briefs.id'), nullable=True)
    
    # Error summary
    error_summary = Column(Text, nullable=True)
    
    # Per-source breakdown
    source_runs = Column(JSON, default=list)
    # [{source_id, source_name, status, items_found, items_new, latency_ms, error}]

    def __repr__(self):
        return f"<CollectionRun {self.id} - {self.status}>"
