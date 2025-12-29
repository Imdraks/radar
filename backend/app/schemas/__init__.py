"""
API Schemas (Pydantic models)

Schema Organization:
- opportunity.py: Legacy V1 schemas (Integer IDs, Opportunity model)
- collections.py: V2 schemas (UUIDs, LeadItem model)
- collection.py: Entity/Brief/Contact system schemas
"""
# User schemas
from .user import (
    UserCreate, UserUpdate, UserResponse, UserLogin,
    Token, TokenPayload
)

# Legacy V1 Opportunity schemas (used by /api/v1/opportunities)
from .opportunity import (
    OpportunityCreate, OpportunityUpdate, OpportunityResponse,
    OpportunityListResponse, OpportunityFilters,
    NoteCreate, NoteResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    TagCreate, TagResponse,
    BudgetStatsResponse
)

# Source and Ingestion
from .source import (
    SourceConfigCreate, SourceConfigUpdate, SourceConfigResponse,
    SourceTestResult
)
from .ingestion import IngestionRunResponse, IngestionTriggerRequest
from .scoring import ScoringRuleCreate, ScoringRuleUpdate, ScoringRuleResponse
