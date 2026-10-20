"""
Opportunities endpoints
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import (
    Opportunity, OpportunityNote, OpportunityTask, OpportunityTag,
    OpportunityStatus, OpportunityCategory, SourceType
)
from app.schemas.opportunity import (
    OpportunityResponse, OpportunityListResponse, OpportunityUpdate,
    NoteCreate, NoteResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    BudgetStatsResponse
)
from app.api.deps import get_current_user, require_bizdev, require_admin, require_workspace_member, get_user_workspace_id

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunityListResponse)
def list_opportunities(
    # Pagination
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    # Filters
    status: Optional[OpportunityStatus] = None,
    statuses: Optional[str] = None,  # Comma-separated
    category: Optional[OpportunityCategory] = None,
    categories: Optional[str] = None,  # Comma-separated
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    region: Optional[str] = None,
    source_name: Optional[str] = None,
    source_type: Optional[SourceType] = None,
    q: Optional[str] = None,
    deadline_before: Optional[datetime] = None,
    deadline_after: Optional[datetime] = None,
    min_budget: Optional[Decimal] = None,
    max_budget: Optional[Decimal] = None,
    has_budget: Optional[bool] = None,
    assigned_to_user_id: Optional[int] = None,
    created_after: Optional[datetime] = None,
    # Sorting
    sort_by: str = Query("score", pattern="^(score|deadline_at|created_at|budget_amount)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    # Auth
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member),
):
    """List opportunities with filters and pagination"""
    # Get user's workspace
    ws_id = current_user.workspace_id
    
    query = db.query(Opportunity).filter(Opportunity.workspace_id == ws_id)
    
    # Apply filters
    if status:
        query = query.filter(Opportunity.status == status)
    if statuses:
        status_list = [OpportunityStatus(s.strip()) for s in statuses.split(",")]
        query = query.filter(Opportunity.status.in_(status_list))
    
    if category:
        query = query.filter(Opportunity.category == category)
    if categories:
        cat_list = [OpportunityCategory(c.strip()) for c in categories.split(",")]
        query = query.filter(Opportunity.category.in_(cat_list))
    
    if min_score is not None:
        query = query.filter(Opportunity.score >= min_score)
    if max_score is not None:
        query = query.filter(Opportunity.score <= max_score)
    
    if region:
        query = query.filter(Opportunity.location_region.ilike(f"%{region}%"))
    
    if source_name:
        query = query.filter(Opportunity.source_name == source_name)
    if source_type:
        query = query.filter(Opportunity.source_type == source_type)
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Opportunity.title.ilike(search_term),
                Opportunity.description.ilike(search_term),
                Opportunity.organization.ilike(search_term),
            )
        )
    
    if deadline_before:
        query = query.filter(Opportunity.deadline_at <= deadline_before)
    if deadline_after:
        query = query.filter(Opportunity.deadline_at >= deadline_after)
    
    if min_budget is not None:
        query = query.filter(Opportunity.budget_amount >= min_budget)
    if max_budget is not None:
        query = query.filter(Opportunity.budget_amount <= max_budget)
    
    if has_budget is not None:
        if has_budget:
            query = query.filter(Opportunity.budget_amount.isnot(None))
        else:
            query = query.filter(Opportunity.budget_amount.is_(None))
    
    if assigned_to_user_id:
        query = query.filter(Opportunity.assigned_to_user_id == assigned_to_user_id)
    
    if created_after:
        query = query.filter(Opportunity.created_at >= created_after)
    
    # Count total
    total = query.count()
    
    # Apply sorting
    sort_column = getattr(Opportunity, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Apply pagination
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()
    
    return OpportunityListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get("/budget-stats", response_model=BudgetStatsResponse)
def get_budget_stats(
    bins: int = Query(15, ge=5, le=30),
    # Same filters as list
    status: Optional[OpportunityStatus] = None,
    statuses: Optional[str] = None,
    category: Optional[OpportunityCategory] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member),
):
    """Get budget statistics for histogram filter"""
    ws_id = current_user.workspace_id
    query = db.query(Opportunity).filter(
        Opportunity.workspace_id == ws_id,
        Opportunity.budget_amount.isnot(None)
    )
    
    # Apply same filters
    if status:
        query = query.filter(Opportunity.status == status)
    if statuses:
        status_list = [OpportunityStatus(s.strip()) for s in statuses.split(",")]
        query = query.filter(Opportunity.status.in_(status_list))
    if category:
        query = query.filter(Opportunity.category == category)
    if region:
        query = query.filter(Opportunity.location_region.ilike(f"%{region}%"))
    
    # Get stats
    stats = db.query(
        func.min(Opportunity.budget_amount).label("min_budget"),
        func.max(Opportunity.budget_amount).label("max_budget"),
        func.avg(Opportunity.budget_amount).label("avg_budget"),
        func.count(Opportunity.id).label("count"),
    ).filter(Opportunity.budget_amount.isnot(None))
    
    # Apply same filters
    if status:
        stats = stats.filter(Opportunity.status == status)
    if statuses:
        stats = stats.filter(Opportunity.status.in_(status_list))
    if category:
        stats = stats.filter(Opportunity.category == category)
    if region:
        stats = stats.filter(Opportunity.location_region.ilike(f"%{region}%"))
    
    result = stats.first()
    
    total_query = db.query(func.count(Opportunity.id))
    if status:
        total_query = total_query.filter(Opportunity.status == status)
    total_count = total_query.scalar()
    
    if not result or result.count == 0:
        return BudgetStatsResponse(
            min_budget=None,
            max_budget=None,
            avg_budget=None,
            count_with_budget=0,
            total_count=total_count,
            histogram=[],
        )
    
    min_val = float(result.min_budget)
    max_val = float(result.max_budget)
    
    # Build histogram
    histogram = []
    if max_val > min_val:
        bin_width = (max_val - min_val) / bins
        for i in range(bins):
            bin_min = min_val + (i * bin_width)
            bin_max = min_val + ((i + 1) * bin_width)
            
            count_query = query.filter(
                and_(
                    Opportunity.budget_amount >= bin_min,
                    Opportunity.budget_amount < bin_max if i < bins - 1 else Opportunity.budget_amount <= bin_max
                )
            )
            count = count_query.count()
            
            histogram.append({
                "min": round(bin_min, 2),
                "max": round(bin_max, 2),
                "count": count,
            })
    else:
        # All same value
        histogram.append({
            "min": min_val,
            "max": max_val,
            "count": result.count,
        })
    
    return BudgetStatsResponse(
        min_budget=result.min_budget,
        max_budget=result.max_budget,
        avg_budget=round(result.avg_budget, 2) if result.avg_budget else None,
        count_with_budget=result.count,
        total_count=total_count,
        histogram=histogram,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member),
):
    """Get opportunity by ID"""
    ws_id = current_user.workspace_id
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return opportunity


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(
    opportunity_id: int,
    update_data: OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_workspace_member),
):
    """Update opportunity"""
    ws_id = current_user.workspace_id
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(opportunity, field, value)
    
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/merge")
def merge_opportunities(
    opportunity_id: int,
    merge_into_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Merge duplicate opportunity into another"""
    ws_id = current_user.workspace_id
    source = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    target = db.query(Opportunity).filter(
        Opportunity.id == merge_into_id,
        Opportunity.workspace_id == ws_id
    ).first()
    
    if not source or not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both opportunities not found",
        )
    
    if source.id == target.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge opportunity into itself",
        )
    
    # Move notes and tasks
    db.query(OpportunityNote).filter(
        OpportunityNote.opportunity_id == source.id
    ).update({"opportunity_id": target.id})
    
    db.query(OpportunityTask).filter(
        OpportunityTask.opportunity_id == source.id
    ).update({"opportunity_id": target.id})
    
    # Merge URLs
    all_urls = set(target.urls_all or [])
    all_urls.update(source.urls_all or [])
    if source.url_primary:
        all_urls.add(source.url_primary)
    target.urls_all = list(all_urls)
    
    # Mark source as duplicate
    source.status = OpportunityStatus.ARCHIVED
    source.duplicate_of_id = target.id
    
    db.commit()
    
    return {"message": "Opportunities merged successfully", "target_id": str(target.id)}


