"""
Dossier models for advanced GPT pipeline
- SourceDocument: raw content storage for grounding
- Dossier: enriched opportunity with GPT analysis
- DossierEvidence: proof for each extracted field (anti-hallucination)
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Text, DateTime, Enum, Integer, Numeric, 
    JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


# ============================================================================
# ENUMS
# ============================================================================

class DocType(str, PyEnum):
    """Type of source document"""
    HTML = "HTML"
    EMAIL_HTML = "EMAIL_HTML"
    EMAIL_TEXT = "EMAIL_TEXT"
    PDF_TEXT = "PDF_TEXT"
    ATTACHMENT = "ATTACHMENT"
    WEB_SNAPSHOT_TEXT = "WEB_SNAPSHOT_TEXT"  # Full page from web enrichment
    WEB_EXTRACT = "WEB_EXTRACT"  # Specific snippet from web enrichment


class DossierState(str, PyEnum):
    """State of dossier processing"""
    NOT_CREATED = "NOT_CREATED"
    PROCESSING = "PROCESSING"
    ENRICHING = "ENRICHING"  # Web enrichment in progress
    MERGING = "MERGING"  # Final GPT merge pass
    READY = "READY"
    FAILED = "FAILED"


class EvidenceProvenance(str, PyEnum):
    """Where the evidence came from"""
    STANDARD_DOC = "STANDARD_DOC"  # From original ingestion
    WEB_ENRICHED = "WEB_ENRICHED"  # From web enrichment actors


class EvidenceType(str, PyEnum):
    """Type of evidence source"""
    HTML = "HTML"
    EMAIL = "EMAIL"
    PDF = "PDF"
    WEB = "WEB"


# ============================================================================
# SOURCE DOCUMENTS - Raw content storage
# ============================================================================

class SourceDocument(Base):
    """
    Stores raw content from ingestion and web enrichment.
    GPT uses these documents for grounded analysis.
    """
    __tablename__ = "source_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to opportunity
    opportunity_id = Column(
        Integer, 
        ForeignKey('opportunities.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Document type
    doc_type = Column(Enum(DocType), nullable=False, index=True)
    
    # Raw content
    raw_text = Column(Text, nullable=True)  # Extracted text content
    raw_html = Column(Text, nullable=True)  # Original HTML if applicable
    
    # Metadata
    raw_metadata = Column(JSON, default=dict)
    # Expected fields: url, fetched_at, content_type, email_from, email_subject,
    # attachment_name, file_size, encoding, etc.
    
    # For web enrichment tracking
    source_url = Column(String(2000), nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    opportunity = relationship(
        "Opportunity",
        backref="source_documents"
    )
    
    __table_args__ = (
        Index('ix_source_docs_opp_type', 'opportunity_id', 'doc_type'),
    )
    
    def __repr__(self):
        return f"<SourceDocument {self.doc_type.value} for opp {self.opportunity_id}>"


# ============================================================================
# DOSSIER - Enriched opportunity (1:1 with opportunity)
# ============================================================================

class Dossier(Base):
    """
    GPT-enriched analysis of an opportunity.
    One dossier per opportunity (unique constraint).
    """
    __tablename__ = "dossiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to opportunity (1:1)
    opportunity_id = Column(
        Integer, 
        ForeignKey('opportunities.id', ondelete='CASCADE'), 
        nullable=False,
        unique=True,
        index=True
    )
    
    # Processing state
    state = Column(
        Enum(DossierState), 
        default=DossierState.NOT_CREATED, 
        nullable=False,
        index=True
    )
    
    # === GPT Generated Content ===
    
    # Summaries
    summary_short = Column(String(500), nullable=True)  # <500 chars
    summary_long = Column(Text, nullable=True)  # Markdown format
    
    # Structured analysis
    key_points = Column(JSON, default=list)  # Array of key points
    action_checklist = Column(JSON, default=list)  # Array of action items
    
    # === Extracted Fields (structured) ===
    extracted_fields = Column(JSON, default=dict)
    # Expected structure:
    # {
    #   "deadline_at": "2025-02-15T00:00:00",
    #   "budget_amount": 50000,
    #   "budget_hint": "Entre 40k et 60k €",
    #   "location": {"city": "Paris", "region": "IDF", "country": "FR"},
    #   "contact_email": "contact@org.fr",
    #   "contact_phone": "+33 1 23 45 67 89",
    #   "contact_url": "https://...",
    #   "exigences": ["Expérience événementiel", "Capacité 500 pers"],
    #   "contraintes": ["Délai court", "Budget serré"],
    #   "doc_list": ["cahier_charges.pdf", "annexe_technique.pdf"]
    # }
    
    # === Quality & Confidence ===
    
    # Confidence score from GPT (0-100)
    confidence_plus = Column(Integer, default=0)
    
    # Quality flags (missing critical info)
    quality_flags = Column(JSON, default=list)
    # Expected: ["missing_deadline", "missing_budget", "missing_contact", 
    #            "low_confidence", "incomplete_requirements"]
    
    # Missing fields that need web enrichment
    missing_fields = Column(JSON, default=list)
    # Expected: ["deadline_at", "budget_amount", "contact_email"]
    
    # === Source Tracking ===
    
    # IDs of source_documents used for analysis
    sources_used = Column(JSON, default=list)  # Array of source_document UUIDs
    
    # === Final Scoring ===
    
    # Combined score: base + confidence adjustment
    score_final = Column(Integer, default=0, index=True)
    
    # Processing info
    gpt_model_used = Column(String(50), nullable=True)  # e.g., "gpt-4o"
    tokens_used = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)  # Last successful GPT pass
    enriched_at = Column(DateTime, nullable=True)  # Last web enrichment
    
    # Relationships
    opportunity = relationship(
        "Opportunity",
        backref="dossier",
        uselist=False  # 1:1 relationship
    )
    evidence = relationship(
        "DossierEvidence",
        back_populates="dossier",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('ix_dossiers_state_score', 'state', 'score_final'),
    )
    
    def __repr__(self):
        return f"<Dossier {self.state.value} for opp {self.opportunity_id}>"
    
    def calculate_final_score(self, base_score: int) -> int:
        """Calculate final score: base + confidence adjustment"""
        # score_final = clamp(score_base + (confidence_plus * 0.2), 0, 100)
        adjustment = int(self.confidence_plus * 0.2)
        self.score_final = max(0, min(100, base_score + adjustment))
        return self.score_final


# ============================================================================
# DOSSIER EVIDENCE - Anti-hallucination proof
# ============================================================================

class DossierEvidence(Base):
    """
    Evidence for each extracted field in a dossier.
    CRITICAL: Every non-null field must have at least one evidence.
    """
    __tablename__ = "dossier_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to dossier
    dossier_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('dossiers.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Field this evidence supports
    field_key = Column(String(50), nullable=False, index=True)
    # Expected: "deadline_at", "budget_amount", "contact_email", 
    #           "contact_phone", "contact_url", "location", etc.
    
    # Extracted value
    value = Column(Text, nullable=True)
    
    # Provenance tracking
    provenance = Column(
        Enum(EvidenceProvenance), 
        nullable=False,
        default=EvidenceProvenance.STANDARD_DOC
    )
    
    # Evidence type
    evidence_type = Column(Enum(EvidenceType), nullable=False)
    
    # Reference to source
    evidence_ref = Column(String(2000), nullable=True)
    # Could be: URL, email message-id, file path, source_document_id
    
    source_document_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('source_documents.id', ondelete='SET NULL'), 
        nullable=True
    )
    
    # Evidence snippet (proof text)
    evidence_snippet = Column(String(500), nullable=True)  # Max 300-500 chars
    
    # Confidence for this specific evidence (0-100)
    confidence = Column(Integer, default=50)
    
    # For web enrichment
    source_url = Column(String(2000), nullable=True)
    retrieved_at = Column(DateTime, nullable=True)
    retrieval_method = Column(String(50), nullable=True)  # e.g., "google_search", "direct_fetch"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dossier = relationship("Dossier", back_populates="evidence")
    source_document = relationship("SourceDocument")
    
    __table_args__ = (
        Index('ix_evidence_dossier_field', 'dossier_id', 'field_key'),
    )
    
    def __repr__(self):
        return f"<DossierEvidence {self.field_key}={self.value[:20] if self.value else 'null'}>"


# ============================================================================
# WEB ENRICHMENT RUN - Track enrichment jobs
# ============================================================================

class WebEnrichmentRun(Base):
    """
    Track web enrichment jobs for observability.
    """
    __tablename__ = "web_enrichment_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to dossier
    dossier_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('dossiers.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Status
    status = Column(String(20), default="PENDING")  # PENDING, RUNNING, SUCCESS, FAILED
    
    # What fields we're looking for
    target_fields = Column(JSON, default=list)  # ["deadline_at", "contact_email"]
    
    # Results summary
    fields_found = Column(JSON, default=list)  # Fields successfully found
    fields_not_found = Column(JSON, default=list)  # Fields not found
    
    # Actors used
    actors_used = Column(JSON, default=list)  # ["contact_actor", "deadline_actor"]
    
    # URLs consulted
    urls_consulted = Column(JSON, default=list)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Errors
    errors = Column(JSON, default=list)
    
    # Relationships
    dossier = relationship("Dossier", backref="enrichment_runs")
    
    def __repr__(self):
        return f"<WebEnrichmentRun {self.status} for dossier {self.dossier_id}>"
