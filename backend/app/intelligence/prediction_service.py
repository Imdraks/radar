"""
Artist Prediction Service
Provides statistical projections based on historical snapshots.

Uses exponential weighted moving average (EWMA) for trend calculation
and Monte Carlo-like scenario projections.
"""
import math
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db.models.artist_snapshot import ArtistSnapshot

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PredictionScenario:
    """Un scénario de prédiction (pessimiste, central, optimiste)"""
    value_30d: int
    value_90d: int
    growth_rate: float  # Taux de croissance utilisé


@dataclass
class PredictionExplanation:
    """Une raison expliquant la prédiction"""
    text: str
    impact: str  # "positive", "negative", "neutral"
    weight: float  # Importance 0-1


@dataclass
class ArtistPrediction:
    """Résultat complet d'une prédiction artiste"""
    artist_name: str
    current_listeners: int
    
    # Scénarios
    pessimistic: PredictionScenario
    central: PredictionScenario
    optimistic: PredictionScenario
    
    # Probabilités et confiance
    growth_probability: float  # 0-100%
    confidence_score: int  # 0-100
    confidence_label: str  # "Faible", "Moyenne", "Élevée"
    
    # Données historiques pour le graphique
    historical_data: List[Dict[str, Any]] = field(default_factory=list)
    
    # Explications
    explanations: List[PredictionExplanation] = field(default_factory=list)
    
    # Métadonnées
    snapshot_count: int = 0
    data_span_days: int = 0
    last_update: Optional[datetime] = None
    is_valid: bool = True
    error_message: Optional[str] = None


# ============================================================================
# PREDICTION SERVICE
# ============================================================================