# Notes endpoints
@router.get("/{opportunity_id}/notes", response_model=List[NoteResponse])
def list_notes(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notes for an opportunity"""
    ws_id = current_user.workspace_id
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    notes = db.query(OpportunityNote).filter(
        OpportunityNote.opportunity_id == opportunity_id
    ).order_by(desc(OpportunityNote.created_at)).all()
    return notes


@router.post("/{opportunity_id}/notes", response_model=NoteResponse)
def create_note(
    opportunity_id: int,
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_bizdev),
):
    """Create a note on an opportunity"""
    ws_id = current_user.workspace_id
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    
    note = OpportunityNote(
        opportunity_id=opportunity_id,
        author_id=current_user.id,
        content=note_data.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# Tasks endpoints
@router.get("/{opportunity_id}/tasks", response_model=List[TaskResponse])
def list_tasks(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tasks for an opportunity"""
    ws_id = current_user.workspace_id
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    tasks = db.query(OpportunityTask).filter(
        OpportunityTask.opportunity_id == opportunity_id
    ).order_by(OpportunityTask.due_date).all()
    return tasks


@router.post("/{opportunity_id}/tasks", response_model=TaskResponse)
def create_task(
    opportunity_id: int,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_bizdev),
):
    """Create a task on an opportunity"""
    ws_id = current_user.workspace_id
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    
    task = OpportunityTask(
        opportunity_id=opportunity_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        assigned_to_id=task_data.assigned_to_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{opportunity_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    opportunity_id: int,
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_bizdev),
):
    """Update a task"""
    ws_id = current_user.workspace_id
    opp = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.workspace_id == ws_id
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    task = db.query(OpportunityTask).filter(
        OpportunityTask.id == task_id,
        OpportunityTask.opportunity_id == opportunity_id,
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    update_dict = task_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(task, field, value)
    
    # Set completed_at if status changed to DONE
    if task_data.status == "DONE" and task.completed_at is None:
        task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    return task
