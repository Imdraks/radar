"""
Agency Cockpit V2 API - Projects, Deliverables, Production
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models.agency import (
    Client, Deal, Project, Deliverable, Approval, 
    ProjectStatus, DeliverableStatus, ApprovalStatus, DealStatus
)
from app.db.models.user import User
from app.api.deps import get_current_user, require_workspace_member, resolve_workspace_id
from app.db.models.workspace import WorkspaceMember
from app.schemas.agency import (
    # Project
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectStatus as ProjectStatusEnum,
    # Deliverable
    DeliverableCreate, DeliverableUpdate, DeliverableResponse,
    DeliverableStatus as DeliverableStatusEnum,
    # Approval
    ApprovalCreate, ApprovalUpdate, ApprovalResponse,
    ApprovalStatus as ApprovalStatusEnum,
    # Production
    ProductionResponse, ProductionColumn, ProductionItem
)
from app.services.google_workspace import (
    get_google_workspace_service, 
    GoogleAPIError, 
    TokenExpiredError
)
from app.core.cache import cache_get

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agency", tags=["agency-projects"])


def get_ws_id(current_user: User, db: Session, workspace_id: Optional[int] = None) -> int:
    return resolve_workspace_id(db, current_user, workspace_id)


# ============================================================================
# PROJECTS
# ============================================================================

@router.get("/projects", response_model=List[ProjectListResponse])
async def list_projects(
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Liste des projets du workspace"""
    ws_id = get_ws_id(current_user, db)
    
    query = db.query(Project).join(Client).filter(Client.workspace_id == ws_id)
    
    if status:
        # Convert string to enum (case-insensitive)
        try:
            status_enum = ProjectStatus(status.lower())
            query = query.filter(Project.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if client_id:
        query = query.filter(Project.client_id == client_id)
    
    projects = query.offset(skip).limit(limit).all()
    now = datetime.utcnow()
    
    result = []
    for project in projects:
        # Count deliverables
        total_deliverables = db.query(func.count(Deliverable.id)).filter(
            Deliverable.project_id == project.id
        ).scalar() or 0
        
        approved_deliverables = db.query(func.count(Deliverable.id)).filter(
            Deliverable.project_id == project.id,
            Deliverable.status.in_([DeliverableStatus.APPROVED, DeliverableStatus.DELIVERED])
        ).scalar() or 0
        
        progress = int((approved_deliverables / total_deliverables * 100)) if total_deliverables > 0 else 0
        
        days_until = None
        is_urgent = False
        if project.deadline:
            days_until = (project.deadline - now).days
            is_urgent = days_until <= 3 and days_until >= 0
        
        result.append(ProjectListResponse(
            id=project.id,
            name=project.name,
            status=ProjectStatusEnum(project.status.value),
            client_id=project.client_id,
            client_name=project.client.name if project.client else None,
            deadline=project.deadline,
            days_until_deadline=days_until,
            is_urgent=is_urgent,
            progress_percent=progress,
            deliverables_count=total_deliverables,
            deliverables_approved=approved_deliverables
        ))
    
    return result


# ============================================================================
# BACKGROUND TASK: CREATE DRIVE STRUCTURE
# ============================================================================

async def create_project_drive_structure_task(
    project_id: int,
    project_name: str,
    user_id: int,
    db_url: str,
):
    """
    Background task to create Google Drive folder structure for a project.
    Called automatically after project creation.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    try:
        # Check if user has Google Workspace connected
        tokens = cache_get(f"google_workspace_tokens:{user_id}")
        if not tokens:
            logger.info(f"User {user_id} has no Google Workspace connected, skipping Drive creation")
            return
        
        # Get Google Workspace service
        service = get_google_workspace_service(user_id)
        
        # TODO: Get template IDs from workspace settings
        # brief_template_id = workspace.brief_template_id
        # report_template_id = workspace.report_template_id
        brief_template_id = None
        report_template_id = None
        
        # Create the Drive structure
        result = await service.create_project_drive_structure(
            project_name=project_name,
            brief_template_id=brief_template_id,
            report_template_id=report_template_id,
        )
        
        if result["success"] or result["drive_folder_id"]:
            # Update project with Drive folder ID
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()
            
            try:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.drive_folder_id = result["drive_folder_id"]
                    if result.get("brief_doc_id"):
                        project.brief_doc_id = result["brief_doc_id"]
                    if result.get("report_sheet_id"):
                        project.report_sheet_id = result["report_sheet_id"]
                    
                    # Save subfolder IDs
                    subfolders = result.get("subfolders", {})
                    if subfolders.get("00_Assets"):
                        project.drive_folder_assets = subfolders["00_Assets"]
                    if subfolders.get("01_Brief"):
                        project.drive_folder_brief = subfolders["01_Brief"]
                    if subfolders.get("02_Production"):
                        project.drive_folder_production = subfolders["02_Production"]
                    if subfolders.get("03_PostProd"):
                        project.drive_folder_postprod = subfolders["03_PostProd"]
                    if subfolders.get("04_Exports"):
                        project.drive_folder_exports = subfolders["04_Exports"]
                    if subfolders.get("05_Admin"):
                        project.drive_folder_admin = subfolders["05_Admin"]
                    if subfolders.get("07_Livrables"):
                        project.drive_folder_livrables = subfolders["07_Livrables"]
                    if subfolders.get("99_Archive"):
                        project.drive_folder_archive = subfolders["99_Archive"]
                    
                    db.commit()
                    logger.info(f"Updated project {project_id} with Drive folder: {result['drive_folder_id']}")
            finally:
                db.close()
        
        if result["errors"]:
            logger.warning(f"Drive structure created with errors: {result['errors']}")
            
    except TokenExpiredError:
        logger.warning(f"Google token expired for user {user_id}, Drive structure not created")
    except Exception as e:
        logger.error(f"Failed to create Drive structure for project {project_id}: {e}")


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Créer un nouveau projet avec création automatique du dossier Drive"""
    ws_id = get_ws_id(current_user, db)
    
    client = None
    # Vérifier client si fourni (avec filtrage workspace)
    if project_in.client_id:
        client = db.query(Client).filter(
            Client.id == project_in.client_id,
            Client.workspace_id == ws_id
        ).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    
    # Vérifier deal si fourni (via Client pour filtrage workspace)
    if project_in.deal_id:
        deal = db.query(Deal).join(Client).filter(
            Deal.id == project_in.deal_id,
            Client.workspace_id == ws_id
        ).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
    
    if client is None:
        from app.services.production_context import internal_client
        client = internal_client(db, ws_id)
    project = Project(
        workspace_id=ws_id,
        client_id=client.id,
        deal_id=project_in.deal_id,
        name=project_in.name,
        status=project_in.status.value if project_in.status else ProjectStatus.ACTIVE,
        deadline=project_in.deadline,
        budget=project_in.budget,
        description=project_in.description,
        owner_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Trigger background task to create Drive folder structure
    from app.core.config import settings
    background_tasks.add_task(
        create_project_drive_structure_task,
        project_id=project.id,
        project_name=project.name,
        user_id=current_user.id,
        db_url=settings.database_url,
    )
    logger.info(f"Project {project.id} created, Drive structure creation scheduled")
    
    return ProjectResponse(
        id=project.id,
        client_id=project.client_id,
        deal_id=project.deal_id,
        name=project.name,
        status=ProjectStatusEnum(project.status.value),
        deadline=project.deadline,
        budget=project.budget,
        description=project.description,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        client_name=client.name if client else None
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Détails d'un projet"""
    ws_id = get_ws_id(current_user, db)
    
    project = db.query(Project).join(Client).filter(
        Project.id == project_id,
        Client.workspace_id == ws_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    now = datetime.utcnow()
    
    total_deliverables = db.query(func.count(Deliverable.id)).filter(
        Deliverable.project_id == project.id
    ).scalar() or 0
    
    approved_deliverables = db.query(func.count(Deliverable.id)).filter(
        Deliverable.project_id == project.id,
        Deliverable.status.in_([DeliverableStatus.APPROVED, DeliverableStatus.DELIVERED])
    ).scalar() or 0
    
    progress = int((approved_deliverables / total_deliverables * 100)) if total_deliverables > 0 else 0
    
    days_until = None
    is_urgent = False
    if project.deadline:
        days_until = (project.deadline - now).days
        is_urgent = days_until <= 3 and days_until >= 0
    
    # Build Drive URLs from IDs
    drive_folder_url = f"https://drive.google.com/drive/folders/{project.drive_folder_id}" if project.drive_folder_id else None
    brief_doc_url = f"https://docs.google.com/document/d/{project.brief_doc_id}/edit" if project.brief_doc_id else None
    report_sheet_url = f"https://docs.google.com/spreadsheets/d/{project.report_sheet_id}/edit" if project.report_sheet_id else None
    
    return ProjectResponse(
        id=project.id,
        client_id=project.client_id,
        deal_id=project.deal_id,
        name=project.name,
        status=ProjectStatusEnum(project.status.value),
        deadline=project.deadline,
        budget=project.budget,
        description=project.description,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        # Drive integration
        drive_folder_id=project.drive_folder_id,
        drive_folder_url=drive_folder_url,
        brief_doc_id=project.brief_doc_id,
        brief_doc_url=brief_doc_url,
        report_sheet_id=project.report_sheet_id,
        report_sheet_url=report_sheet_url,
        # Computed
        client_name=project.client.name if project.client else None,
        owner_name=project.owner.email if project.owner else None,
        deliverables_count=total_deliverables,
        deliverables_approved=approved_deliverables,
        progress_percent=progress,
        days_until_deadline=days_until,
        is_urgent=is_urgent
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Mettre à jour un projet"""
    ws_id = get_ws_id(current_user, db)
    
    project = db.query(Project).join(Client).filter(
        Project.id == project_id,
        Client.workspace_id == ws_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project_in.client_id is not None:
        new_client = db.query(Client).filter(
            Client.id == project_in.client_id,
            Client.workspace_id == ws_id
        ).first()
        if not new_client:
            raise HTTPException(status_code=404, detail="Client not found")
        project.client_id = project_in.client_id
    if project_in.deal_id is not None:
        new_deal = db.query(Deal).join(Client).filter(
            Deal.id == project_in.deal_id,
            Client.workspace_id == ws_id
        ).first()
        if not new_deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        project.deal_id = project_in.deal_id
    if project_in.name is not None:
        project.name = project_in.name
    if project_in.status is not None:
        project.status = project_in.status.value
    if project_in.deadline is not None:
        project.deadline = project_in.deadline
    if project_in.budget is not None:
        project.budget = project_in.budget
    if project_in.description is not None:
        project.description = project_in.description
    
    db.commit()
    db.refresh(project)
    
    return await get_project(project_id, db, current_user)


@router.put("/projects/{project_id}/status")
async def update_project_status(
    project_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Quick status update"""
    ws_id = get_ws_id(current_user, db)
    
    project = db.query(Project).join(Client).filter(
        Project.id == project_id,
        Client.workspace_id == ws_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = status
    db.commit()
    
    return {"status": "updated", "new_status": status}


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Supprimer un projet et déplacer son dossier Drive vers Archives"""
    ws_id = get_ws_id(current_user, db)
    
    project = db.query(Project).join(Client).filter(
        Project.id == project_id,
        Client.workspace_id == ws_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Save drive_folder_id before deletion for archiving
    drive_folder_id = project.drive_folder_id
    project_name = project.name
    user_id = current_user.id
    
    # Delete from database
    db.delete(project)
    db.commit()
    
    # Move Drive folder to Archives in background
    if drive_folder_id:
        background_tasks.add_task(
            archive_project_folder,
            user_id=user_id,
            drive_folder_id=drive_folder_id,
            project_name=project_name
        )
    
    return {"status": "deleted"}


async def archive_project_folder(user_id: int, drive_folder_id: str, project_name: str):
    """Move project folder to Radar/Archives folder"""
    try:
        # Get user token from cache
        token_data = await cache_get(f"google_tokens:{user_id}")
        if not token_data:
            logger.warning(f"No Google token for user {user_id}, cannot archive folder")
            return
        
        service = await get_google_workspace_service(token_data)
        
        # Find or create Archives folder in Radar
        radar_folder = await service.find_folder_by_name("Radar", parent_id=None)
        if not radar_folder:
            logger.warning("Radar folder not found, cannot archive project")
            return
        
        archives_folder = await service.find_folder_by_name("Archives", radar_folder["id"])
        if not archives_folder:
            # Create Archives folder if it doesn't exist
            archives_result = await service.create_folder("Archives", radar_folder["id"])
            archives_folder_id = archives_result["id"]
        else:
            archives_folder_id = archives_folder["id"]
        
        # Find Projets folder to remove as parent
        projets_folder = await service.find_folder_by_name("Projets", radar_folder["id"])
        old_parent_id = projets_folder["id"] if projets_folder else None
        
        # Move project folder to Archives
        await service.move_file(
            file_id=drive_folder_id,
            new_parent_id=archives_folder_id,
            old_parent_id=old_parent_id
        )
        
        logger.info(f"Archived project folder '{project_name}' to Radar/Archives")
        
    except Exception as e:
        logger.error(f"Failed to archive project folder {project_name}: {e}")


# ============================================================================
# DELIVERABLES
# ============================================================================

@router.get("/deliverables", response_model=List[DeliverableResponse])
async def list_deliverables(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Liste des livrables du workspace"""
    ws_id = get_ws_id(current_user, db)
    
    query = db.query(Deliverable).join(Project).join(Client).filter(Client.workspace_id == ws_id)
    
    if project_id:
        query = query.filter(Deliverable.project_id == project_id)
    if status:
        # Convert string to enum (case-insensitive)
        try:
            status_enum = DeliverableStatus(status.lower())
            query = query.filter(Deliverable.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    deliverables = query.offset(skip).limit(limit).all()
    now = datetime.utcnow()
    
    result = []
    for d in deliverables:
        has_pending = db.query(func.count(Approval.id)).filter(
            Approval.deliverable_id == d.id,
            Approval.status == ApprovalStatus.PENDING
        ).scalar() > 0
        
        days_until = None
        if d.due_date:
            days_until = (d.due_date - now).days
        
        result.append(DeliverableResponse(
            id=d.id,
            project_id=d.project_id,
            name=d.name,
            type=d.type,
            status=DeliverableStatusEnum(d.status.value),
            due_date=d.due_date,
            link=d.link,
            notes=d.notes,
            created_at=d.created_at,
            updated_at=d.updated_at,
            project_name=d.project.name if d.project else None,
            client_name=d.project.client.name if d.project and d.project.client else None,
            has_pending_approval=has_pending,
            days_until_due=days_until
        ))
    
    return result


@router.post("/deliverables", response_model=DeliverableResponse)
async def create_deliverable(
    deliverable_in: DeliverableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Créer un nouveau livrable"""
    ws_id = get_ws_id(current_user, db)
    
    project = db.query(Project).join(Client).filter(
        Project.id == deliverable_in.project_id,
        Client.workspace_id == ws_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    deliverable = Deliverable(
        project_id=deliverable_in.project_id,
        name=deliverable_in.name,
        type=deliverable_in.type,
        status=deliverable_in.status.value if deliverable_in.status else DeliverableStatus.DRAFT,
        due_date=deliverable_in.due_date,
        link=deliverable_in.link,
        notes=deliverable_in.notes
    )
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    
    return DeliverableResponse(
        id=deliverable.id,
        project_id=deliverable.project_id,
        name=deliverable.name,
        type=deliverable.type,
        status=DeliverableStatusEnum(deliverable.status.value),
        due_date=deliverable.due_date,
        link=deliverable.link,
        notes=deliverable.notes,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at,
        project_name=project.name,
        client_name=project.client.name if project.client else None
    )


@router.get("/deliverables/{deliverable_id}", response_model=DeliverableResponse)
async def get_deliverable(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Détails d'un livrable"""
    ws_id = get_ws_id(current_user, db)
    
    d = db.query(Deliverable).join(Project).join(Client).filter(
        Deliverable.id == deliverable_id,
        Client.workspace_id == ws_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    now = datetime.utcnow()
    has_pending = db.query(func.count(Approval.id)).filter(
        Approval.deliverable_id == d.id,
        Approval.status == ApprovalStatus.PENDING
    ).scalar() > 0
    
    days_until = None
    if d.due_date:
        days_until = (d.due_date - now).days
    
    return DeliverableResponse(
        id=d.id,
        project_id=d.project_id,
        name=d.name,
        type=d.type,
        status=DeliverableStatusEnum(d.status.value),
        due_date=d.due_date,
        link=d.link,
        notes=d.notes,
        created_at=d.created_at,
        updated_at=d.updated_at,
        project_name=d.project.name if d.project else None,
        client_name=d.project.client.name if d.project and d.project.client else None,
        has_pending_approval=has_pending,
        days_until_due=days_until
    )


@router.put("/deliverables/{deliverable_id}", response_model=DeliverableResponse)
async def update_deliverable(
    deliverable_id: int,
    deliverable_in: DeliverableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Mettre à jour un livrable"""
    ws_id = get_ws_id(current_user, db)
    
    d = db.query(Deliverable).join(Project).join(Client).filter(
        Deliverable.id == deliverable_id,
        Client.workspace_id == ws_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    if deliverable_in.name is not None:
        d.name = deliverable_in.name
    if deliverable_in.type is not None:
        d.type = deliverable_in.type
    if deliverable_in.status is not None:
        d.status = deliverable_in.status.value
    if deliverable_in.due_date is not None:
        d.due_date = deliverable_in.due_date
    if deliverable_in.link is not None:
        d.link = deliverable_in.link
    if deliverable_in.notes is not None:
        d.notes = deliverable_in.notes
    
    db.commit()
    db.refresh(d)
    
    return await get_deliverable(deliverable_id, db, current_user)


@router.put("/deliverables/{deliverable_id}/status")
async def update_deliverable_status(
    deliverable_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Quick status update (for kanban)"""
    ws_id = get_ws_id(current_user, db)
    
    d = db.query(Deliverable).join(Project).join(Client).filter(
        Deliverable.id == deliverable_id,
        Client.workspace_id == ws_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    d.status = status
    db.commit()
    
    return {"status": "updated", "new_status": status}


@router.delete("/deliverables/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Supprimer un livrable et déplacer son fichier Drive vers 99_Archive du projet"""
    ws_id = get_ws_id(current_user, db)
    
    d = db.query(Deliverable).join(Project).join(Client).filter(
        Deliverable.id == deliverable_id,
        Client.workspace_id == ws_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    # Get info before deletion
    drive_file_id = d.drive_file_id
    deliverable_name = d.name
    project = db.query(Project).join(Client).filter(
        Project.id == d.project_id,
        Client.workspace_id == ws_id
    ).first()
    archive_folder_id = project.drive_folder_archive if project else None
    user_id = current_user.id
    
    db.delete(d)
    db.commit()
    
    # Move file to archive in background if it has a Drive file
    if drive_file_id and archive_folder_id:
        background_tasks.add_task(
            archive_item_to_project_folder,
            user_id=user_id,
            file_id=drive_file_id,
            archive_folder_id=archive_folder_id,
            item_name=deliverable_name,
            item_type="livrable"
        )
    
    return {"status": "deleted"}


async def archive_item_to_project_folder(
    user_id: int,
    file_id: str,
    archive_folder_id: str,
    item_name: str,
    item_type: str
):
    """Move a file to the project's archive folder"""
    try:
        token_data = await cache_get(f"google_tokens:{user_id}")
        if not token_data:
            logger.warning(f"No Google token for user {user_id}, cannot archive {item_type}")
            return
        
        service = await get_google_workspace_service(token_data)
        
        await service.move_file(
            file_id=file_id,
            new_parent_id=archive_folder_id
        )
        
        logger.info(f"Archived {item_type} '{item_name}' to project archive folder")
        
    except Exception as e:
        logger.error(f"Failed to archive {item_type} {item_name}: {e}")


# ============================================================================
# PRODUCTION KANBAN
# ============================================================================

@router.get("/production", response_model=ProductionResponse)
async def get_production(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Production Kanban - tous les livrables par statut"""
    ws_id = get_ws_id(current_user, db)
    
    columns = []
    total_items = 0
    now = datetime.utcnow()
    
    status_labels = {
        DeliverableStatus.DRAFT: "Brouillon",
        DeliverableStatus.TO_REVIEW: "À valider",
        DeliverableStatus.CHANGES_REQUESTED: "Corrections",
        DeliverableStatus.APPROVED: "Validé",
        DeliverableStatus.DELIVERED: "Livré"
    }
    
    for status in DeliverableStatus:
        query = db.query(Deliverable).join(Project).join(Client).filter(
            Deliverable.status == status,
            Client.workspace_id == ws_id
        )
        
        if project_id:
            query = query.filter(Deliverable.project_id == project_id)
        
        deliverables = query.all()
        
        items = []
        for d in deliverables:
            days_until = None
            is_urgent = False
            if d.due_date:
                days_until = (d.due_date - now).days
                is_urgent = days_until <= 3 and days_until >= 0
            
            has_pending = db.query(func.count(Approval.id)).filter(
                Approval.deliverable_id == d.id,
                Approval.status == ApprovalStatus.PENDING
            ).scalar() > 0
            
            items.append(ProductionItem(
                id=d.id,
                name=d.name,
                type=d.type,
                status=DeliverableStatusEnum(d.status.value),
                due_date=d.due_date,
                days_until_due=days_until,
                is_urgent=is_urgent,
                project_id=d.project_id,
                project_name=d.project.name if d.project else "",
                client_name=d.project.client.name if d.project and d.project.client else "",
                has_pending_approval=has_pending,
                link=d.link
            ))
        
        columns.append(ProductionColumn(
            status=DeliverableStatusEnum(status.value),
            label=status_labels.get(status, status.value),
            items=items,
            count=len(items)
        ))
        
        total_items += len(items)
    
    return ProductionResponse(
        columns=columns,
        total_items=total_items
    )


# ============================================================================
# APPROVALS
# ============================================================================

@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_approvals(
    status: Optional[str] = Query(None),
    deliverable_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Liste des demandes de validation"""
    ws_id = get_ws_id(current_user, db)
    
    query = db.query(Approval).join(Deliverable).join(Project).join(Client).filter(
        Client.workspace_id == ws_id
    )
    
    if status:
        # Convert string to enum (case-insensitive)
        try:
            status_enum = ApprovalStatus(status.lower())
            query = query.filter(Approval.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if deliverable_id:
        query = query.filter(Approval.deliverable_id == deliverable_id)
    
    approvals = query.offset(skip).limit(limit).all()
    
    result = []
    for a in approvals:
        result.append(ApprovalResponse(
            id=a.id,
            deliverable_id=a.deliverable_id,
            status=ApprovalStatusEnum(a.status.value),
            feedback=a.feedback,
            requested_at=a.requested_at,
            decided_at=a.decided_at,
            decided_by=a.decided_by,
            deliverable_name=a.deliverable.name if a.deliverable else None,
            project_name=a.deliverable.project.name if a.deliverable and a.deliverable.project else None,
            client_name=a.deliverable.project.client.name if a.deliverable and a.deliverable.project and a.deliverable.project.client else None
        ))
    
    return result


@router.post("/approvals", response_model=ApprovalResponse)
async def create_approval(
    approval_in: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Demander une validation"""
    ws_id = get_ws_id(current_user, db)
    
    deliverable = db.query(Deliverable).join(Project).join(Client).filter(
        Deliverable.id == approval_in.deliverable_id,
        Client.workspace_id == ws_id
    ).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    # Change deliverable status to "to_review"
    deliverable.status = DeliverableStatus.TO_REVIEW
    
    approval = Approval(
        deliverable_id=approval_in.deliverable_id,
        status=ApprovalStatus.PENDING,
        feedback=approval_in.feedback
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    
    return ApprovalResponse(
        id=approval.id,
        deliverable_id=approval.deliverable_id,
        status=ApprovalStatusEnum(approval.status.value),
        feedback=approval.feedback,
        requested_at=approval.requested_at,
        deliverable_name=deliverable.name,
        project_name=deliverable.project.name if deliverable.project else None,
        client_name=deliverable.project.client.name if deliverable.project and deliverable.project.client else None
    )


@router.put("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: int,
    status: str,  # "approved" or "changes"
    feedback: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member)
):
    """Décider d'une validation"""
    ws_id = get_ws_id(current_user, db)
    
    approval = db.query(Approval).join(Deliverable).join(Project).join(Client).filter(
        Approval.id == approval_id,
        Client.workspace_id == ws_id
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    approval.status = status
    approval.feedback = feedback
    approval.decided_at = datetime.utcnow()
    approval.decided_by = current_user.id
    
    # Update deliverable status - already filtered by approval's workspace
    deliverable = db.query(Deliverable).filter(
        Deliverable.id == approval.deliverable_id
    ).first()
    if deliverable:
        if status == "approved":
            deliverable.status = DeliverableStatus.APPROVED
        elif status == "changes":
            deliverable.status = DeliverableStatus.CHANGES_REQUESTED
    
    db.commit()
    
    return {"status": "decided", "decision": status}
