"""
New Radar Features Models:
- Daily Shortlists (Auto-Shortlist)
- Opportunity Clusters (Dedup)
- Profiles (Fit Score)
- Deadline Alerts (Deadline Guard)
- Source Health
- Contact Finder Evidence
"""
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Date, Enum, ForeignKey,
    Integer, Float, Numeric, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


# ============================================================================
# PROFILES (Fit Score par Profil)
# ============================================================================

class ProfileObjective(str, PyEnum):
    """Objectives that a profile can target"""
    SPONSOR = "SPONSOR"
    BOOKING = "BOOKING"
    VENUE = "VENUE"
    PARTNERSHIP = "PARTNERSHIP"
    GRANT = "GRANT"
    PUBLIC_TENDER = "PUBLIC_TENDER"


class Profile(Base):
    """
    User-defined profile for opportunity matching.
    Influences shortlist generation and fit score calculation.
    """
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Keywords filtering
    keywords_include = Column(ARRAY(String), default=list)  # Must match at least one
    keywords_exclude = Column(ARRAY(String), default=list)  # Must not match any
    
    # Location filtering
    regions = Column(ARRAY(String), default=list)  # e.g., ["Île-de-France", "PACA"]
    cities = Column(ARRAY(String), default=list)   # e.g., ["Paris", "Marseille"]
    
    # Budget filtering
    budget_min = Column(Numeric(15, 2), nullable=True)
    budget_max = Column(Numeric(15, 2), nullable=True)
    
    # Objectives
    objectives = Column(ARRAY(String), default=list)  # List of ProfileObjective values
    
    # Scoring weights (how to compute fit score)
    weights = Column(JSON, default=lambda: {
        "score_base": 0.4,      # Weight for base opportunity score
        "budget_match": 0.2,    # Weight for budget match
        "deadline_proximity": 0.15,  # Weight for deadline proximity
        "contact_present": 0.15,     # Weight for having contact info
        "location_match": 0.1,       # Weight for location match
    })
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shortlists = relationship("DailyShortlist", back_populates="profile", cascade="all, delete-orphan")
    opportunity_scores = relationship("OpportunityProfileScore", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Profile {self.name}>"


class OpportunityProfileScore(Base):
    """
    Precomputed fit score for an opportunity against a profile.
    Recalculated periodically or on-demand.
    """
    __tablename__ = "opportunity_profile_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    
    # Score result
    fit_score = Column(Integer, default=0)  # 0-100
    
    # Score breakdown
    reasons = Column(JSON, default=dict)
    # Example: {
    #   "budget_match": true,
    #   "deadline_soon": true,
    #   "contact_present": false,
    #   "location_match": true,
    #   "keyword_matches": ["rap", "festival"],
    #   "score_components": {"base": 35, "budget": 20, "deadline": 15, "location": 10}
    # }
    
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    opportunity = relationship("Opportunity")
    profile = relationship("Profile", back_populates="opportunity_scores")
    
    __table_args__ = (
        UniqueConstraint('opportunity_id', 'profile_id', name='uq_opportunity_profile'),
        Index('ix_opp_profile_score', 'profile_id', 'fit_score'),
    )


# ============================================================================
# DAILY SHORTLISTS (Auto-Shortlist quotidienne)
# ============================================================================

class ShortlistReason(str, PyEnum):
    """Reasons why an opportunity was shortlisted"""
    BUDGET_MATCH = "budget_match"
    DEADLINE_SOON = "deadline_soon"
    CONTACT_PRESENT = "contact_present"
    LOCATION_MATCH = "location_match"
    SOURCE_QUALITY = "source_quality"
    SCORE_HIGH = "score_high"
    KEYWORD_MATCH = "keyword_match"
    NEW_TODAY = "new_today"


class DailyShortlist(Base):
    """
    Daily generated shortlist for a profile.
    Contains top N opportunities with explanations.
    """
    __tablename__ = "daily_shortlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Date and profile
    date = Column(Date, nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    
    # Shortlist items (JSON array)
    items = Column(JSON, nullable=False, default=list)
    # Format: [
    #   {
    #     "opportunity_id": "uuid",
    #     "title": "...",
    #     "score": 85,
    #     "fit_score": 92,
    #     "reasons": ["budget_match", "deadline_soon", "score_high"],
    #     "deadline_at": "2025-01-15T00:00:00",
    #     "organization": "..."
    #   },
    #   ...
    # ]
    
    # Stats
    total_candidates = Column(Integer, default=0)  # How many were considered
    items_count = Column(Integer, default=0)       # How many made the cut
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profile = relationship("Profile", back_populates="shortlists")
    
    __table_args__ = (
        UniqueConstraint('date', 'profile_id', name='uq_daily_shortlist_date_profile'),
        Index('ix_shortlist_date_profile', 'date', 'profile_id'),
    )

    def __repr__(self):
        return f"<DailyShortlist {self.date} - {self.profile_id}>"


# ============================================================================
# OPPORTUNITY CLUSTERS (Dedup intelligent)
# ============================================================================

class OpportunityCluster(Base):
    """
    A cluster of similar/duplicate opportunities.
    One opportunity is designated as the "canonical" one.
    """
    __tablename__ = "opportunity_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # The main/canonical opportunity to display
    canonical_opportunity_id = Column(
        Integer, 
        ForeignKey('opportunities.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Cluster quality score (higher = more confident clustering)
    cluster_score = Column(Float, default=1.0)
    
    # Metadata
    member_count = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    canonical_opportunity = relationship("Opportunity", foreign_keys=[canonical_opportunity_id])
    members = relationship("OpportunityClusterMember", back_populates="cluster", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OpportunityCluster {self.id} - {self.member_count} members>"


class OpportunityClusterMember(Base):
    """
    Member of an opportunity cluster (alternative source).
    """
    __tablename__ = "opportunity_cluster_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    cluster_id = Column(Integer, ForeignKey('opportunity_clusters.id', ondelete='CASCADE'), nullable=False)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Similarity to canonical
    similarity_score = Column(Float, default=1.0)  # 0.0 - 1.0
    
    # Why it was clustered
    match_type = Column(String(50), default="hash")  # "url", "hash", "cosine"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cluster = relationship("OpportunityCluster", back_populates="members")
    opportunity = relationship("Opportunity")
    
    __table_args__ = (
        Index('ix_cluster_member', 'cluster_id', 'opportunity_id'),
    )


# ============================================================================
# DEADLINE ALERTS (Deadline Guard)
# ============================================================================

class AlertType(str, PyEnum):
    """Types of deadline alerts"""
    D7 = "D7"   # 7 days before
    D3 = "D3"   # 3 days before
    D1 = "D1"   # 1 day before


class AlertStatus(str, PyEnum):
    """Status of an alert"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeadlineAlert(Base):
    """
    Scheduled deadline alerts for opportunities.
    Prevents missing important deadlines.
    """
    __tablename__ = "deadline_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False)
    
    # Alert configuration
    alert_type = Column(Enum(AlertType), nullable=False)
    scheduled_for = Column(DateTime, nullable=False, index=True)
    
    # Delivery status
    status = Column(Enum(AlertStatus), default=AlertStatus.PENDING)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Notification channels used
    channels = Column(JSON, default=list)  # ["email", "webhook"]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    opportunity = relationship("Opportunity")
    
    __table_args__ = (
        UniqueConstraint('opportunity_id', 'alert_type', name='uq_deadline_alert'),
        Index('ix_deadline_alert_scheduled', 'scheduled_for', 'status'),
    )

    def __repr__(self):
        return f"<DeadlineAlert {self.alert_type} for {self.opportunity_id}>"


# ============================================================================
# SOURCE HEALTH (Qualité et stabilité des sources)
# ============================================================================

class SourceHealth(Base):
    """
    Daily health metrics for each source.
    Helps diagnose buggy or useless sources.
    """
    __tablename__ = "source_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    source_id = Column(Integer, ForeignKey('source_configs.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    
    # Request metrics
    requests = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # 0.0 - 1.0
    
    # Performance metrics
    avg_latency_ms = Column(Integer, default=0)
    max_latency_ms = Column(Integer, default=0)
    
    # Content metrics
    items_found = Column(Integer, default=0)      # Raw items fetched
    items_kept = Column(Integer, default=0)       # After dedup/filtering
    items_new = Column(Integer, default=0)        # Actually new to DB
    duplicates_count = Column(Integer, default=0)
    duplicates_rate = Column(Float, default=0.0)  # 0.0 - 1.0
    
    # Error tracking
    error_types = Column(JSON, default=dict)  # {"timeout": 3, "parse_error": 1}
    last_error = Column(Text, nullable=True)
    
    # Computed health score (0-100)
    health_score = Column(Integer, default=100)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source = relationship("SourceConfig")
    
    __table_args__ = (
        UniqueConstraint('source_id', 'date', name='uq_source_health_date'),
        Index('ix_source_health_date', 'date', 'source_id'),
        Index('ix_source_health_score', 'health_score'),
    )

    def __repr__(self):
        return f"<SourceHealth {self.source_id} {self.date}>"


# ============================================================================
# CONTACT FINDER (Web Enrichment Evidence)
# ============================================================================

class ContactFinderResult(Base):
    """
    Results from contact finder enrichment.
    Stores evidence for found contacts.
    """
    __tablename__ = "contact_finder_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False)
    
    # Status
    status = Column(String(20), default="pending")  # pending, found, not_found, error
    
    # Found contact info
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_role = Column(String(100), nullable=True)
    
    # Evidence (REQUIRED - never fill without evidence)
    evidence_url = Column(String(2000), nullable=True)
    evidence_snippet = Column(Text, nullable=True)  # The text that contains the contact
    evidence_domain = Column(String(255), nullable=True)
    
    # Search metadata
    searched_urls = Column(JSON, default=list)  # All URLs that were searched
    search_method = Column(String(50), default="official_first")  # official_first, social, etc.
    
    # Performance
    search_duration_ms = Column(Integer, nullable=True)
    pages_crawled = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunity = relationship("Opportunity")
    
    __table_args__ = (
        Index('ix_contact_finder_opportunity', 'opportunity_id'),
        Index('ix_contact_finder_status', 'status'),
    )

    def __repr__(self):
        return f"<ContactFinderResult {self.opportunity_id} - {self.status}>"
