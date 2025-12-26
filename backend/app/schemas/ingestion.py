"""
Ingestion run schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from app.db.models.ingestion import IngestionStatus


class IngestionSearchParams(BaseModel):
    """Search parameters for targeted ingestion"""
    keywords: Optional[str] = None  # Comma-separated keywords
    region: Optional[str] = None
    city: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class IngestionRunResponse(BaseModel):
    """Ingestion run response schema"""
    id: UUID
    source_config_id: Optional[UUID] = None
    source_name: str
    status: IngestionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    items_fetched: int
    items_new: int
    items_duplicate: int
    items_updated: int
    items_error: int
    errors: List[str]
    run_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class IngestionTriggerRequest(BaseModel):
    """Request to trigger ingestion"""
    source_ids: Optional[List[UUID]] = None  # If None, run all active sources
    source_types: Optional[List[str]] = None  # Filter by type
    search_params: Optional[IngestionSearchParams] = None  # Search criteria
