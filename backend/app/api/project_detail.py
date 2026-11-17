"""
API for Project Detail Page
Complete endpoints for the project view with 4 tabs:
- Overview (next action, blockers, today tasks, pending validations, timeline)
- Deliverables (CRUD with status management)
- Production (Kanban tasks)
- Assets (Drive links and files)
"""
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_
from pydantic import BaseModel
from enum import Enum

from app.db.session import get_db
from app.db.models.agency import (
    Project, Deliverable, Approval, Asset, AgencyTask, ProjectActivityLog,
    ProjectStatus, DeliverableStatus, ApprovalStatus, TaskStatus, TaskPriority,
    ActivityType, Client
)
from app.db.models.user import User
from app.api.deps import get_current_user, resolve_workspace_id
from app.services.google_workspace import get_google_workspace_service, TokenExpiredError
from app.core.cache import cache_get

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agency/projects", tags=["project-detail"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ActivityTypeEnum(str, Enum):
    CREATION = "creation"
    UPDATE = "update"
    VALIDATION = "validation"
    DELIVERY = "delivery"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    DELIVERABLE_ADDED = "deliverable_added"
    TASK_COMPLETED = "task_completed"


class ProjectDetailResponse(BaseModel):
    """Complete project response for the detail page header"""
    id: int
    name: str
    client_id: int
    client_name: Optional[str] = None
    status: str
    deadline: Optional[datetime] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    
    # Google Drive
    drive_folder_id: Optional[str] = None
    brief_doc_id: Optional[str] = None
    report_sheet_id: Optional[str] = None
    
    # Next action
    next_action_text: Optional[str] = None
    next_action_due_date: Optional[datetime] = None
    
    # Blocked
    blocked_reason: Optional[str] = None
    
    # Computed stats
    progress_percent: int = 0
    deliverables_total: int = 0
    deliverables_approved: int = 0
    tasks_todo: int = 0
    tasks_doing: int = 0
    tasks_done: int = 0
    pending_validations: int = 0
    days_until_deadline: Optional[int] = None
    is_urgent: bool = False
    
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OverviewResponse(BaseModel):
    """Overview tab data"""
    next_action_text: Optional[str] = None
    next_action_due_date: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    
    # Today's tasks for this project
    today_tasks: List[dict] = []
    
    # Pending validations
    pending_validations: List[dict] = []
    
    # Recent activity
    recent_activity: List[dict] = []


class DeliverableDetailResponse(BaseModel):
    """Deliverable response for the detail table"""
    id: int
    name: str
    type: Optional[str] = None
    status: str
    due_date: Optional[datetime] = None
    link: Optional[str] = None
    drive_file_id: Optional[str] = None
    notes: Optional[str] = None
    has_pending_approval: bool = False
    days_until_due: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeliverableCreateRequest(BaseModel):
    name: str
    type: Optional[str] = None
    status: str = "draft"
    due_date: Optional[datetime] = None
    link: Optional[str] = None
    drive_file_id: Optional[str] = None
    notes: Optional[str] = None


class DeliverableUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    link: Optional[str] = None
    drive_file_id: Optional[str] = None
    notes: Optional[str] = None


class TaskDetailResponse(BaseModel):
    """Task response for Kanban"""
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None


class AssetDetailResponse(BaseModel):
    """Asset response"""
    id: int
    kind: str
    name: str
    url: str
    version: Optional[str] = None
    asset_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssetCreateRequest(BaseModel):
    kind: str = "link"
    name: str
    url: str
    version: Optional[str] = None
    asset_type: Optional[str] = None


class ActivityLogResponse(BaseModel):
    """Activity log response"""
    id: int
    message: str
    activity_type: Optional[str] = None
    created_at: datetime
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectUpdateRequest(BaseModel):
    """Partial project update"""
    name: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    next_action_text: Optional[str] = None
    next_action_due_date: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    drive_folder_id: Optional[str] = None
    brief_doc_id: Optional[str] = None
    report_sheet_id: Optional[str] = None


# ============================================================================
# HELPER: Log activity
# ============================================================================

