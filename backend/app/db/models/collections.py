"""
Modèles SQLAlchemy pour le système de collectes refondé
- Collection: historique des collectes
- CollectionLog: logs détaillés
- LeadItem: source de vérité unique (opportunités + candidats)
- CollectionResult: liaison collection <-> lead_items
- SourceDocument: documents bruts (preuves)
- DossierV2: packaging IA
- Evidence: traçabilité des données
"""
import uuid
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey,
    Enum, UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


# ================================================================
# ENUMS
# ================================================================

class CollectionType(str, PyEnum):
    STANDARD = "STANDARD"
    AI = "AI"


class CollectionStatus(str, PyEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class LeadItemKind(str, PyEnum):
    OPPORTUNITY = "OPPORTUNITY"
    DOSSIER_CANDIDATE = "DOSSIER_CANDIDATE"


class LeadItemStatus(str, PyEnum):
    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    CONTACTED = "CONTACTED"
    WON = "WON"
    LOST = "LOST"
    ARCHIVED = "ARCHIVED"


class DocType(str, PyEnum):
    HTML = "HTML"
    PDF_TEXT = "PDF_TEXT"
    EMAIL_TEXT = "EMAIL_TEXT"
    WEB_SNAPSHOT_TEXT = "WEB_SNAPSHOT_TEXT"
    WEB_EXTRACT = "WEB_EXTRACT"


class DossierObjective(str, PyEnum):
    SPONSOR = "SPONSOR"
    BOOKING = "BOOKING"
    PRESS = "PRESS"
    VENUE = "VENUE"
    SUPPLIER = "SUPPLIER"
    GRANT = "GRANT"


class DossierState(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class EvidenceProvenance(str, PyEnum):
    STANDARD_DOC = "STANDARD_DOC"
    WEB_ENRICHED = "WEB_ENRICHED"
    AI_EXTRACTED = "AI_EXTRACTED"
    GPT_GROUNDED = "GPT_GROUNDED"


class LogLevel(str, PyEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ================================================================
# MODELS
# ================================================================

class CollectionV2(Base):
    """Historique des collectes (standard et IA)"""
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(20), nullable=False)  # STANDARD, AI
    status = Column(String(20), nullable=False, default=CollectionStatus.QUEUED.value)
    name = Column(String(255), nullable=True)
    params = Column(JSONB, nullable=True)  # Inputs utilisateur
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    stats = Column(JSONB, nullable=True)  # pages_fetched, results_count, errors_count, tokens_used
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    logs = relationship("CollectionLog", back_populates="collection", cascade="all, delete-orphan")
    results = relationship("CollectionResult", back_populates="collection", cascade="all, delete-orphan")
    documents = relationship("SourceDocument", back_populates="collection")
    creator = relationship("User", foreign_keys=[created_by])

    def set_running(self):
        self.status = CollectionStatus.RUNNING.value
        self.started_at = datetime.utcnow()

    def set_done(self, stats: Dict[str, Any] = None):
        self.status = CollectionStatus.DONE.value
        self.finished_at = datetime.utcnow()
        if stats:
            self.stats = stats

    def set_failed(self, error: str):
        self.status = CollectionStatus.FAILED.value
        self.finished_at = datetime.utcnow()
        self.error = error

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class CollectionLog(Base):
    """Logs détaillés des collectes"""
    __tablename__ = "collection_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String(10), nullable=False, default=LogLevel.INFO.value)
    message = Column(Text, nullable=False)
    context = Column(JSONB, nullable=True)

    # Relations
    collection = relationship("CollectionV2", back_populates="logs")


class LeadItem(Base):
    """Source de vérité unique pour opportunités et candidats dossiers"""
    __tablename__ = "lead_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String(30), nullable=False)  # OPPORTUNITY, DOSSIER_CANDIDATE
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    organization_name = Column(String(300), nullable=True)
    url_primary = Column(String(2000), nullable=True)
    source_id = Column(Integer, ForeignKey('source_configs.id', ondelete='SET NULL'), nullable=True)
    source_name = Column(String(255), nullable=True)
    source_type = Column(String(50), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    location_city = Column(String(100), nullable=True)
    location_region = Column(String(100), nullable=True)
    location_country = Column(String(100), nullable=True, default='France')
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    budget_currency = Column(String(10), nullable=True, default='EUR')
    budget_display = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_url = Column(String(500), nullable=True)
    contact_name = Column(String(200), nullable=True)
    has_contact = Column(Boolean, default=False)
    has_deadline = Column(Boolean, default=False)
    score_base = Column(Integer, nullable=True, default=0)
    score_breakdown = Column(JSONB, nullable=True)
    status = Column(String(30), nullable=False, default=LeadItemStatus.NEW.value)
    tags = Column(JSONB, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    canonical_hash = Column(String(64), nullable=True, unique=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    collection_results = relationship("CollectionResult", back_populates="lead_item", cascade="all, delete-orphan")
    source_documents = relationship("SourceDocument", back_populates="lead_item", cascade="all, delete-orphan")
    dossier = relationship("DossierV2", back_populates="lead_item", uselist=False, cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="lead_item", cascade="all, delete-orphan")
    assignee = relationship("User", foreign_keys=[assigned_to])

    @staticmethod
    def compute_canonical_hash(title: str, org: str = None, deadline: datetime = None, city: str = None) -> str:
        """Calcule un hash canonique pour dédup sans URL"""
        normalized = f"{(title or '').lower().strip()}"
        if org:
            normalized += f"|{org.lower().strip()}"
        if deadline:
            normalized += f"|{deadline.isoformat()}"
        if city:
            normalized += f"|{city.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    @property
    def has_contact(self) -> bool:
        return bool(self.contact_email or self.contact_phone or self.contact_url)

    @property
    def has_deadline(self) -> bool:
        return self.deadline_at is not None

    @property
    def budget_display(self) -> Optional[str]:
        if self.budget_min and self.budget_max:
            return f"{int(self.budget_min):,} - {int(self.budget_max):,} {self.budget_currency}"
        elif self.budget_max:
            return f"≤ {int(self.budget_max):,} {self.budget_currency}"
        elif self.budget_min:
            return f"≥ {int(self.budget_min):,} {self.budget_currency}"
        return None


class CollectionResult(Base):
    """Liaison entre collection et lead_items produits"""
    __tablename__ = "collection_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)
    lead_item_id = Column(UUID(as_uuid=True), ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=False)
    is_new = Column(Boolean, default=True)  # Nouveau ou existant (dédup)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    collection = relationship("CollectionV2", back_populates="results")
    lead_item = relationship("LeadItem", back_populates="collection_results")

    __table_args__ = (
        UniqueConstraint('collection_id', 'lead_item_id', name='uq_collection_results'),
    )


class SourceDocument(Base):
    """Documents bruts servant de preuves"""
    __tablename__ = "source_documents_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_item_id = Column(UUID(as_uuid=True), ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='SET NULL'), nullable=True)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey('dossiers_v2.id', ondelete='SET NULL'), nullable=True)
    source_id = Column(Integer, ForeignKey('source_configs.id', ondelete='SET NULL'), nullable=True)
    url = Column(String(2000), nullable=True)
    doc_type = Column(String(30), nullable=True)
    raw_html = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    storage_path = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    lead_item = relationship("LeadItem", back_populates="source_documents")
    collection = relationship("CollectionV2", back_populates="documents")
    dossier = relationship("DossierV2", back_populates="source_documents")
    evidence_items = relationship("Evidence", back_populates="source_document")

    @staticmethod
    def compute_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()


class DossierV2(Base):
    """Dossier IA enrichi (1:1 avec lead_item)"""
    __tablename__ = "dossiers_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_item_id = Column(UUID(as_uuid=True), ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=False, unique=True)
    objective = Column(String(30), nullable=False)
    target_entities = Column(JSONB, nullable=True)
    state = Column(String(20), nullable=False, default=DossierState.PROCESSING.value)
    # Contenu structuré
    sections = Column(JSONB, nullable=True)  # [{title, content, evidence_refs}]
    summary = Column(Text, nullable=True)
    key_findings = Column(JSONB, nullable=True)  # [str]
    recommendations = Column(JSONB, nullable=True)  # [str]
    # Qualité et métriques
    quality_score = Column(Integer, nullable=True, default=0)
    quality_breakdown = Column(JSONB, nullable=True)  # {completeness, source_quality, relevance}
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String(50), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    lead_item = relationship("LeadItem", back_populates="dossier")
    evidence_items = relationship("Evidence", back_populates="dossier", cascade="all, delete-orphan")
    source_documents = relationship("SourceDocument", back_populates="dossier")

    def set_ready(self):
        self.state = DossierState.READY.value

    def set_failed(self, error: str):
        self.state = DossierState.FAILED.value
        self.error_message = error


class Evidence(Base):
    """Traçabilité des données extraites"""
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_item_id = Column(UUID(as_uuid=True), ForeignKey('lead_items.id', ondelete='CASCADE'), nullable=True)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey('dossiers_v2.id', ondelete='CASCADE'), nullable=True)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey('source_documents_v2.id', ondelete='SET NULL'), nullable=True)
    field_name = Column(String(100), nullable=False)  # Champ ciblé
    value = Column(Text, nullable=True)  # Valeur extraite
    quote = Column(Text, nullable=True)  # Citation exacte du document
    url = Column(String(2000), nullable=True)  # URL source
    provenance = Column(String(30), nullable=False)  # STANDARD_DOC, WEB_ENRICHED, GPT_GROUNDED
    confidence = Column(Float, nullable=True, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    lead_item = relationship("LeadItem", back_populates="evidence_items")
    dossier = relationship("DossierV2", back_populates="evidence_items")
    source_document = relationship("SourceDocument", back_populates="evidence_items")
