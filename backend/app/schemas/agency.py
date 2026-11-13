"""
Pydantic schemas for Agency Cockpit V2
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class DealStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTE_SENT = "quote_sent"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DELIVERED = "delivered"
    ARCHIVED = "archived"


class DeliverableStatus(str, Enum):
    DRAFT = "draft"
    TO_REVIEW = "to_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    DELIVERED = "delivered"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    CHANGES = "changes"
    APPROVED = "approved"


class AssetKind(str, Enum):
    LINK = "link"
    FILE = "file"


class TaskStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CalendarEventType(str, Enum):
    SHOOT = "shoot"
    DELIVERY = "delivery"
    MEETING = "meeting"
    DEADLINE = "deadline"
    OTHER = "other"


# ============================================================================
# CLIENT SCHEMAS
# ============================================================================

class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None


class ClientBase(BaseModel):
    name: str
    contacts: List[ContactInfo] = []
    
    # Address fields
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "France"
    
    # Legal info
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    
    # Banking info (IBAN is encrypted when stored)
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None
    
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contacts: Optional[List[ContactInfo]] = None
    
    # Address fields
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Legal info
    siret: Optional[str] = None
    vat_number: Optional[str] = None
    
    # Banking info (IBAN is encrypted when stored)
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None
    
    notes: Optional[str] = None


class ClientResponse(ClientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Banking info (masked for display)
    iban_masked: Optional[str] = None
    
    # Computed fields for dashboard
    active_deals_count: int = 0
    active_projects_count: int = 0
    total_value: float = 0

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    id: int
    name: str
    contacts: List[Any] = []
    active_deals_count: int = 0
    active_projects_count: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# DEAL SCHEMAS
# ============================================================================

class DealBase(BaseModel):
    client_id: int
    title: str
    status: DealStatus = DealStatus.NEW
    value: Optional[float] = None
    next_action_date: Optional[datetime] = None
    source: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    client_id: Optional[int] = None
    title: Optional[str] = None
    status: Optional[DealStatus] = None
    value: Optional[float] = None
    next_action_date: Optional[datetime] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class DealResponse(DealBase):
    id: int
    owner_id: Optional[int] = None
    last_contact_at: Optional[datetime] = None
    legacy_opportunity_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Nested
    client_name: Optional[str] = None
    owner_name: Optional[str] = None
    days_since_contact: Optional[int] = None

    class Config:
        from_attributes = True


class DealListResponse(BaseModel):
    id: int
    title: str
    status: DealStatus
    value: Optional[float] = None
    client_id: int
    client_name: Optional[str] = None
    next_action_date: Optional[datetime] = None
    last_contact_at: Optional[datetime] = None
    days_since_contact: Optional[int] = None
    owner_name: Optional[str] = None
    tags: List[str] = []

    class Config:
        from_attributes = True


# ============================================================================
# PROJECT SCHEMAS
# ============================================================================

class ProjectBase(BaseModel):
    client_id: Optional[int] = None  # Optional for quick project creation
    deal_id: Optional[int] = None
    name: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    deadline: Optional[datetime] = None
    budget: Optional[float] = None
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    client_id: Optional[int] = None
    deal_id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    deadline: Optional[datetime] = None
    budget: Optional[float] = None
    description: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Google Drive integration
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    brief_doc_id: Optional[str] = None
    brief_doc_url: Optional[str] = None
    report_sheet_id: Optional[str] = None
    report_sheet_url: Optional[str] = None
    
    # Computed
    client_name: Optional[str] = None
    owner_name: Optional[str] = None
    deliverables_count: int = 0
    deliverables_approved: int = 0
    progress_percent: int = 0
    days_until_deadline: Optional[int] = None
    is_urgent: bool = False

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    id: int
    name: str
    status: ProjectStatus
    client_id: int
    client_name: Optional[str] = None
    deadline: Optional[datetime] = None
    days_until_deadline: Optional[int] = None
    is_urgent: bool = False
    progress_percent: int = 0
    deliverables_count: int = 0
    deliverables_approved: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# DELIVERABLE SCHEMAS
# ============================================================================

class DeliverableBase(BaseModel):
    project_id: int
    name: str
    type: Optional[str] = None
    status: DeliverableStatus = DeliverableStatus.DRAFT
    due_date: Optional[datetime] = None
    link: Optional[str] = None
    notes: Optional[str] = None


class DeliverableCreate(DeliverableBase):
    pass


class DeliverableUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[DeliverableStatus] = None
    due_date: Optional[datetime] = None
    link: Optional[str] = None
    notes: Optional[str] = None


class DeliverableResponse(DeliverableBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed
    project_name: Optional[str] = None
    client_name: Optional[str] = None
    has_pending_approval: bool = False
    days_until_due: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================================
# APPROVAL SCHEMAS
# ============================================================================

class ApprovalBase(BaseModel):
    deliverable_id: int
    status: ApprovalStatus = ApprovalStatus.PENDING
    feedback: Optional[str] = None


class ApprovalCreate(ApprovalBase):
    pass


class ApprovalUpdate(BaseModel):
    status: Optional[ApprovalStatus] = None
    feedback: Optional[str] = None


class ApprovalResponse(ApprovalBase):
    id: int
    requested_at: datetime
    decided_at: Optional[datetime] = None
    decided_by: Optional[int] = None
    
    # Computed
    deliverable_name: Optional[str] = None
    project_name: Optional[str] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# ASSET SCHEMAS
# ============================================================================

class AssetBase(BaseModel):
    project_id: int
    kind: AssetKind = AssetKind.LINK
    name: str
    url: str
    version: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    kind: Optional[AssetKind] = None
    name: Optional[str] = None
    url: Optional[str] = None
    version: Optional[str] = None


class AssetResponse(AssetBase):
    id: int
    created_at: datetime
    created_by: Optional[int] = None
    
    # Computed
    project_name: Optional[str] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskBase(BaseModel):
    project_id: Optional[int] = None
    deal_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    project_id: Optional[int] = None
    deal_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    is_auto_generated: bool = False
    auto_type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed
    project_name: Optional[str] = None
    deal_title: Optional[str] = None
    client_name: Optional[str] = None
    assignee_name: Optional[str] = None
    is_overdue: bool = False

    class Config:
        from_attributes = True


# ============================================================================
# CALENDAR EVENT SCHEMAS
# ============================================================================

class CalendarEventBase(BaseModel):
    project_id: Optional[int] = None
    title: str
    type: CalendarEventType = CalendarEventType.OTHER
    start: datetime
    end: Optional[datetime] = None
    all_day: bool = False
    location: Optional[str] = None
    notes: Optional[str] = None


class CalendarEventCreate(CalendarEventBase):
    pass


class CalendarEventUpdate(BaseModel):
    project_id: Optional[int] = None
    title: Optional[str] = None
    type: Optional[CalendarEventType] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class CalendarEventResponse(CalendarEventBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed
    project_name: Optional[str] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# DASHBOARD V2 SCHEMAS
# ============================================================================

class TodoItem(BaseModel):
    """Item for "À faire aujourd'hui" block"""
    id: int
    type: str  # 'followup', 'validation', 'task', 'deadline'
    title: str
    subtitle: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    link: Optional[str] = None


class UrgencyItem(BaseModel):
    """Item for "Urgences" block"""
    id: int
    type: str  # 'deadline', 'blocked_project', 'overdue_task'
    title: str
    subtitle: Optional[str] = None
    deadline: Optional[datetime] = None
    days_remaining: Optional[int] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    severity: str = "warning"  # 'warning', 'danger'


class BusinessItem(BaseModel):
    """Item for "Business" block"""
    id: int
    type: str  # 'hot_lead', 'quote_sent', 'won_deal'
    title: str
    subtitle: Optional[str] = None
    value: Optional[float] = None
    client_name: Optional[str] = None
    status: Optional[str] = None
    days_waiting: Optional[int] = None


class DashboardV2Response(BaseModel):
    """Dashboard V2 - 3 blocks response"""
    # Block A: À faire aujourd'hui
    todos: List[TodoItem] = []
    todos_count: int = 0
    
    # Block B: Urgences
    urgencies: List[UrgencyItem] = []
    urgencies_count: int = 0
    
    # Block C: Business
    business: List[BusinessItem] = []
    business_count: int = 0
    
    # Quick stats
    active_projects: int = 0
    pending_validations: int = 0
    hot_leads: Optional[int] = None
    monthly_revenue: Optional[float] = None


# ============================================================================
# PIPELINE SCHEMAS
# ============================================================================

class PipelineColumn(BaseModel):
    status: DealStatus
    label: str
    deals: List[DealListResponse] = []
    count: int = 0
    total_value: float = 0


class PipelineResponse(BaseModel):
    columns: List[PipelineColumn] = []
    total_deals: int = 0
    total_value: float = 0


# ============================================================================
# PRODUCTION SCHEMAS  
# ============================================================================

class ProductionItem(BaseModel):
    """Item in production kanban"""
    id: int
    name: str
    type: Optional[str] = None
    status: DeliverableStatus
    due_date: Optional[datetime] = None
    days_until_due: Optional[int] = None
    is_urgent: bool = False
    project_id: int
    project_name: str
    client_name: str
    has_pending_approval: bool = False
    link: Optional[str] = None


class ProductionColumn(BaseModel):
    status: DeliverableStatus
    label: str
    items: List[ProductionItem] = []
    count: int = 0


class ProductionResponse(BaseModel):
    columns: List[ProductionColumn] = []
    total_items: int = 0
