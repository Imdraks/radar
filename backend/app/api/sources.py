"""
Source configuration endpoints
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.user import User
from app.db.models.source import SourceConfig
from app.db.models.opportunity import SourceType
from app.schemas.source import (
    SourceConfigCreate, SourceConfigUpdate, SourceConfigResponse,
    SourceTestResult
)
from app.api.deps import get_current_user, require_admin
from app.ingestion.factory import get_connector

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=List[SourceConfigResponse])
def list_sources(
    is_active: bool = None,
    source_type: SourceType = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all source configurations"""
    query = db.query(SourceConfig)
    
    if is_active is not None:
        query = query.filter(SourceConfig.is_active == is_active)
    if source_type:
        query = query.filter(SourceConfig.source_type == source_type)
    
    return query.order_by(SourceConfig.name).all()


@router.get("/{source_id}", response_model=SourceConfigResponse)
def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get source configuration by ID"""
    source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return source


@router.post("", response_model=SourceConfigResponse)
def create_source(
    source_data: SourceConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new source configuration"""
    # Check for duplicate name
    existing = db.query(SourceConfig).filter(
        SourceConfig.name == source_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source with this name already exists",
        )
    
    source = SourceConfig(**source_data.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceConfigResponse)
def update_source(
    source_id: int,
    update_data: SourceConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update source configuration"""
    source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(source, field, value)
    
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete source configuration"""
    source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    db.delete(source)
    db.commit()
    return {"message": "Source deleted successfully"}


@router.post("/{source_id}/test", response_model=SourceTestResult)
async def test_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Test a source configuration"""
    source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    try:
        connector = get_connector(source)
        items = await connector.fetch(limit=5)
        
        return SourceTestResult(
            success=True,
            message=f"Successfully fetched {len(items)} items",
            items_found=len(items),
            sample_items=[
                {"title": item.get("title", ""), "url": item.get("url", "")}
                for item in items[:3]
            ],
        )
    except Exception as e:
        return SourceTestResult(
            success=False,
            message=f"Test failed: {str(e)}",
            errors=[str(e)],
        )
