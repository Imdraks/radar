"""
Workspace & InboxItem Models
Multi-user workspace for team collaboration with Google Drive integration
"""
import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, Enum, JSON, Date, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base
from app.core.subscription import PLAN_CONFIGS, Plan

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.agency import Client, Deal, Project, AgencyTask


# ============================================================================
# ENUMS
# ============================================================================

class WorkspaceRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InboxStatus(str, enum.Enum):
    INBOX = "inbox"
    TRIAGED = "triaged"
    DONE = "done"
    ARCHIVED = "archived"


class InboxType(str, enum.Enum):
    IDEA = "idea"
    REQUEST = "request"
    BUG = "bug"
    CONTENT = "content"
    TASK = "task"
    OTHER = "other"


# ============================================================================
# WORKSPACE
# ============================================================================

class Workspace(Base):
    """
    Workspace for team collaboration.
    Each workspace has its own Google Drive structure and templates.
    """
    __tablename__ = "workspaces"
    __table_args__ = (
        Index("ix_workspaces_owner_user_id", "owner_user_id"),
        Index("ix_workspaces_name", "name"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Google Drive Integration
    drive_root_folder_id: Mapped[Optional[str]] = mapped_column(String(255))
    templates_folder_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Google Templates (Doc/Sheet IDs)
    brief_template_doc_id: Mapped[Optional[str]] = mapped_column(String(255))
    report_template_sheet_id: Mapped[Optional[str]] = mapped_column(String(255))
    devis_template_doc_id: Mapped[Optional[str]] = mapped_column(String(255))
    facture_template_doc_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Google Calendar
    calendar_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # =========== BILLING EMITTER INFO (Radar Business) ===========
    # Company/Legal info for quotes and invoices
    legal_name: Mapped[Optional[str]] = mapped_column(String(255))  # Nom société
    legal_address: Mapped[Optional[str]] = mapped_column(String(500))  # Adresse complète
    legal_city: Mapped[Optional[str]] = mapped_column(String(100))
    legal_postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    legal_country: Mapped[Optional[str]] = mapped_column(String(100), default="France")
    legal_phone: Mapped[Optional[str]] = mapped_column(String(50))
    legal_email: Mapped[Optional[str]] = mapped_column(String(255))
    siret: Mapped[Optional[str]] = mapped_column(String(20))
    vat_number: Mapped[Optional[str]] = mapped_column(String(30))
    forme_juridique: Mapped[Optional[str]] = mapped_column(String(50))  # SAS, SARL, EURL, EI, SASU, SA, SCI
    capital_social: Mapped[Optional[str]] = mapped_column(String(50))  # "10 000 €"
    rcs_city: Mapped[Optional[str]] = mapped_column(String(100))  # Ville d'immatriculation RCS
    tva_franchise: Mapped[Optional[bool]] = mapped_column(default=False)  # Franchise de base TVA (art. 293 B)
    logo_drive_file_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Payment info (IBAN, BIC, payment instructions)
    payment_info: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # Example: {"iban": "FR76...", "bic": "BNPAFRPP", "bank_name": "BNP Paribas", "instructions": "..."}
    
    # Settings (JSON for extensibility)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # =========== SUBSCRIPTION ===========
    # Plan: mini, standard, premium
    plan: Mapped[str] = mapped_column(String(20), default="core", nullable=False)
    
    # Enabled packs (JSON array): ["core", "clients", "leads", "talents"]
    enabled_packs: Mapped[list] = mapped_column(JSON, default=lambda: ["core"])
    
    # Add-ons (JSON array): ["radar_business"]
    addons: Mapped[list] = mapped_column(JSON, default=list)
    
    # Seat limits
    max_seats: Mapped[int] = mapped_column(default=PLAN_CONFIGS[Plan.CORE].max_seats)
    
    # Billing (Stripe)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255))
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_user_id], backref="owned_workspaces")
    members: Mapped[List["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    inbox_items: Mapped[List["InboxItem"]] = relationship("InboxItem", back_populates="workspace", cascade="all, delete-orphan")
    
    @property
    def drive_url(self) -> Optional[str]:
        """Get Google Drive folder URL"""
        if self.drive_root_folder_id:
            return f"https://drive.google.com/drive/folders/{self.drive_root_folder_id}"
        return None


# ============================================================================
# WORKSPACE MEMBER
# ============================================================================

class WorkspaceMember(Base):
    """
    Member of a workspace with a specific role.
    """
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        Index("ix_workspace_members_workspace_id", "workspace_id"),
        Index("ix_workspace_members_user_id", "user_id"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole, values_callable=lambda x: [e.value for e in x], name="workspacerole", create_type=False), default=WorkspaceRole.MEMBER)
    
    # Invite info
    invited_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], backref="workspace_memberships")


