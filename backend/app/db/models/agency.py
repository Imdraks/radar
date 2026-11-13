"""
Agency Cockpit Models - V2 Data Model
Client → Deal → Project → Deliverable → Approval
                       → Asset
                       → Task
                       → CalendarEvent
"""
import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, Enum, Float, JSON, Index, Table
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
import uuid

from app.db.base import Base


# ============================================================================
# ENUMS - Statuts normalisés
# ============================================================================

class DealStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTE_SENT = "quote_sent"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DELIVERED = "delivered"
    ARCHIVED = "archived"


class DeliverableStatus(str, enum.Enum):
    DRAFT = "draft"
    TO_REVIEW = "to_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    DELIVERED = "delivered"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    CHANGES = "changes"
    APPROVED = "approved"


class AssetKind(str, enum.Enum):
    LINK = "link"
    FILE = "file"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CalendarEventType(str, enum.Enum):
    SHOOT = "shoot"
    DELIVERY = "delivery"
    MEETING = "meeting"
    DEADLINE = "deadline"
    OTHER = "other"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# ============================================================================
# CLIENT
# ============================================================================

class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_name", "name"),
        Index("ix_clients_workspace_id", "workspace_id"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Workspace association - CRITICAL for multi-tenancy
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Contacts stockés en JSON: [{"name": "...", "email": "...", "phone": "...", "role": "..."}]
    contacts: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # ===== Champs pour facturation =====
    # Adresse
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[Optional[str]] = mapped_column(String(100), default="France")
    
    # Infos légales
    siret: Mapped[Optional[str]] = mapped_column(String(20))
    vat_number: Mapped[Optional[str]] = mapped_column(String(30))
    
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    deals: Mapped[List["Deal"]] = relationship("Deal", back_populates="client", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="client", cascade="all, delete-orphan")


# ============================================================================
# DEAL (Pipeline commercial)
# ============================================================================

class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_status", "status"),
        Index("ix_deals_client_id", "client_id"),
        Index("ix_deals_owner_id", "owner_id"),
        Index("ix_deals_next_action_date", "next_action_date"),
        Index("ix_deals_last_contact_at", "last_contact_at"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relation client
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client: Mapped["Client"] = relationship("Client", back_populates="deals")
    
    # Infos deal
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DealStatus] = mapped_column(
        Enum(DealStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=DealStatus.NEW
    )
    value: Mapped[Optional[float]] = mapped_column(Float)  # Montant estimé
    
    # Suivi
    next_action_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_contact_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Owner (user qui gère le deal)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Source (d'où vient le lead)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Tags stockés en JSON: ["tag1", "tag2"]
    tags: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Lien avec ancien système (migration)
    legacy_opportunity_id: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="deal", uselist=False)
    tasks: Mapped[List["AgencyTask"]] = relationship("AgencyTask", back_populates="deal", cascade="all, delete-orphan")


# ============================================================================
# PROJECT
# ============================================================================

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_status", "status"),
        Index("ix_projects_client_id", "client_id"),
        Index("ix_projects_deadline", "deadline"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relations
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client: Mapped["Client"] = relationship("Client", back_populates="projects")
    
    deal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deals.id"))
    deal: Mapped[Optional["Deal"]] = relationship("Deal", back_populates="project")
    
    # Infos projet
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=ProjectStatus.ACTIVE
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    budget: Mapped[Optional[float]] = mapped_column(Float)
    
    # Owner
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Workspace (multi-tenancy)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"))
    
    # Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Google Drive integration
    drive_folder_id: Mapped[Optional[str]] = mapped_column(String(100))
    brief_doc_id: Mapped[Optional[str]] = mapped_column(String(100))
    report_sheet_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Google Drive subfolder IDs
    drive_folder_assets: Mapped[Optional[str]] = mapped_column(String(100))  # 00_Assets
    drive_folder_brief: Mapped[Optional[str]] = mapped_column(String(100))
    drive_folder_production: Mapped[Optional[str]] = mapped_column(String(100))
    drive_folder_postprod: Mapped[Optional[str]] = mapped_column(String(100))
    drive_folder_exports: Mapped[Optional[str]] = mapped_column(String(100))
    drive_folder_admin: Mapped[Optional[str]] = mapped_column(String(100))
    drive_folder_livrables: Mapped[Optional[str]] = mapped_column(String(100))  # 07_Livrables
    drive_folder_archive: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Next action tracking
    next_action_text: Mapped[Optional[str]] = mapped_column(String(500))
    next_action_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Blocked reason (when status = BLOCKED)
    blocked_reason: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    deliverables: Mapped[List["Deliverable"]] = relationship("Deliverable", back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[List["AgencyTask"]] = relationship("AgencyTask", back_populates="project", cascade="all, delete-orphan")
    events: Mapped[List["CalendarEvent"]] = relationship("CalendarEvent", back_populates="project", cascade="all, delete-orphan")
    activity_logs: Mapped[List["ProjectActivityLog"]] = relationship("ProjectActivityLog", back_populates="project", cascade="all, delete-orphan")


# ============================================================================
# DELIVERABLE
# ============================================================================

class Deliverable(Base):
    __tablename__ = "deliverables"
    __table_args__ = (
        Index("ix_deliverables_project_id", "project_id"),
        Index("ix_deliverables_status", "status"),
        Index("ix_deliverables_due_date", "due_date"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relation projet
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["Project"] = relationship("Project", back_populates="deliverables")
    
    # Infos
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(100))  # video, design, document, etc.
    status: Mapped[DeliverableStatus] = mapped_column(
        Enum(DeliverableStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=DeliverableStatus.DRAFT
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    link: Mapped[Optional[str]] = mapped_column(String(1000))
    drive_file_id: Mapped[Optional[str]] = mapped_column(String(100))  # Google Drive file ID
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="deliverable", cascade="all, delete-orphan")


# ============================================================================
# APPROVAL
# ============================================================================

class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_deliverable_id", "deliverable_id"),
        Index("ix_approvals_status", "status"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relation livrable
    deliverable_id: Mapped[int] = mapped_column(ForeignKey("deliverables.id"), nullable=False)
    deliverable: Mapped["Deliverable"] = relationship("Deliverable", back_populates="approvals")
    
    # Statut
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=ApprovalStatus.PENDING
    )
    
    # Feedback
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))


# ============================================================================
# ASSET TYPE ENUM
# ============================================================================

class AssetType(str, enum.Enum):
    DRIVE = "DRIVE"
    FIGMA = "FIGMA"
    DROPBOX = "DROPBOX"
    YOUTUBE = "YOUTUBE"
    LINK = "LINK"
    DOC = "DOC"
    SHEET = "SHEET"
    OTHER = "OTHER"


class AssetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"


# ============================================================================
# ASSET
# ============================================================================

class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_project_id", "project_id"),
        Index("ix_assets_kind", "kind"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relation projet
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    
    # Workspace (multi-tenancy)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"))
    
    # Infos - legacy fields (kept for compatibility)
    kind: Mapped[AssetKind] = mapped_column(
        Enum(AssetKind, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=AssetKind.LINK
    )
    asset_type: Mapped[Optional[str]] = mapped_column(String(50))  # brief, report, template, other (legacy)
    
    # Infos - new unified fields
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(50))  # DRIVE, FIGMA, DROPBOX, YOUTUBE, LINK, DOC, SHEET, OTHER
    version: Mapped[Optional[str]] = mapped_column(String(50))  # v1, v2, final, etc.
    status: Mapped[Optional[str]] = mapped_column(String(20))  # DRAFT, FINAL
    
    # Google Drive integration
    drive_file_id: Mapped[Optional[str]] = mapped_column(String(255))
    drive_folder_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


# ============================================================================
# TASK (Production)
# ============================================================================

class AgencyTask(Base):
    __tablename__ = "agency_tasks"
    __table_args__ = (
        Index("ix_agency_tasks_project_id", "project_id"),
        Index("ix_agency_tasks_deal_id", "deal_id"),
        Index("ix_agency_tasks_status", "status"),
        Index("ix_agency_tasks_priority", "priority"),
        Index("ix_agency_tasks_due_date", "due_date"),
        Index("ix_agency_tasks_assignee_id", "assignee_id"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relations (optionnelles)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks")
    
    deal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deals.id"))
    deal: Mapped[Optional["Deal"]] = relationship("Deal", back_populates="tasks")
    
    # Infos
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=TaskStatus.TODO
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=TaskPriority.MEDIUM
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Assignee
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Auto-generated (pour relances auto)
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_type: Mapped[Optional[str]] = mapped_column(String(50))  # "followup", "deadline_alert", etc.
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# CALENDAR EVENT
# ============================================================================

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        Index("ix_calendar_events_project_id", "project_id"),
        Index("ix_calendar_events_start", "start"),
        Index("ix_calendar_events_type", "type"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relation projet (optionnel)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="events")
    
    # Infos événement
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=CalendarEventType.OTHER
    )
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Détails
    location: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# PROJECT ACTIVITY LOG
# ============================================================================

class ActivityType(str, enum.Enum):
    CREATION = "creation"
    UPDATE = "update"
    VALIDATION = "validation"
    DELIVERY = "delivery"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    DELIVERABLE_ADDED = "deliverable_added"
    TASK_COMPLETED = "task_completed"


class ProjectActivityLog(Base):
    """Activity log specific to a project timeline"""
    __tablename__ = "project_activity_logs"
    __table_args__ = (
        Index("ix_project_activity_logs_project_id", "project_id"),
        Index("ix_project_activity_logs_created_at", "created_at"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Relation projet
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project: Mapped["Project"] = relationship("Project", back_populates="activity_logs")
    
    # Log content
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    activity_type: Mapped[Optional[ActivityType]] = mapped_column(
        Enum(ActivityType, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=True
    )
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
