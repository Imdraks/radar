"""
API endpoints for artist predictions (Radar Discovery)
Statistical projections based on historical snapshots.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user, get_current_workspace
from app.db.models.user import User
from app.db.models.workspace import Workspace
from app.intelligence.prediction_service import (
    ArtistPredictionService,
    ArtistPrediction,
    PredictionScenario,
    PredictionExplanation
)

router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ScenarioResponse(BaseModel):
    value_30d: int
    value_90d: int
    growth_rate: float


class ExplanationResponse(BaseModel):
    text: str
    impact: str  # "positive", "negative", "neutral"
    weight: float


class HistoricalDataPoint(BaseModel):
    date: str
    listeners: int


class ArtistPredictionResponse(BaseModel):
    """Réponse complète de prédiction artiste"""
    artist_name: str
    current_listeners: int
    
    # Scénarios
    pessimistic: ScenarioResponse
    central: ScenarioResponse
    optimistic: ScenarioResponse
    
    # Probabilités et confiance
    growth_probability: Optional[float]
    confidence_score: Optional[int]
    confidence_label: str
    
    # Données historiques
    historical_data: List[HistoricalDataPoint]
    
    # Explications
    explanations: List[ExplanationResponse]
    
    # Métadonnées
    snapshot_count: int
    data_span_days: int
    last_update: Optional[datetime]
    is_valid: bool
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class ArtistPredictionSummary(BaseModel):
    """Résumé rapide des prédictions"""
    artist_name: str
    current_listeners: int
    predicted_30d_min: int
    predicted_30d_max: int
    predicted_90d_min: int
    predicted_90d_max: int
    growth_probability: Optional[float]
    confidence_label: str
    is_valid: bool


class SnapshotCountResponse(BaseModel):
    artist_name: str
    snapshot_count: int
    predictions_available: bool
    min_required: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/{artist_name}", response_model=ArtistPredictionResponse)
async def get_artist_prediction(
    artist_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """
    Obtenir les prédictions pour un artiste.
    
    Retourne les projections à 30 et 90 jours basées sur l'historique
    des snapshots. Nécessite au minimum 2 snapshots.
    
    **Scénarios retournés:**
    - pessimistic: mu - sigma
    - central: mu (moyenne pondérée)
    - optimistic: mu + sigma
    
    **Confiance:**
    - 0-39: Faible
    - 40-69: Moyenne  
    - 70-100: Élevée
    """
    service = ArtistPredictionService(db)
    prediction = service.get_prediction(artist_name, current_workspace.id)
    
    return _convert_prediction_to_response(prediction)


@router.get("/{artist_name}/summary", response_model=ArtistPredictionSummary)
async def get_artist_prediction_summary(
    artist_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """
    Obtenir un résumé rapide des prédictions.
    
    Idéal pour afficher dans une liste ou un tableau.
    """
    service = ArtistPredictionService(db)
    prediction = service.get_prediction(artist_name, current_workspace.id)
    
    return ArtistPredictionSummary(
        artist_name=prediction.artist_name,
        current_listeners=prediction.current_listeners,
        predicted_30d_min=prediction.pessimistic.value_30d,
        predicted_30d_max=prediction.optimistic.value_30d,
        predicted_90d_min=prediction.pessimistic.value_90d,
        predicted_90d_max=prediction.optimistic.value_90d,
        growth_probability=None,
        confidence_label="Non calibrée",
        is_valid=prediction.is_valid
    )


@router.get("/{artist_name}/snapshot-count", response_model=SnapshotCountResponse)
async def get_snapshot_count(
    artist_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """
    Retourne le nombre de snapshots disponibles pour un artiste.
    
    Utile pour savoir si les prédictions sont disponibles.
    Minimum 2 snapshots requis pour les prédictions.
    """
    service = ArtistPredictionService(db)
    count = service.get_snapshot_count(artist_name, current_workspace.id)
    
    return SnapshotCountResponse(
        artist_name=artist_name,
        snapshot_count=count,
        predictions_available=count >= 2,
        min_required=2
    )


@router.post("/{artist_name}/refresh")
async def refresh_artist_prediction(
    artist_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """
    Demande le rafraîchissement des données d'un artiste.
    
    Cela déclenche une nouvelle analyse qui créera un nouveau snapshot.
    Retourne un task_id pour suivre l'avancement.
    """
    from app.workers.tasks import analyze_artist_intelligence_task
    
    # Lancer la tâche Celery
    task = analyze_artist_intelligence_task.delay(
        artist_name=artist_name,
        workspace_id=current_workspace.id,
        user_id=current_user.id
    )
    
    return {
        "message": "Analyse en cours",
        "task_id": task.id,
        "artist_name": artist_name
    }


@router.get("/{artist_name}/evaluation")
def evaluate_artist_predictions(artist_name: str, db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    return ArtistPredictionService(db).evaluate_history(artist_name, workspace.id)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _convert_prediction_to_response(prediction: ArtistPrediction) -> ArtistPredictionResponse:
    """Convertit un ArtistPrediction en ArtistPredictionResponse"""
    return ArtistPredictionResponse(
        artist_name=prediction.artist_name,
        current_listeners=prediction.current_listeners,
        pessimistic=ScenarioResponse(
            value_30d=prediction.pessimistic.value_30d,
            value_90d=prediction.pessimistic.value_90d,
            growth_rate=prediction.pessimistic.growth_rate
        ),
        central=ScenarioResponse(
            value_30d=prediction.central.value_30d,
            value_90d=prediction.central.value_90d,
            growth_rate=prediction.central.growth_rate
        ),
        optimistic=ScenarioResponse(
            value_30d=prediction.optimistic.value_30d,
            value_90d=prediction.optimistic.value_90d,
            growth_rate=prediction.optimistic.growth_rate
        ),
        growth_probability=None,
        confidence_score=None,
        confidence_label="Non calibrée",
        historical_data=[
            HistoricalDataPoint(date=d["date"], listeners=d["listeners"])
            for d in prediction.historical_data
        ],
        explanations=[
            ExplanationResponse(
                text=e.text,
                impact=e.impact,
                weight=e.weight
            )
            for e in prediction.explanations
        ],
        snapshot_count=prediction.snapshot_count,
        data_span_days=prediction.data_span_days,
        last_update=prediction.last_update,
        is_valid=prediction.is_valid,
        error_message=prediction.error_message
    )