# ============================================================================
# WORKSPACE INVITE (Authorized Emails)
# ============================================================================

class WorkspaceInvite(Base):
    """
    Authorized email for a workspace.
    When a user signs up/logs in with this email, they are auto-added to the workspace.
    """
    __tablename__ = "workspace_invites"
    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_workspace_invite_email"),
        Index("ix_workspace_invites_email", "email"),
        Index("ix_workspace_invites_workspace_id", "workspace_id"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="member")
    
    # Tracking
    invited_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    claimed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", backref="invites")


# ============================================================================
# INBOX ITEM
# ============================================================================

class InboxItem(Base):
    """
    Quick capture item for ideas, tasks, bugs, etc.
    Can be triaged to Task, Deal, Project, or Deliverable.
    """
    __tablename__ = "inbox_items"
    __table_args__ = (
        Index("ix_inbox_items_workspace_id", "workspace_id"),
        Index("ix_inbox_items_status", "status"),
        Index("ix_inbox_items_created_by", "created_by"),
        Index("ix_inbox_items_created_at", "created_at"),
        Index("ix_inbox_items_due_date", "due_date"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(2000))
    
    # Classification
    type: Mapped[InboxType] = mapped_column(
        Enum(InboxType, values_callable=lambda x: [e.value for e in x]), 
        default=InboxType.OTHER
    )
    tags: Mapped[Optional[dict]] = mapped_column(JSON, default=list)  # ["tag1", "tag2"]
    
    # Status
    status: Mapped[InboxStatus] = mapped_column(
        Enum(InboxStatus, values_callable=lambda x: [e.value for e in x]), 
        default=InboxStatus.INBOX
    )
    
    # Due date (optional, parsed from "due:YYYY-MM-DD")
    due_date: Mapped[Optional[datetime]] = mapped_column(Date)
    
    # Triage info (when converted to Task/Deal/Project)
    triaged_to_type: Mapped[Optional[str]] = mapped_column(String(50))
    triaged_to_id: Mapped[Optional[int]] = mapped_column(Integer)
    triaged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    triaged_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Parsing hints (extracted from text)
    mentioned_client: Mapped[Optional[str]] = mapped_column(String(255))
    mentioned_project: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="inbox_items")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], backref="inbox_items")
    
    @classmethod
    def parse_text(cls, text: str) -> dict:
        """
        Parse text for tags, due dates, and type hints.
        Format: "Text content @client #project due:2026-01-25 type:idea"
        """
        import re
        
        result = {
            "clean_text": text,
            "mentioned_client": None,
            "mentioned_project": None,
            "due_date": None,
            "type": InboxType.OTHER,
            "tags": []
        }
        
        # Extract @client
        client_match = re.search(r'@(\w+)', text)
        if client_match:
            result["mentioned_client"] = client_match.group(1)
            text = text.replace(client_match.group(0), "").strip()
        
        # Extract #project or #tag
        tag_matches = re.findall(r'#(\w+)', text)
        if tag_matches:
            result["tags"] = tag_matches
            # First tag might be project name
            if tag_matches:
                result["mentioned_project"] = tag_matches[0]
            for match in tag_matches:
                text = text.replace(f"#{match}", "").strip()
        
        # Extract due:YYYY-MM-DD
        due_match = re.search(r'due:(\d{4}-\d{2}-\d{2})', text)
        if due_match:
            from datetime import datetime as dt
            try:
                result["due_date"] = dt.strptime(due_match.group(1), "%Y-%m-%d").date()
            except ValueError:
                pass
            text = text.replace(due_match.group(0), "").strip()
        
        # Extract type:xxx
        type_match = re.search(r'type:(\w+)', text)
        if type_match:
            type_str = type_match.group(1).lower()
            type_map = {
                "idea": InboxType.IDEA,
                "idee": InboxType.IDEA,
                "request": InboxType.REQUEST,
                "demande": InboxType.REQUEST,
                "bug": InboxType.BUG,
                "content": InboxType.CONTENT,
                "contenu": InboxType.CONTENT,
                "task": InboxType.TASK,
                "tache": InboxType.TASK,
            }
            result["type"] = type_map.get(type_str, InboxType.OTHER)
            text = text.replace(type_match.group(0), "").strip()
        
        result["clean_text"] = text
        return result
