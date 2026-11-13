"""
Opportunity and related models
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Enum, ForeignKey,
    Integer, Numeric, JSON, Table, Index
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class SourceType(str, PyEnum):
    """Source types for opportunities"""
    EMAIL = "EMAIL"
    RSS = "RSS"
    HTML = "HTML"
    API = "API"


class OpportunityCategory(str, PyEnum):
    """Opportunity categories"""
    PUBLIC_TENDER = "PUBLIC_TENDER"       # Marché public / consultation
    CALL_FOR_PROJECTS = "CALL_FOR_PROJECTS"  # Appel à projets
    GRANT = "GRANT"                        # Aide / subvention
    PARTNERSHIP = "PARTNERSHIP"            # Partenariat / sponsor
    VENUE = "VENUE"                        # Lieu / privatisation
    SUPPLIER = "SUPPLIER"                  # Prestataire / technique
    OTHER = "OTHER"


class OpportunityStatus(str, PyEnum):
    """Pipeline status"""
    NEW = "NEW"
    REVIEW = "REVIEW"
    QUALIFIED = "QUALIFIED"
    CONTACTED = "CONTACTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    WON = "WON"
    LOST = "LOST"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class TaskStatus(str, PyEnum):
    """Task status"""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


# Association table for tags
opportunity_tags = Table(
    'opportunity_tag_associations',
    Base.metadata,
    Column('opportunity_id', Integer, ForeignKey('opportunities.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('opportunity_tags.id'), primary_key=True)
)


class Opportunity(Base):
    """Main opportunity model"""
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Workspace isolation
    workspace_id = Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    
    # External identification (for deduplication)
    external_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Source information
    source_type = Column(Enum(SourceType), nullable=False)
    source_name = Column(String(255), nullable=False, index=True)
    source_config_id = Column(Integer, ForeignKey('source_configs.id'), nullable=True)
    
    # Core content
    title = Column(String(500), nullable=False)
    category = Column(Enum(OpportunityCategory), default=OpportunityCategory.OTHER, index=True)
    organization = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    snippet = Column(String(500), nullable=True)
    
    # URLs
    url_primary = Column(String(2000), nullable=True, index=True)
    urls_all = Column(JSON, default=list)  # List of all related URLs
    
    # Dates
    published_at = Column(DateTime, nullable=True)
    deadline_at = Column(DateTime, nullable=True, index=True)
    
    # Location
    location_city = Column(String(100), nullable=True)
    location_region = Column(String(100), nullable=True, index=True)
    location_country = Column(String(2), default="FR")
    
    # Budget
    budget_amount = Column(Numeric(15, 2), nullable=True, index=True)
    budget_currency = Column(String(3), default="EUR")
    budget_hint = Column(String(500), nullable=True)
    
    # Contact
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_url = Column(String(2000), nullable=True)
    
    # Scoring
    score = Column(Integer, default=0, index=True)
    score_breakdown = Column(JSON, default=dict)
    
    # Pipeline status
    status = Column(Enum(OpportunityStatus), default=OpportunityStatus.NEW, index=True)
    assigned_to_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Deduplication
    possible_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, ForeignKey('opportunities.id'), nullable=True)
    
    # Raw data (for debugging)
    raw_content_hash = Column(String(64), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source_config = relationship("SourceConfig", back_populates="opportunities")
    assigned_to = relationship(
        "User",
        back_populates="assigned_opportunities",
        foreign_keys=[assigned_to_user_id]
    )
    notes = relationship("OpportunityNote", back_populates="opportunity", cascade="all, delete-orphan")
    tasks = relationship("OpportunityTask", back_populates="opportunity", cascade="all, delete-orphan")
    tags = relationship("OpportunityTag", secondary=opportunity_tags, back_populates="opportunities")
    duplicates = relationship("Opportunity", backref="duplicate_of", remote_side=[id])
    
    # Indexes
    __table_args__ = (
        Index('ix_opportunities_score_deadline', 'score', 'deadline_at'),
        Index('ix_opportunities_status_score', 'status', 'score'),
        Index('ix_opportunities_created_status', 'created_at', 'status'),
    )
    
    def __repr__(self):
        return f"<Opportunity {self.title[:50]}>"


class OpportunityNote(Base):
    """Notes on opportunities"""
    __tablename__ = "opportunity_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="notes")
    author = relationship("User", back_populates="notes")


class OpportunityTask(Base):
    """Tasks / reminders on opportunities"""
    __tablename__ = "opportunity_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="tasks")
    assigned_to = relationship("User", back_populates="tasks")


class OpportunityTag(Base):
    """Tags for opportunities"""
    __tablename__ = "opportunity_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(7), default="#6366f1")  # Hex color
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    opportunities = relationship("Opportunity", secondary=opportunity_tags, back_populates="tags")