def log_project_activity(
    db: Session,
    project_id: int,
    message: str,
    activity_type: ActivityType,
    user_id: Optional[int] = None
):
    """Create a project activity log entry"""
    log = ProjectActivityLog(
        project_id=project_id,
        message=message,
        activity_type=activity_type,
        created_by=user_id
    )
    db.add(log)
    db.commit()
    return log


# ============================================================================
# PROJECT DETAIL ENDPOINTS
# ============================================================================

@router.get("/{project_id}/detail", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete project details for the header"""
    project = db.query(Project).options(
        joinedload(Project.client)
    ).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get owner separately
    owner = db.query(User).filter(User.id == project.owner_id).first() if project.owner_id else None
    
    now = datetime.utcnow()
    
    # Count deliverables
    total_deliverables = db.query(func.count(Deliverable.id)).filter(
        Deliverable.project_id == project_id
    ).scalar() or 0
    
    approved_deliverables = db.query(func.count(Deliverable.id)).filter(
        Deliverable.project_id == project_id,
        Deliverable.status.in_([DeliverableStatus.APPROVED, DeliverableStatus.DELIVERED])
    ).scalar() or 0
    
    # Count tasks by status
    tasks_todo = db.query(func.count(AgencyTask.id)).filter(
        AgencyTask.project_id == project_id,
        AgencyTask.status == TaskStatus.TODO
    ).scalar() or 0
    
    tasks_doing = db.query(func.count(AgencyTask.id)).filter(
        AgencyTask.project_id == project_id,
        AgencyTask.status == TaskStatus.DOING
    ).scalar() or 0
    
    tasks_done = db.query(func.count(AgencyTask.id)).filter(
        AgencyTask.project_id == project_id,
        AgencyTask.status == TaskStatus.DONE
    ).scalar() or 0
    
    # Pending validations
    pending_count = db.query(func.count(Approval.id)).join(Deliverable).filter(
        Deliverable.project_id == project_id,
        Approval.status == ApprovalStatus.PENDING
    ).scalar() or 0
    
    progress = int((approved_deliverables / total_deliverables * 100)) if total_deliverables > 0 else 0
    
    days_until = None
    is_urgent = False
    if project.deadline:
        days_until = (project.deadline - now).days
        is_urgent = 0 <= days_until <= 3
    
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        client_id=project.client_id,
        client_name=project.client.name if project.client else None,
        status=project.status.value,
        deadline=project.deadline,
        owner_id=project.owner_id,
        owner_name=owner.full_name or owner.email if owner else None,
        description=project.description,
        budget=project.budget,
        drive_folder_id=project.drive_folder_id,
        brief_doc_id=project.brief_doc_id,
        report_sheet_id=project.report_sheet_id,
        next_action_text=project.next_action_text,
        next_action_due_date=project.next_action_due_date,
        blocked_reason=project.blocked_reason,
        progress_percent=progress,
        deliverables_total=total_deliverables,
        deliverables_approved=approved_deliverables,
        tasks_todo=tasks_todo,
        tasks_doing=tasks_doing,
        tasks_done=tasks_done,
        pending_validations=pending_count,
        days_until_deadline=days_until,
        is_urgent=is_urgent,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get("/{project_id}/overview", response_model=OverviewResponse)
async def get_project_overview(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overview tab data: next action, blockers, today tasks, validations, timeline"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Today's tasks
    today_tasks = db.query(AgencyTask).filter(
        AgencyTask.project_id == project_id,
        AgencyTask.status != TaskStatus.DONE,
        or_(
            AgencyTask.due_date == None,
            AgencyTask.due_date <= today_end
        )
    ).order_by(AgencyTask.priority.desc(), AgencyTask.due_date).limit(10).all()
    
    today_tasks_data = [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "priority": t.priority.value,
            "due_date": t.due_date.isoformat() if t.due_date else None
        }
        for t in today_tasks
    ]
    
    # Pending validations
    pending_approvals = db.query(Approval).join(Deliverable).filter(
        Deliverable.project_id == project_id,
        Approval.status == ApprovalStatus.PENDING
    ).all()
    
    pending_data = []
    for approval in pending_approvals:
        deliverable = db.query(Deliverable).filter(Deliverable.id == approval.deliverable_id).first()
        if deliverable:
            pending_data.append({
                "id": approval.id,
                "deliverable_id": deliverable.id,
                "deliverable_name": deliverable.name,
                "requested_at": approval.requested_at.isoformat() if approval.requested_at else None
            })
    
    # Recent activity (last 20)
    activities = db.query(ProjectActivityLog).filter(
        ProjectActivityLog.project_id == project_id
    ).order_by(desc(ProjectActivityLog.created_at)).limit(20).all()
    
    activity_data = []
    for a in activities:
        creator = db.query(User).filter(User.id == a.created_by).first() if a.created_by else None
        activity_data.append({
            "id": a.id,
            "message": a.message,
            "activity_type": a.activity_type.value if a.activity_type else None,
            "created_at": a.created_at.isoformat(),
            "created_by_name": creator.full_name or creator.email if creator else None
        })
    
    return OverviewResponse(
        next_action_text=project.next_action_text,
        next_action_due_date=project.next_action_due_date,
        blocked_reason=project.blocked_reason,
        today_tasks=today_tasks_data,
        pending_validations=pending_data,
        recent_activity=activity_data
    )


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
async def update_project_detail(
    project_id: int,
    data: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project fields (partial update)"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    changes = []
    
    if data.name is not None:
        project.name = data.name
        changes.append("Nom mis à jour")
    if data.status is not None:
        old_status = project.status.value
        project.status = data.status
        changes.append(f"Statut changé: {old_status} → {data.status}")
    if data.deadline is not None:
        project.deadline = data.deadline
        changes.append("Deadline mise à jour")
    if data.description is not None:
        project.description = data.description
    if data.next_action_text is not None:
        project.next_action_text = data.next_action_text
        changes.append("Prochaine action définie")
    if data.next_action_due_date is not None:
        project.next_action_due_date = data.next_action_due_date
    if data.blocked_reason is not None:
        project.blocked_reason = data.blocked_reason
        if data.blocked_reason:
            changes.append(f"Bloqué: {data.blocked_reason}")
    if data.drive_folder_id is not None:
        project.drive_folder_id = data.drive_folder_id
    if data.brief_doc_id is not None:
        project.brief_doc_id = data.brief_doc_id
    if data.report_sheet_id is not None:
        project.report_sheet_id = data.report_sheet_id
    
    db.commit()
    
    # Log changes
    if changes:
        log_project_activity(
            db, project_id,
            " | ".join(changes),
            ActivityType.UPDATE,
            current_user.id
        )
    
    return await get_project_detail(project_id, db, current_user)


# ============================================================================
# DRIVE FOLDERS ENDPOINT
# ============================================================================

class DriveFolderInfo(BaseModel):
    key: str
    label: str
    folder_id: Optional[str] = None


class DriveFoldersResponse(BaseModel):
    project_id: int
    drive_folder_id: Optional[str] = None
    folders: List[DriveFolderInfo] = []


@router.get("/{project_id}/drive-folders", response_model=DriveFoldersResponse)
async def get_project_drive_folders(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the list of Drive subfolders for a project (used for file upload destination)"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    folders = [
        DriveFolderInfo(key="assets", label="00_Assets", folder_id=project.drive_folder_assets),
        DriveFolderInfo(key="brief", label="01_Brief", folder_id=project.drive_folder_brief),
        DriveFolderInfo(key="production", label="02_Production", folder_id=project.drive_folder_production),
        DriveFolderInfo(key="postprod", label="03_PostProd", folder_id=project.drive_folder_postprod),
        DriveFolderInfo(key="exports", label="04_Exports", folder_id=project.drive_folder_exports),
        DriveFolderInfo(key="admin", label="05_Admin", folder_id=project.drive_folder_admin),
        DriveFolderInfo(key="livrables", label="07_Livrables", folder_id=project.drive_folder_livrables),
        DriveFolderInfo(key="archive", label="99_Archive", folder_id=project.drive_folder_archive),
    ]
    
    return DriveFoldersResponse(
        project_id=project_id,
        drive_folder_id=project.drive_folder_id,
        folders=folders
    )


# ============================================================================
# DELIVERABLES ENDPOINTS
# ============================================================================

@router.get("/{project_id}/deliverables", response_model=List[DeliverableDetailResponse])
async def get_project_deliverables(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all deliverables for a project"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    now = datetime.utcnow()
    deliverables = db.query(Deliverable).filter(
        Deliverable.project_id == project_id
    ).order_by(Deliverable.due_date, Deliverable.created_at).all()
    
    result = []
    for d in deliverables:
        has_pending = db.query(func.count(Approval.id)).filter(
            Approval.deliverable_id == d.id,
            Approval.status == ApprovalStatus.PENDING
        ).scalar() > 0
        
        days_until = None
        if d.due_date:
            days_until = (d.due_date - now).days
        
        result.append(DeliverableDetailResponse(
            id=d.id,
            name=d.name,
            type=d.type,
            status=d.status.value,
            due_date=d.due_date,
            link=d.link,
            drive_file_id=d.drive_file_id,
            notes=d.notes,
            has_pending_approval=has_pending,
            days_until_due=days_until,
            created_at=d.created_at,
            updated_at=d.updated_at
        ))
    
    return result


@router.post("/{project_id}/deliverables", response_model=DeliverableDetailResponse)
async def create_project_deliverable(
    project_id: int,
    data: DeliverableCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new deliverable for the project"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    deliverable = Deliverable(
        project_id=project_id,
        name=data.name,
        type=data.type,
        status=DeliverableStatus(data.status),
        due_date=data.due_date,
        link=data.link,
        drive_file_id=data.drive_file_id,
        notes=data.notes
    )
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    
    # Log activity
    log_project_activity(
        db, project_id,
        f"Livrable ajouté: {data.name}",
        ActivityType.DELIVERABLE_ADDED,
        current_user.id
    )
    
    return DeliverableDetailResponse(
        id=deliverable.id,
        name=deliverable.name,
        type=deliverable.type,
        status=deliverable.status.value,
        due_date=deliverable.due_date,
        link=deliverable.link,
        drive_file_id=deliverable.drive_file_id,
        notes=deliverable.notes,
        has_pending_approval=False,
        days_until_due=None,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at
    )


@router.patch("/deliverables/{deliverable_id}", response_model=DeliverableDetailResponse)
async def update_deliverable(
    deliverable_id: int,
    data: DeliverableUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a deliverable"""
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id, Deliverable.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    old_status = deliverable.status.value
    
    if data.name is not None:
        deliverable.name = data.name
    if data.type is not None:
        deliverable.type = data.type
    if data.status is not None:
        deliverable.status = DeliverableStatus(data.status)
    if data.due_date is not None:
        deliverable.due_date = data.due_date
    if data.link is not None:
        deliverable.link = data.link
    if data.drive_file_id is not None:
        deliverable.drive_file_id = data.drive_file_id
    if data.notes is not None:
        deliverable.notes = data.notes
    
    db.commit()
    db.refresh(deliverable)
    
    # Log status change
    if data.status and data.status != old_status:
        activity_type = ActivityType.VALIDATION if data.status in ["approved", "delivered"] else ActivityType.UPDATE
        log_project_activity(
            db, deliverable.project_id,
            f"Livrable '{deliverable.name}': {old_status} → {data.status}",
            activity_type,
            current_user.id
        )
    
    now = datetime.utcnow()
    days_until = None
    if deliverable.due_date:
        days_until = (deliverable.due_date - now).days
    
    has_pending = db.query(func.count(Approval.id)).filter(
        Approval.deliverable_id == deliverable.id,
        Approval.status == ApprovalStatus.PENDING
    ).scalar() > 0
    
    return DeliverableDetailResponse(
        id=deliverable.id,
        name=deliverable.name,
        type=deliverable.type,
        status=deliverable.status.value,
        due_date=deliverable.due_date,
        link=deliverable.link,
        drive_file_id=deliverable.drive_file_id,
        notes=deliverable.notes,
        has_pending_approval=has_pending,
        days_until_due=days_until,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at
    )


@router.post("/deliverables/{deliverable_id}/request-validation")
async def request_deliverable_validation(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request validation for a deliverable"""
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id, Deliverable.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    # Update deliverable status
    deliverable.status = DeliverableStatus.TO_REVIEW
    
    # Create approval request
    approval = Approval(
        deliverable_id=deliverable_id,
        status=ApprovalStatus.PENDING
    )
    db.add(approval)
    db.commit()
    
    # Log activity
    log_project_activity(
        db, deliverable.project_id,
        f"Validation demandée: {deliverable.name}",
        ActivityType.UPDATE,
        current_user.id
    )
    
    return {"status": "success", "message": "Validation requested"}


@router.post("/deliverables/{deliverable_id}/approve")
async def approve_deliverable(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a deliverable"""
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id, Deliverable.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    # Update deliverable status
    deliverable.status = DeliverableStatus.APPROVED
    
    # Update pending approvals
    db.query(Approval).filter(
        Approval.deliverable_id == deliverable_id,
        Approval.status == ApprovalStatus.PENDING
    ).update({
        "status": ApprovalStatus.APPROVED,
        "decided_at": datetime.utcnow(),
        "decided_by": current_user.id
    })
    
    db.commit()
    
    # Log activity
    log_project_activity(
        db, deliverable.project_id,
        f"Livrable validé: {deliverable.name}",
        ActivityType.VALIDATION,
        current_user.id
    )
    
    return {"status": "success", "message": "Deliverable approved"}


@router.delete("/deliverables/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a deliverable and move its Drive file to project's 99_Archive folder"""
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id, Deliverable.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    project_id = deliverable.project_id
    name = deliverable.name
    drive_file_id = deliverable.drive_file_id
    
    # Get project archive folder
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    archive_folder_id = project.drive_folder_archive if project else None
    user_id = current_user.id
    
    db.delete(deliverable)
    db.commit()
    
    # Log activity
    log_project_activity(
        db, project_id,
        f"Livrable supprimé: {name}",
        ActivityType.UPDATE,
        current_user.id
    )
    
    # Move file to archive in background if it has a Drive file
    if drive_file_id and archive_folder_id:
        background_tasks.add_task(
            archive_deliverable_file,
            user_id=user_id,
            file_id=drive_file_id,
            archive_folder_id=archive_folder_id,
            deliverable_name=name
        )
    
    return {"status": "deleted"}


async def archive_deliverable_file(
    user_id: int,
    file_id: str,
    archive_folder_id: str,
    deliverable_name: str
):
    """Move a deliverable's Drive file to the project's archive folder"""
    try:
        token_data = await cache_get(f"google_tokens:{user_id}")
        if not token_data:
            logger.warning(f"No Google token for user {user_id}, cannot archive deliverable")
            return
        
        service = await get_google_workspace_service(token_data)
        
        # Move file to archive folder
        await service.move_file(
            file_id=file_id,
            new_parent_id=archive_folder_id
        )
        
        logger.info(f"Archived deliverable '{deliverable_name}' to project archive folder")
        
    except Exception as e:
        logger.error(f"Failed to archive deliverable {deliverable_name}: {e}")


# ============================================================================
# TASKS ENDPOINTS (Production Kanban)
# ============================================================================

@router.get("/{project_id}/tasks", response_model=List[TaskDetailResponse])
async def get_project_tasks(
    project_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tasks for a project (for Kanban)"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = db.query(AgencyTask).filter(AgencyTask.project_id == project_id)
    
    if status:
        query = query.filter(AgencyTask.status == TaskStatus(status))
    
    tasks = query.order_by(AgencyTask.priority.desc(), AgencyTask.due_date, AgencyTask.created_at).all()
    
    result = []
    for t in tasks:
        assignee = db.query(User).filter(User.id == t.assignee_id).first() if t.assignee_id else None
        result.append(TaskDetailResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status.value,
            priority=t.priority.value,
            due_date=t.due_date,
            assignee_id=t.assignee_id,
            assignee_name=assignee.full_name or assignee.email if assignee else None,
            created_at=t.created_at
        ))
    
    return result


@router.post("/{project_id}/tasks", response_model=TaskDetailResponse)
async def create_project_task(
    project_id: int,
    data: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task for the project"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task = AgencyTask(
        project_id=project_id,
        title=data.title,
        description=data.description,
        status=TaskStatus(data.status),
        priority=TaskPriority(data.priority),
        due_date=data.due_date,
        assignee_id=data.assignee_id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Log activity
    log_project_activity(
        db, project_id,
        f"Tâche créée: {data.title}",
        ActivityType.CREATION,
        current_user.id
    )
    
    assignee = db.query(User).filter(User.id == task.assignee_id).first() if task.assignee_id else None
    
    return TaskDetailResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority.value,
        due_date=task.due_date,
        assignee_id=task.assignee_id,
        assignee_name=assignee.full_name or assignee.email if assignee else None,
        created_at=task.created_at
    )


@router.patch("/tasks/{task_id}", response_model=TaskDetailResponse)
async def update_task(
    task_id: int,
    data: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task"""
    task = db.query(AgencyTask).filter(AgencyTask.id == task_id, AgencyTask.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    old_status = task.status.value
    
    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.status is not None:
        task.status = TaskStatus(data.status)
    if data.priority is not None:
        task.priority = TaskPriority(data.priority)
    if data.due_date is not None:
        task.due_date = data.due_date
    if data.assignee_id is not None:
        task.assignee_id = data.assignee_id
    
    db.commit()
    db.refresh(task)
    
    # Log if task completed
    if data.status == "done" and old_status != "done":
        log_project_activity(
            db, task.project_id,
            f"Tâche terminée: {task.title}",
            ActivityType.TASK_COMPLETED,
            current_user.id
        )
    
    assignee = db.query(User).filter(User.id == task.assignee_id).first() if task.assignee_id else None
    
    return TaskDetailResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority.value,
        due_date=task.due_date,
        assignee_id=task.assignee_id,
        assignee_name=assignee.full_name or assignee.email if assignee else None,
        created_at=task.created_at
    )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task"""
    task = db.query(AgencyTask).filter(AgencyTask.id == task_id, AgencyTask.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    project_id = task.project_id
    title = task.title
    
    db.delete(task)
    db.commit()
    
    return {"status": "deleted"}


# ============================================================================
# ASSETS ENDPOINTS
# ============================================================================

@router.get("/{project_id}/assets", response_model=List[AssetDetailResponse])
async def get_project_assets(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all assets for a project"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    assets = db.query(Asset).filter(
        Asset.project_id == project_id
    ).order_by(Asset.asset_type, Asset.created_at).all()
    
    return [
        AssetDetailResponse(
            id=a.id,
            kind=a.kind.value,
            name=a.name,
            url=a.url,
            version=a.version,
            asset_type=a.asset_type,
            created_at=a.created_at
        )
        for a in assets
    ]


@router.post("/{project_id}/assets", response_model=AssetDetailResponse)
async def create_project_asset(
    project_id: int,
    data: AssetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new asset for the project"""
    from app.db.models.agency import AssetKind
    
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    asset = Asset(
        project_id=project_id,
        workspace_id=project.workspace_id,  # Inherit from project
        kind=AssetKind(data.kind),
        name=data.name,
        url=data.url,
        version=data.version,
        asset_type=data.asset_type,
        created_by=current_user.id
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return AssetDetailResponse(
        id=asset.id,
        kind=asset.kind.value,
        name=asset.name,
        url=asset.url,
        version=asset.version,
        asset_type=asset.asset_type,
        created_at=asset.created_at
    )


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an asset"""
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.project.has(Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id"))))).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    db.delete(asset)
    db.commit()
    
    return {"status": "deleted"}


# ============================================================================
# ACTIVITY LOG ENDPOINTS
# ============================================================================

@router.get("/{project_id}/activity", response_model=List[ActivityLogResponse])
async def get_project_activity(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project activity timeline"""
    project = db.query(Project).filter(Project.id == project_id, Project.client.has(Client.workspace_id == resolve_workspace_id(db, current_user, db.info.get("workspace_id")))).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    activities = db.query(ProjectActivityLog).filter(
        ProjectActivityLog.project_id == project_id
    ).order_by(desc(ProjectActivityLog.created_at)).limit(limit).all()
    
    result = []
    for a in activities:
        creator = db.query(User).filter(User.id == a.created_by).first() if a.created_by else None
        result.append(ActivityLogResponse(
            id=a.id,
            message=a.message,
            activity_type=a.activity_type.value if a.activity_type else None,
            created_at=a.created_at,
            created_by=a.created_by,
            created_by_name=creator.full_name or creator.email if creator else None
        ))
    
    return result