class ArtistPredictionService:
    """
    Service de prédiction pour les artistes.
    
    Utilise les snapshots historiques pour calculer des projections
    statistiques de croissance à 30 et 90 jours.
    """
    
    # Poids des sources secondaires
    TIKTOK_WEIGHT = 0.15
    YOUTUBE_WEIGHT = 0.10
    CONCERTS_WEIGHT = 0.05
    
    # Paramètres EWMA
    EWMA_ALPHA = 0.3  # Plus élevé = plus de poids aux données récentes
    
    # Seuils de confiance
    MIN_SNAPSHOTS = 2
    OPTIMAL_SNAPSHOTS = 5
    MAX_DATA_AGE_DAYS = 90
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_prediction(
        self,
        artist_name: str,
        workspace_id: Optional[int] = None
    ) -> ArtistPrediction:
        """
        Calcule une prédiction complète pour un artiste.
        
        Args:
            artist_name: Nom de l'artiste
            workspace_id: ID du workspace (optionnel pour isolation)
            
        Returns:
            ArtistPrediction avec toutes les données
        """
        normalized_name = ArtistSnapshot.normalize_name(artist_name)
        
        # Récupérer les snapshots
        snapshots = self._get_snapshots(normalized_name, workspace_id)
        return self._predict_from_snapshots(artist_name, snapshots)

    def _predict_from_snapshots(self, artist_name, snapshots):
        """Shared inference path; evaluations pass only observations available at the origin."""
        
        # Vérifier si on a assez de données
        if len(snapshots) < self.MIN_SNAPSHOTS:
            return self._create_invalid_prediction(
                artist_name,
                f"Historique insuffisant ({len(snapshots)} snapshot(s), minimum requis: {self.MIN_SNAPSHOTS})"
            )
        
        # Extraire les données Spotify
        spotify_data = self._extract_spotify_series(snapshots)
        
        if not spotify_data or len(spotify_data) < 2:
            return self._create_invalid_prediction(
                artist_name,
                "Données Spotify insuffisantes pour les prédictions"
            )
        
        # Calculer les taux de croissance
        growth_rates = self._calculate_growth_rates(spotify_data)
        
        if not growth_rates:
            return self._create_invalid_prediction(
                artist_name,
                "Impossible de calculer les tendances de croissance"
            )
        
        # Calculer mu (tendance) et sigma (incertitude)
        mu, sigma = self._calculate_ewma_stats(growth_rates)
        
        # Ajuster avec les sources secondaires
        mu_adjusted = self._adjust_with_secondary_sources(mu, snapshots)
        
        # Calculer les scénarios
        current_listeners = spotify_data[-1]["value"]
        pessimistic = self._project_scenario(current_listeners, mu_adjusted - sigma)
        central = self._project_scenario(current_listeners, mu_adjusted)
        optimistic = self._project_scenario(current_listeners, mu_adjusted + sigma)
        
        # Calculer la probabilité de croissance
        growth_probability = self._calculate_growth_probability(mu_adjusted, sigma)
        
        # Calculer le score de confiance
        confidence_score = self._calculate_confidence_score(snapshots)
        confidence_label = self._get_confidence_label(confidence_score)
        
        # Préparer les données historiques pour le graphique
        historical_data = self._prepare_historical_data(spotify_data)
        
        # Générer les explications
        explanations = self._generate_explanations(snapshots, growth_rates, mu_adjusted)
        
        # Calculer la durée des données
        data_span = (snapshots[0].snapshot_date - snapshots[-1].snapshot_date).days if len(snapshots) > 1 else 0
        
        return ArtistPrediction(
            artist_name=artist_name,
            current_listeners=current_listeners,
            pessimistic=pessimistic,
            central=central,
            optimistic=optimistic,
            growth_probability=growth_probability,
            confidence_score=confidence_score,
            confidence_label=confidence_label,
            historical_data=historical_data,
            explanations=explanations,
            snapshot_count=len(snapshots),
            data_span_days=abs(data_span),
            last_update=snapshots[0].snapshot_date if snapshots else None,
            is_valid=True
        )
    
    def evaluate_history(self, artist_name: str, workspace_id: int) -> dict:
        """Rolling-origin evaluation of the actual model, compared with a last-value baseline.

        Uses only prior observations at every origin. Small samples are descriptive
        diagnostics and cannot establish a calibrated probability of success.
        """
        snapshots = self._get_snapshots(ArtistSnapshot.normalize_name(artist_name), workspace_id, limit=180)
        chronological = sorted(snapshots, key=lambda row: row.snapshot_date)
        observations = [row for row in chronological if row.spotify_monthly_listeners and row.spotify_monthly_listeners > 0]
        samples = []
        for i in range(1, len(observations) - 1):
            origin = observations[i]
            future = [row for row in observations[i+1:] if 30 <= (row.snapshot_date-origin.snapshot_date).days <= 90]
            if not future:
                continue
            target = future[0]
            training = sorted([row for row in snapshots if row.snapshot_date <= origin.snapshot_date], key=lambda row: row.snapshot_date, reverse=True)
            prediction = self._predict_from_snapshots(artist_name, training)
            if not prediction.is_valid:
                continue
            horizon = (target.snapshot_date-origin.snapshot_date).days
            expected = int(origin.spotify_monthly_listeners * math.exp(prediction.central.growth_rate * horizon))
            actual = target.spotify_monthly_listeners
            samples.append({"origin": origin.snapshot_date.isoformat(), "target": target.snapshot_date.isoformat(),
                            "horizon_days": horizon, "predicted": expected, "observed": actual,
                            "absolute_error": abs(expected-actual), "baseline_error": abs(origin.spotify_monthly_listeners-actual)})
        count = len(samples)
        return {"method": "rolling_origin_existing_model", "status": "descriptive" if count else "insufficient_history",
                "sample_count": count, "calibrated_probability": False,
                "mae_listeners": sum(row["absolute_error"] for row in samples)/count if count else None,
                "baseline_mae_listeners": sum(row["baseline_error"] for row in samples)/count if count else None,
                "samples": samples}

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    def _get_snapshots(
        self,
        normalized_name: str,
        workspace_id: Optional[int] = None,
        limit: int = 30
    ) -> List[ArtistSnapshot]:
        """Récupère les snapshots historiques triés par date décroissante"""
        query = self.db.query(ArtistSnapshot).filter(
            ArtistSnapshot.artist_name_normalized == normalized_name
        )
        
        if workspace_id:
            query = query.filter(ArtistSnapshot.workspace_id == workspace_id)
        
        return query.order_by(desc(ArtistSnapshot.snapshot_date)).limit(limit).all()
    
    def _extract_spotify_series(
        self,
        snapshots: List[ArtistSnapshot]
    ) -> List[Dict[str, Any]]:
        """Extrait la série temporelle Spotify des snapshots"""
        series = []
        for snap in reversed(snapshots):  # Ordre chronologique
            if snap.spotify_monthly_listeners and snap.spotify_monthly_listeners > 0:
                series.append({
                    "date": snap.snapshot_date,
                    "value": snap.spotify_monthly_listeners
                })
        return series
    
    def _calculate_growth_rates(
        self,
        spotify_data: List[Dict[str, Any]]
    ) -> List[float]:
        """
        Calcule les taux de croissance logarithmiques.
        growth_rate = ln(listeners_t / listeners_t-1)
        """
        rates = []
        for i in range(1, len(spotify_data)):
            prev_value = spotify_data[i-1]["value"]
            curr_value = spotify_data[i]["value"]
            
            if prev_value > 0 and curr_value > 0:
                # Croissance logarithmique
                rate = math.log(curr_value / prev_value)
                
                # Normaliser par le temps écoulé (en jours)
                days_diff = (spotify_data[i]["date"] - spotify_data[i-1]["date"]).days
                if days_diff > 0:
                    # Normaliser sur base journalière
                    daily_rate = rate / days_diff
                    rates.append(daily_rate)
        
        return rates
    
    def _calculate_ewma_stats(
        self,
        growth_rates: List[float]
    ) -> Tuple[float, float]:
        """
        Calcule la moyenne pondérée (EWMA) et l'écart-type.
        Les données récentes ont plus de poids.
        """
        if not growth_rates:
            return 0.0, 0.1
        
        # EWMA pour mu
        alpha = self.EWMA_ALPHA
        mu = growth_rates[0]
        
        for i in range(1, len(growth_rates)):
            mu = alpha * growth_rates[i] + (1 - alpha) * mu
        
        # Écart-type pondéré
        if len(growth_rates) < 2:
            sigma = abs(mu) * 0.5  # Haute incertitude avec peu de données
        else:
            variance = 0.0
            weight_sum = 0.0
            for i, rate in enumerate(growth_rates):
                weight = alpha ** (len(growth_rates) - 1 - i)
                variance += weight * (rate - mu) ** 2
                weight_sum += weight
            
            sigma = math.sqrt(variance / weight_sum) if weight_sum > 0 else abs(mu) * 0.5
        
        # Minimum sigma pour éviter division par zéro
        sigma = max(sigma, 0.001)
        
        return mu, sigma
    
    def _adjust_with_secondary_sources(
        self,
        mu: float,
        snapshots: List[ArtistSnapshot]
    ) -> float:
        """
        Ajuste mu avec les signaux secondaires.
        mu_adjusted = mu + 0.15*tiktok + 0.10*youtube + 0.05*concerts
        """
        if len(snapshots) < 2:
            return mu
        
        latest = snapshots[0]
        previous = snapshots[1]
        
        adjustments = 0.0
        
        # TikTok signal (-1 to +1)
        tiktok_signal = self._calculate_source_signal(
            latest.tiktok_followers,
            previous.tiktok_followers
        )
        adjustments += self.TIKTOK_WEIGHT * tiktok_signal
        
        # YouTube signal (-1 to +1)
        youtube_signal = self._calculate_source_signal(
            latest.youtube_subscribers,
            previous.youtube_subscribers
        )
        adjustments += self.YOUTUBE_WEIGHT * youtube_signal
        
        # Concerts signal (0 to +1, pas de négatif)
        concerts_signal = 0.0
        if latest.concerts_next_30d and latest.concerts_next_30d > 0:
            # Plus de concerts = signal positif, plafonné à 1
            concerts_signal = min(latest.concerts_next_30d / 5.0, 1.0)
        adjustments += self.CONCERTS_WEIGHT * concerts_signal
        
        return mu + adjustments
    
    def _calculate_source_signal(
        self,
        current: Optional[int],
        previous: Optional[int]
    ) -> float:
        """Calcule un signal normalisé entre -1 et +1"""
        if not current or not previous or previous == 0:
            return 0.0
        
        growth = (current - previous) / previous
        
        # Clamp entre -1 et +1
        return max(-1.0, min(1.0, growth))
    
    def _project_scenario(
        self,
        current_listeners: int,
        growth_rate: float
    ) -> PredictionScenario:
        """
        Projette les listeners futurs.
        listeners_future = listeners_now * exp(growth_rate * horizon)
        """
        # Projection à 30 jours
        value_30d = int(current_listeners * math.exp(growth_rate * 30))
        
        # Projection à 90 jours
        value_90d = int(current_listeners * math.exp(growth_rate * 90))
        
        # Garantir des valeurs positives
        value_30d = max(0, value_30d)
        value_90d = max(0, value_90d)
        
        return PredictionScenario(
            value_30d=value_30d,
            value_90d=value_90d,
            growth_rate=growth_rate
        )
    
    def _calculate_growth_probability(
        self,
        mu: float,
        sigma: float
    ) -> float:
        """
        Calcule la probabilité de croissance via sigmoid.
        growth_probability = sigmoid(mu / sigma)
        """
        if sigma == 0:
            return 50.0
        
        z = mu / sigma
        probability = 1 / (1 + math.exp(-z))
        
        return round(probability * 100, 1)
    
    def _calculate_confidence_score(
        self,
        snapshots: List[ArtistSnapshot]
    ) -> int:
        """
        Calcule le score de confiance (0-100) basé sur:
        - Nombre de snapshots
        - Ancienneté des données
        - Diversité des sources
        - Qualité des données
        """
        if not snapshots:
            return 0
        
        score = 0.0
        
        # 1. Nombre de snapshots (max 30 points)
        snapshot_score = min(len(snapshots) / self.OPTIMAL_SNAPSHOTS, 1.0) * 30
        score += snapshot_score
        
        # 2. Fraîcheur des données (max 25 points)
        latest = snapshots[0]
        days_old = (datetime.utcnow() - latest.snapshot_date).days
        freshness_score = max(0, 1 - days_old / self.MAX_DATA_AGE_DAYS) * 25
        score += freshness_score
        
        # 3. Diversité des sources (max 25 points)
        source_count = 0
        if latest.spotify_monthly_listeners:
            source_count += 1
        if latest.tiktok_followers:
            source_count += 1
        if latest.youtube_subscribers:
            source_count += 1
        if latest.instagram_followers:
            source_count += 1
        diversity_score = (source_count / 4) * 25
        score += diversity_score
        
        # 4. Qualité moyenne des données (max 20 points)
        avg_quality = sum(s.source_quality_score or 50 for s in snapshots) / len(snapshots)
        quality_score = (avg_quality / 100) * 20
        score += quality_score
        
        return int(min(100, max(0, score)))
    
    def _get_confidence_label(self, score: int) -> str:
        """Convertit le score en label"""
        if score >= 70:
            return "Élevée"
        elif score >= 40:
            return "Moyenne"
        else:
            return "Faible"
    
    def _prepare_historical_data(
        self,
        spotify_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prépare les données pour le graphique"""
        return [
            {
                "date": item["date"].isoformat(),
                "listeners": item["value"]
            }
            for item in spotify_data
        ]
    
    def _generate_explanations(
        self,
        snapshots: List[ArtistSnapshot],
        growth_rates: List[float],
        mu_adjusted: float
    ) -> List[PredictionExplanation]:
        """Génère les explications de la prédiction (max 3)"""
        explanations = []
        
        if len(snapshots) < 2:
            return explanations
        
        latest = snapshots[0]
        previous = snapshots[1]
        
        # 1. Tendance Spotify
        if len(growth_rates) >= 1:
            avg_growth = sum(growth_rates) / len(growth_rates)
            pct = avg_growth * 100 * 14  # Sur 14 jours approximatif
            
            if abs(pct) > 1:
                sign = "+" if pct > 0 else ""
                explanations.append(PredictionExplanation(
                    text=f"{sign}{pct:.0f}% d'auditeurs Spotify récemment",
                    impact="positive" if pct > 0 else "negative",
                    weight=0.7
                ))
        
        # 2. Signal TikTok
        if latest.tiktok_followers and previous.tiktok_followers:
            tiktok_growth = ((latest.tiktok_followers - previous.tiktok_followers) / previous.tiktok_followers) * 100
            if abs(tiktok_growth) > 3:
                sign = "+" if tiktok_growth > 0 else ""
                explanations.append(PredictionExplanation(
                    text=f"TikTok {sign}{tiktok_growth:.0f}%",
                    impact="positive" if tiktok_growth > 0 else "negative",
                    weight=0.15
                ))
        
        # 3. Concerts
        if latest.concerts_next_30d and latest.concerts_next_30d > 0:
            explanations.append(PredictionExplanation(
                text=f"{latest.concerts_next_30d} concert(s) annoncé(s)",
                impact="positive",
                weight=0.05
            ))
        
        # 4. YouTube
        if latest.youtube_subscribers and previous.youtube_subscribers:
            yt_growth = ((latest.youtube_subscribers - previous.youtube_subscribers) / previous.youtube_subscribers) * 100
            if abs(yt_growth) > 2:
                sign = "+" if yt_growth > 0 else ""
                explanations.append(PredictionExplanation(
                    text=f"YouTube {sign}{yt_growth:.0f}%",
                    impact="positive" if yt_growth > 0 else "negative",
                    weight=0.10
                ))
        
        # Trier par poids et limiter à 3
        explanations.sort(key=lambda x: x.weight, reverse=True)
        return explanations[:3]
    
    def _create_invalid_prediction(
        self,
        artist_name: str,
        error_message: str
    ) -> ArtistPrediction:
        """Crée une prédiction invalide avec message d'erreur"""
        empty_scenario = PredictionScenario(value_30d=0, value_90d=0, growth_rate=0.0)
        
        return ArtistPrediction(
            artist_name=artist_name,
            current_listeners=0,
            pessimistic=empty_scenario,
            central=empty_scenario,
            optimistic=empty_scenario,
            growth_probability=50.0,
            confidence_score=0,
            confidence_label="Faible",
            is_valid=False,
            error_message=error_message
        )
    
    # ========================================================================
    # SNAPSHOT MANAGEMENT
    # ========================================================================
    
    def create_snapshot(
        self,
        artist_name: str,
        workspace_id: Optional[int],
        spotify_monthly_listeners: Optional[int] = None,
        spotify_followers: Optional[int] = None,
        tiktok_followers: Optional[int] = None,
        youtube_subscribers: Optional[int] = None,
        youtube_views_30d: Optional[int] = None,
        instagram_followers: Optional[int] = None,
        concerts_next_30d: int = 0,
        concerts_next_90d: int = 0,
        source_quality_score: float = 50.0,
        sources_used: Optional[str] = None
    ) -> ArtistSnapshot:
        """Crée un nouveau snapshot pour un artiste"""
        snapshot = ArtistSnapshot(
            artist_name=artist_name,
            artist_name_normalized=ArtistSnapshot.normalize_name(artist_name),
            workspace_id=workspace_id,
            snapshot_date=datetime.utcnow(),
            spotify_monthly_listeners=spotify_monthly_listeners,
            spotify_followers=spotify_followers,
            tiktok_followers=tiktok_followers,
            youtube_subscribers=youtube_subscribers,
            youtube_views_30d=youtube_views_30d,
            instagram_followers=instagram_followers,
            concerts_next_30d=concerts_next_30d,
            concerts_next_90d=concerts_next_90d,
            source_quality_score=source_quality_score,
            sources_used=sources_used
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        logger.info(f"Created snapshot for {artist_name} with {spotify_monthly_listeners} listeners")
        
        return snapshot
    
    def get_snapshot_count(
        self,
        artist_name: str,
        workspace_id: Optional[int] = None
    ) -> int:
        """Retourne le nombre de snapshots pour un artiste"""
        normalized_name = ArtistSnapshot.normalize_name(artist_name)
        
        query = self.db.query(func.count(ArtistSnapshot.id)).filter(
            ArtistSnapshot.artist_name_normalized == normalized_name
        )
        
        if workspace_id:
            query = query.filter(ArtistSnapshot.workspace_id == workspace_id)
        
        return query.scalar() or 0
