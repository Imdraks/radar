"""
Artist Intelligence Engine 2.0
Advanced AI-powered artist analysis with predictive capabilities
"""
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GrowthTrend(Enum):
    """Artist growth trend classification"""
    EXPLOSIVE = "explosive"      # >100% monthly growth
    RAPID = "rapid"              # 50-100% monthly growth
    STRONG = "strong"            # 20-50% monthly growth
    MODERATE = "moderate"        # 5-20% monthly growth
    STABLE = "stable"            # -5% to 5% monthly growth
    DECLINING = "declining"      # -20% to -5% monthly growth
    FALLING = "falling"          # <-20% monthly growth


class ArtistTier(Enum):
    """Artist classification tier"""
    SUPERSTAR = "superstar"       # >10M monthly listeners
    MAJOR = "major"               # 1M-10M monthly listeners
    ESTABLISHED = "established"  # 100K-1M monthly listeners
    RISING = "rising"            # 10K-100K monthly listeners
    EMERGING = "emerging"        # 1K-10K monthly listeners
    UNDERGROUND = "underground"  # <1K monthly listeners


class MarketPosition(Enum):
    """Artist market position relative to peers"""
    LEADER = "leader"            # Top 10% in genre
    CONTENDER = "contender"      # Top 25%
    COMPETITIVE = "competitive"  # Top 50%
    DEVELOPING = "developing"    # Bottom 50%


@dataclass
class TrendPrediction:
    """Prediction for future metrics"""
    metric_name: str
    current_value: int
    predicted_value_30d: int
    predicted_value_90d: int
    predicted_value_180d: int
    confidence: float  # 0-1
    growth_rate_monthly: float  # percentage
    trend: GrowthTrend


@dataclass
class MarketAnalysis:
    """Market position analysis"""
    tier: ArtistTier
    position: MarketPosition
    genre_rank_estimate: int  # Estimated rank in genre
    similar_artists: List[str]
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]


@dataclass
class BookingIntelligence:
    """Intelligent booking recommendations"""
    estimated_fee_min: int
    estimated_fee_max: int
    optimal_fee: int
    negotiation_power: str  # "low", "medium", "high"
    best_booking_window: str  # "1-2 months", "3-6 months", etc.
    event_type_fit: Dict[str, float]  # festival: 0.9, club: 0.7, etc.
    territory_strength: Dict[str, float]  # France: 0.9, Belgium: 0.7, etc.
    seasonal_demand: Dict[str, float]  # summer: 0.9, winter: 0.6, etc.


@dataclass
class ContentStrategy:
    """Content and engagement strategy recommendations"""
    best_platforms: List[str]
    posting_frequency: Dict[str, str]
    engagement_rate: float
    viral_potential: float
    content_recommendations: List[str]
    collaboration_suggestions: List[str]


@dataclass
class ArtistIntelligenceReport:
    """Complete AI intelligence report for an artist"""
    artist_name: str
    analysis_date: datetime
    overall_score: float  # 0-100
    confidence_score: float  # 0-1
    
    # Core metrics
    tier: ArtistTier
    market_analysis: MarketAnalysis
    
    # Predictions
    listener_prediction: TrendPrediction
    social_prediction: TrendPrediction
    overall_trend: GrowthTrend
    
    # Intelligence
    booking_intelligence: BookingIntelligence
    content_strategy: ContentStrategy
    
    # Risk assessment
    risk_score: float  # 0-1, higher = more risky
    risk_factors: List[str]
    
    # Opportunities
    opportunity_score: float  # 0-1
    key_opportunities: List[str]
    
    # AI insights
    ai_summary: str
    recommendations: List[str]


class ArtistIntelligenceEngine:
    """
    Advanced AI engine for artist analysis and predictions.
    Uses statistical analysis and heuristic models for predictions.
    """
    
    # Genre benchmarks (average monthly listeners for "established" artist)
    GENRE_BENCHMARKS = {
        "pop": 500000,
        "hip-hop": 400000,
        "rap": 400000,
        "electronic": 200000,
        "dance": 200000,
        "rock": 300000,
        "indie": 150000,
        "r&b": 250000,
        "jazz": 50000,
        "classical": 30000,
        "metal": 100000,
        "folk": 80000,
        "country": 200000,
        "latin": 350000,
        "reggaeton": 400000,
        "afrobeat": 150000,
        "default": 200000,
    }
    
    # Fee multipliers by tier
    FEE_MULTIPLIERS = {
        ArtistTier.SUPERSTAR: (150000, 500000),
        ArtistTier.MAJOR: (30000, 150000),
        ArtistTier.ESTABLISHED: (8000, 30000),
        ArtistTier.RISING: (2000, 8000),
        ArtistTier.EMERGING: (500, 2000),
        ArtistTier.UNDERGROUND: (200, 500),
    }
    
    def __init__(self):
        self.analysis_cache: Dict[str, ArtistIntelligenceReport] = {}
    
    def analyze_artist(
        self,
        artist_name: str,
        spotify_monthly_listeners: int = 0,
        spotify_followers: int = 0,
        youtube_subscribers: int = 0,
        instagram_followers: int = 0,
        tiktok_followers: int = 0,
        genre: str = "default",
        country: str = "FR",
        historical_data: Optional[List[Dict]] = None,
        known_events: Optional[List[Dict]] = None,
        # New: Accept scanner's fee estimates as reference
        scanner_fee_min: Optional[int] = None,
        scanner_fee_max: Optional[int] = None,
        scanner_tier: Optional[str] = None,
    ) -> ArtistIntelligenceReport:
        """
        Generate comprehensive AI intelligence report for an artist.
        
        Args:
            scanner_fee_min: Fee estimate from web scanner (more reliable)
            scanner_fee_max: Fee estimate from web scanner (more reliable)
            scanner_tier: Market tier from web scanner
        """
        logger.info(f"Generating intelligence report for {artist_name}")
        
        # Calculate core metrics - prefer scanner tier if available
        if scanner_tier:
            tier = self._tier_from_string(scanner_tier)
            logger.info(f"Using scanner tier: {tier.value}")
        else:
            tier = self._calculate_tier(spotify_monthly_listeners)
        
        # Calculate growth trends
        listener_prediction = self._predict_growth(
            "monthly_listeners",
            spotify_monthly_listeners,
            historical_data,
            genre
        )
        
        total_social = youtube_subscribers + instagram_followers + tiktok_followers + spotify_followers
        social_prediction = self._predict_growth(
            "total_followers",
            total_social,
            historical_data,
            genre
        )
        
        # Market analysis
        market_analysis = self._analyze_market_position(
            artist_name,
            spotify_monthly_listeners,
            total_social,
            genre,
            tier
        )
        
        # Booking intelligence - use scanner fees if available
        booking_intelligence = self._calculate_booking_intelligence(
            tier,
            spotify_monthly_listeners,
            total_social,
            genre,
            country,
            listener_prediction.trend,
            known_events,
            scanner_fee_min=scanner_fee_min,
            scanner_fee_max=scanner_fee_max,
        )
        
        # Content strategy
        content_strategy = self._generate_content_strategy(
            youtube_subscribers,
            instagram_followers,
            tiktok_followers,
            spotify_followers,
            tier
        )
        
        # Risk assessment
        risk_score, risk_factors = self._assess_risks(
            listener_prediction,
            social_prediction,
            tier,
            historical_data
        )
        
        # Opportunity assessment
        opportunity_score, key_opportunities = self._identify_opportunities(
            tier,
            listener_prediction.trend,
            market_analysis,
            booking_intelligence
        )
        
        # Overall trend
        overall_trend = self._determine_overall_trend(
            listener_prediction.trend,
            social_prediction.trend
        )
        
        # Calculate scores
        overall_score = self._calculate_overall_score(
            tier,
            listener_prediction,
            social_prediction,
            market_analysis,
            risk_score,
            opportunity_score
        )
        
        confidence_score = self._calculate_confidence(
            spotify_monthly_listeners,
            total_social,
            historical_data
        )
        
        # Generate AI insights
        ai_summary, recommendations = self._generate_ai_insights(
            artist_name,
            tier,
            overall_trend,
            market_analysis,
            booking_intelligence,
            risk_factors,
            key_opportunities
        )
        
        report = ArtistIntelligenceReport(
            artist_name=artist_name,
            analysis_date=datetime.utcnow(),
            overall_score=overall_score,
            confidence_score=confidence_score,
            tier=tier,
            market_analysis=market_analysis,
            listener_prediction=listener_prediction,
            social_prediction=social_prediction,
            overall_trend=overall_trend,
            booking_intelligence=booking_intelligence,
            content_strategy=content_strategy,
            risk_score=risk_score,
            risk_factors=risk_factors,
            opportunity_score=opportunity_score,
            key_opportunities=key_opportunities,
            ai_summary=ai_summary,
            recommendations=recommendations
        )
        
        # Cache the report
        self.analysis_cache[artist_name.lower()] = report
        
        return report
    
    def _tier_from_string(self, tier_str: str) -> ArtistTier:
        """Convert tier string from scanner to ArtistTier enum"""
        tier_map = {
            "underground": ArtistTier.UNDERGROUND,
            "emerging": ArtistTier.EMERGING,
            "rising": ArtistTier.RISING,
            "established": ArtistTier.ESTABLISHED,
            "major": ArtistTier.MAJOR,
            "star": ArtistTier.MAJOR,  # Map star to major
            "superstar": ArtistTier.SUPERSTAR,
            "mega_star": ArtistTier.SUPERSTAR,
        }
        return tier_map.get(tier_str.lower(), ArtistTier.ESTABLISHED)
    
    def _calculate_tier(self, monthly_listeners: int) -> ArtistTier:
        """Classify artist into tier based on monthly listeners"""
        if monthly_listeners >= 10_000_000:
            return ArtistTier.SUPERSTAR
        elif monthly_listeners >= 1_000_000:
            return ArtistTier.MAJOR
        elif monthly_listeners >= 100_000:
            return ArtistTier.ESTABLISHED
        elif monthly_listeners >= 10_000:
            return ArtistTier.RISING
        elif monthly_listeners >= 1_000:
            return ArtistTier.EMERGING
        else:
            return ArtistTier.UNDERGROUND
    
    def _predict_growth(
        self,
        metric_name: str,
        current_value: int,
        historical_data: Optional[List[Dict]],
        genre: str
    ) -> TrendPrediction:
        """Predict future growth based on current data and trends"""
        
        # If we have historical data, calculate actual growth rate
        if historical_data and len(historical_data) >= 2:
            values = [d.get(metric_name, current_value) for d in historical_data[-6:]]
            if len(values) >= 2 and values[0] > 0:
                total_growth = (values[-1] - values[0]) / values[0]
                months = len(values) - 1
                monthly_growth = total_growth / months if months > 0 else 0
                confidence = min(0.9, 0.5 + len(historical_data) * 0.05)
            else:
                monthly_growth = 0.05  # Default 5% monthly
                confidence = 0.3
        else:
            # Estimate based on tier and genre
            benchmark = self.GENRE_BENCHMARKS.get(genre.lower(), self.GENRE_BENCHMARKS["default"])
            if current_value < benchmark * 0.1:
                monthly_growth = 0.15  # Emerging artists often grow faster
            elif current_value < benchmark:
                monthly_growth = 0.08
            else:
                monthly_growth = 0.03  # Established artists grow slower
            confidence = 0.4
        
        # Calculate predictions
        predicted_30d = int(current_value * (1 + monthly_growth))
        predicted_90d = int(current_value * (1 + monthly_growth) ** 3)
        predicted_180d = int(current_value * (1 + monthly_growth) ** 6)
        
        # Determine trend
        if monthly_growth > 1.0:
            trend = GrowthTrend.EXPLOSIVE
        elif monthly_growth > 0.5:
            trend = GrowthTrend.RAPID
        elif monthly_growth > 0.2:
            trend = GrowthTrend.STRONG
        elif monthly_growth > 0.05:
            trend = GrowthTrend.MODERATE
        elif monthly_growth > -0.05:
            trend = GrowthTrend.STABLE
        elif monthly_growth > -0.2:
            trend = GrowthTrend.DECLINING
        else:
            trend = GrowthTrend.FALLING
        
        return TrendPrediction(
            metric_name=metric_name,
            current_value=current_value,
            predicted_value_30d=predicted_30d,
            predicted_value_90d=predicted_90d,
            predicted_value_180d=predicted_180d,
            confidence=confidence,
            growth_rate_monthly=monthly_growth * 100,
            trend=trend
        )
    
    def _analyze_market_position(
        self,
        artist_name: str,
        monthly_listeners: int,
        total_social: int,
        genre: str,
        tier: ArtistTier
    ) -> MarketAnalysis:
        """Analyze artist's market position"""
        
        benchmark = self.GENRE_BENCHMARKS.get(genre.lower(), self.GENRE_BENCHMARKS["default"])
        
        # Estimate rank in genre (simplified model)
        if monthly_listeners >= benchmark * 10:
            position = MarketPosition.LEADER
            rank = max(1, int(10 - (monthly_listeners / benchmark)))
        elif monthly_listeners >= benchmark * 2:
            position = MarketPosition.CONTENDER
            rank = max(10, int(100 - (monthly_listeners / benchmark) * 10))
        elif monthly_listeners >= benchmark * 0.5:
            position = MarketPosition.COMPETITIVE
            rank = max(100, int(500 - (monthly_listeners / benchmark) * 50))
        else:
            position = MarketPosition.DEVELOPING
            rank = max(500, int(1000 - (monthly_listeners / benchmark) * 100))
        
        # SWOT Analysis
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []
        
        # Strengths (Forces)
        if tier in [ArtistTier.SUPERSTAR, ArtistTier.MAJOR]:
            strengths.append("Large base de fans établie")
        if total_social > monthly_listeners * 2:
            strengths.append("Forte présence sur les réseaux sociaux")
        if monthly_listeners > benchmark:
            strengths.append(f"Au-dessus de la moyenne dans le genre {genre}")
        
        # Weaknesses (Faiblesses)
        if total_social < monthly_listeners * 0.5:
            weaknesses.append("Faible engagement sur les réseaux sociaux")
        if tier in [ArtistTier.UNDERGROUND, ArtistTier.EMERGING]:
            weaknesses.append("Visibilité limitée sur le marché")
        
        # Opportunities (Opportunités)
        if tier in [ArtistTier.RISING, ArtistTier.EMERGING]:
            opportunities.append("Fort potentiel de croissance")
        if total_social < monthly_listeners:
            opportunities.append("Potentiel réseaux sociaux inexploité")
        opportunities.append("Expansion de contenu multi-plateformes")
        
        # Threats (Menaces)
        if tier == ArtistTier.UNDERGROUND:
            threats.append("Saturation du marché dans le genre")
        threats.append("Dépendance aux algorithmes de streaming")
        
        return MarketAnalysis(
            tier=tier,
            position=position,
            genre_rank_estimate=rank,
            similar_artists=[],  # Would need external data
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats
        )
    
    def _calculate_booking_intelligence(
        self,
        tier: ArtistTier,
        monthly_listeners: int,
        total_social: int,
        genre: str,
        country: str,
        trend: GrowthTrend,
        known_events: Optional[List[Dict]],
        scanner_fee_min: Optional[int] = None,
        scanner_fee_max: Optional[int] = None,
    ) -> BookingIntelligence:
        """Calculate intelligent booking recommendations"""
        
        # Use scanner fees if available (more reliable from known artists DB)
        if scanner_fee_min and scanner_fee_max and scanner_fee_min > 0:
            base_min = scanner_fee_min
            base_max = scanner_fee_max
            logger.info(f"Using scanner fees as base: {base_min:,}€ - {base_max:,}€")
        else:
            # Fallback to tier-based calculation
            base_min, base_max = self.FEE_MULTIPLIERS[tier]
        
        # Adjust for trend (smaller adjustment since scanner fees are already accurate)
        trend_multiplier = {
            GrowthTrend.EXPLOSIVE: 1.15,
            GrowthTrend.RAPID: 1.10,
            GrowthTrend.STRONG: 1.05,
            GrowthTrend.MODERATE: 1.02,
            GrowthTrend.STABLE: 1.0,
            GrowthTrend.DECLINING: 0.95,
            GrowthTrend.FALLING: 0.90,
        }.get(trend, 1.0)
        
        # Adjust for social engagement (smaller impact)
        engagement_ratio = total_social / max(monthly_listeners, 1)
        engagement_multiplier = min(1.1, max(0.9, 0.95 + engagement_ratio * 0.05))
        
        # Calculate fees
        fee_min = int(base_min * trend_multiplier * engagement_multiplier)
        fee_max = int(base_max * trend_multiplier * engagement_multiplier)
        optimal_fee = int((fee_min + fee_max * 0.7) / 1.7)  # Weighted towards lower end (negotiation advantage)
        
        # Negotiation power
        if trend in [GrowthTrend.EXPLOSIVE, GrowthTrend.RAPID]:
            negotiation_power = "high"
        elif trend in [GrowthTrend.STRONG, GrowthTrend.MODERATE]:
            negotiation_power = "medium"
        else:
            negotiation_power = "low"
        
        # Event type fit (simplified model based on tier)
        event_type_fit = {
            "festival": 0.9 if tier in [ArtistTier.MAJOR, ArtistTier.ESTABLISHED] else 0.6,
            "club": 0.8 if tier in [ArtistTier.RISING, ArtistTier.EMERGING] else 0.5,
            "concert_hall": 0.9 if tier in [ArtistTier.MAJOR, ArtistTier.SUPERSTAR] else 0.4,
            "private_event": 0.7,
            "corporate": 0.6 if tier in [ArtistTier.ESTABLISHED, ArtistTier.MAJOR] else 0.4,
        }
        
        # Territory strength (simplified - would need real data)
        territory_strength = {
            "France": 1.0 if country == "FR" else 0.6,
            "Belgium": 0.8,
            "Switzerland": 0.7,
            "Germany": 0.5,
            "UK": 0.5,
            "USA": 0.3 if tier.value not in ["superstar", "major"] else 0.7,
        }
        
        # Seasonal demand
        seasonal_demand = {
            "summer": 0.95,
            "spring": 0.8,
            "fall": 0.75,
            "winter": 0.6,
        }
        
        # Booking window recommendation
        if trend in [GrowthTrend.EXPLOSIVE, GrowthTrend.RAPID]:
            booking_window = "6-12 mois (forte demande attendue)"
        elif tier in [ArtistTier.SUPERSTAR, ArtistTier.MAJOR]:
            booking_window = "6-18 mois"
        else:
            booking_window = "2-6 mois"
        
        return BookingIntelligence(
            estimated_fee_min=fee_min,
            estimated_fee_max=fee_max,
            optimal_fee=optimal_fee,
            negotiation_power=negotiation_power,
            best_booking_window=booking_window,
            event_type_fit=event_type_fit,
            territory_strength=territory_strength,
            seasonal_demand=seasonal_demand
        )
    
    def _generate_content_strategy(
        self,
        youtube: int,
        instagram: int,
        tiktok: int,
        spotify_followers: int,
        tier: ArtistTier
    ) -> ContentStrategy:
        """Generate content strategy recommendations"""
        
        total = youtube + instagram + tiktok + spotify_followers
        
        # Identify best platforms
        platforms = []
        if youtube > total * 0.3:
            platforms.append("YouTube")
        if instagram > total * 0.25:
            platforms.append("Instagram")
        if tiktok > total * 0.2:
            platforms.append("TikTok")
        platforms.append("Spotify")
        
        if not platforms:
            platforms = ["TikTok", "Instagram", "Spotify"]
        
        # Posting frequency
        posting_frequency = {
            "TikTok": "3-5x par semaine",
            "Instagram": "1x par jour (stories: 3-5x)",
            "YouTube": "1-2x par mois",
            "Twitter": "2-3x par jour",
        }
        
        # Engagement rate estimation
        if total > 0:
            # Simplified: assume 2-5% typical engagement
            engagement_rate = 0.035
        else:
            engagement_rate = 0.02
        
        # Viral potential based on TikTok presence and tier
        viral_potential = 0.3
        if tiktok > instagram:
            viral_potential += 0.2
        if tier in [ArtistTier.RISING, ArtistTier.EMERGING]:
            viral_potential += 0.2
        viral_potential = min(0.9, viral_potential)
        
        # Content recommendations
        content_recs = [
            "Behind-the-scenes content en studio",
            "Covers acoustiques de hits actuels",
            "Collaborations avec d'autres artistes",
            "Lives interactifs avec les fans",
        ]
        
        if tiktok > 0:
            content_recs.append("Trends TikTok avec musique originale")
        if tier in [ArtistTier.RISING, ArtistTier.EMERGING]:
            content_recs.append("Challenges utilisateurs pour viralité")
        
        # Collaboration suggestions
        collab_suggestions = [
            "Featurings avec artistes du même genre",
            "Partenariats avec influenceurs musicaux",
            "Playlists collaboratives Spotify",
        ]
        
        return ContentStrategy(
            best_platforms=platforms,
            posting_frequency=posting_frequency,
            engagement_rate=engagement_rate,
            viral_potential=viral_potential,
            content_recommendations=content_recs,
            collaboration_suggestions=collab_suggestions
        )
    
    def _assess_risks(
        self,
        listener_pred: TrendPrediction,
        social_pred: TrendPrediction,
        tier: ArtistTier,
        historical_data: Optional[List[Dict]]
    ) -> Tuple[float, List[str]]:
        """Assess risks for the artist"""
        
        risk_score = 0.3  # Base risk
        risk_factors = []
        
        # Trend risks
        if listener_pred.trend in [GrowthTrend.DECLINING, GrowthTrend.FALLING]:
            risk_score += 0.25
            risk_factors.append("Tendance à la baisse des écoutes")
        
        if social_pred.trend in [GrowthTrend.DECLINING, GrowthTrend.FALLING]:
            risk_score += 0.15
            risk_factors.append("Engagement social en déclin")
        
        # Tier risks
        if tier == ArtistTier.UNDERGROUND:
            risk_score += 0.2
            risk_factors.append("Faible visibilité marché")
        
        # Volatility (if we have historical data)
        if historical_data and len(historical_data) >= 3:
            values = [d.get("monthly_listeners", 0) for d in historical_data]
            if values and max(values) > 0:
                volatility = statistics.stdev(values) / max(values) if len(values) > 1 else 0
                if volatility > 0.3:
                    risk_score += 0.15
                    risk_factors.append("Forte volatilité des métriques")
        
        # Single platform dependency
        risk_factors.append("Dépendance aux algorithmes de streaming")
        
        return min(1.0, risk_score), risk_factors
    
    def _identify_opportunities(
        self,
        tier: ArtistTier,
        trend: GrowthTrend,
        market: MarketAnalysis,
        booking: BookingIntelligence
    ) -> Tuple[float, List[str]]:
        """Identify opportunities for the artist"""
        
        opportunity_score = 0.4  # Base
        opportunities = []
        
        # Growth opportunity
        if trend in [GrowthTrend.EXPLOSIVE, GrowthTrend.RAPID, GrowthTrend.STRONG]:
            opportunity_score += 0.3
            opportunities.append("Forte croissance - moment idéal pour réservation")
        
        # Tier opportunity
        if tier in [ArtistTier.RISING, ArtistTier.EMERGING]:
            opportunity_score += 0.15
            opportunities.append("Artiste émergent - potentiel de découverte")
        
        # Price opportunity
        if booking.negotiation_power == "low":
            opportunities.append("Tarif négociable - bon rapport qualité/prix")
        
        # Market opportunities
        opportunities.extend(market.opportunities[:2])
        
        return min(1.0, opportunity_score), opportunities
    
    def _determine_overall_trend(
        self,
        listener_trend: GrowthTrend,
        social_trend: GrowthTrend
    ) -> GrowthTrend:
        """Determine overall trend from multiple metrics"""
        
        trend_values = {
            GrowthTrend.EXPLOSIVE: 3,
            GrowthTrend.RAPID: 2,
            GrowthTrend.STRONG: 1,
            GrowthTrend.MODERATE: 0,
            GrowthTrend.STABLE: -0.5,
            GrowthTrend.DECLINING: -1,
            GrowthTrend.FALLING: -2,
        }
        
        avg = (trend_values[listener_trend] * 0.6 + trend_values[social_trend] * 0.4)
        
        if avg >= 2.5:
            return GrowthTrend.EXPLOSIVE
        elif avg >= 1.5:
            return GrowthTrend.RAPID
        elif avg >= 0.5:
            return GrowthTrend.STRONG
        elif avg >= -0.25:
            return GrowthTrend.MODERATE
        elif avg >= -0.75:
            return GrowthTrend.STABLE
        elif avg >= -1.5:
            return GrowthTrend.DECLINING
        else:
            return GrowthTrend.FALLING
    
    def _calculate_overall_score(
        self,
        tier: ArtistTier,
        listener_pred: TrendPrediction,
        social_pred: TrendPrediction,
        market: MarketAnalysis,
        risk_score: float,
        opportunity_score: float
    ) -> float:
        """Calculate overall artist score (0-100)"""
        
        # Base score from tier
        tier_scores = {
            ArtistTier.SUPERSTAR: 90,
            ArtistTier.MAJOR: 75,
            ArtistTier.ESTABLISHED: 60,
            ArtistTier.RISING: 50,
            ArtistTier.EMERGING: 35,
            ArtistTier.UNDERGROUND: 20,
        }
        base = tier_scores[tier]
        
        # Growth bonus
        growth_bonus = listener_pred.growth_rate_monthly * 0.5
        growth_bonus = min(15, max(-10, growth_bonus))
        
        # Market position bonus
        position_bonus = {
            MarketPosition.LEADER: 10,
            MarketPosition.CONTENDER: 5,
            MarketPosition.COMPETITIVE: 0,
            MarketPosition.DEVELOPING: -5,
        }[market.position]
        
        # Risk/opportunity adjustment
        risk_adj = (opportunity_score - risk_score) * 10
        
        score = base + growth_bonus + position_bonus + risk_adj
        return max(0, min(100, score))
    
    def _calculate_confidence(
        self,
        monthly_listeners: int,
        total_social: int,
        historical_data: Optional[List[Dict]]
    ) -> float:
        """Calculate confidence in the analysis"""
        
        confidence = 0.3  # Base
        
        # More data = more confidence
        if monthly_listeners > 1000:
            confidence += 0.2
        if total_social > 1000:
            confidence += 0.15
        if historical_data and len(historical_data) >= 3:
            confidence += 0.2
        if historical_data and len(historical_data) >= 6:
            confidence += 0.1
        
        return min(0.95, confidence)
    
    def _generate_ai_insights(
        self,
        artist_name: str,
        tier: ArtistTier,
        trend: GrowthTrend,
        market: MarketAnalysis,
        booking: BookingIntelligence,
        risks: List[str],
        opportunities: List[str]
    ) -> Tuple[str, List[str]]:
        """Generate AI-powered insights and recommendations"""
        
        # Build summary
        tier_desc = {
            ArtistTier.SUPERSTAR: "une superstar internationale",
            ArtistTier.MAJOR: "un artiste majeur",
            ArtistTier.ESTABLISHED: "un artiste établi",
            ArtistTier.RISING: "un artiste en pleine ascension",
            ArtistTier.EMERGING: "un artiste émergent prometteur",
            ArtistTier.UNDERGROUND: "un artiste underground",
        }[tier]
        
        trend_desc = {
            GrowthTrend.EXPLOSIVE: "une croissance explosive",
            GrowthTrend.RAPID: "une croissance rapide",
            GrowthTrend.STRONG: "une forte croissance",
            GrowthTrend.MODERATE: "une croissance modérée",
            GrowthTrend.STABLE: "une audience stable",
            GrowthTrend.DECLINING: "un léger déclin",
            GrowthTrend.FALLING: "une baisse significative",
        }[trend]
        
        summary = (
            f"{artist_name} est {tier_desc} avec {trend_desc}. "
            f"Le cachet estimé se situe entre {booking.estimated_fee_min:,}€ et {booking.estimated_fee_max:,}€. "
        )
        
        if trend in [GrowthTrend.EXPLOSIVE, GrowthTrend.RAPID]:
            summary += "C'est un moment stratégique pour le booker avant que ses tarifs n'augmentent."
        elif trend in [GrowthTrend.DECLINING, GrowthTrend.FALLING]:
            summary += "Attention à la tendance négative - négociation possible mais risque à évaluer."
        else:
            summary += "Un choix solide avec un bon rapport qualité/prix."
        
        # Generate recommendations
        recommendations = []
        
        if booking.negotiation_power == "low":
            recommendations.append(f"💰 Négociation possible - viser {booking.optimal_fee:,}€ ou moins")
        elif booking.negotiation_power == "high":
            recommendations.append(f"⚡ Artiste en forte demande - prévoir {booking.estimated_fee_max:,}€ minimum")
        
        recommendations.append(f"📅 Fenêtre de booking recommandée: {booking.best_booking_window}")
        
        if opportunities:
            recommendations.append(f"✨ Opportunité: {opportunities[0]}")
        
        if risks:
            recommendations.append(f"⚠️ Risque: {risks[0]}")
        
        if market.strengths:
            recommendations.append(f"💪 Point fort: {market.strengths[0]}")
        
        return summary, recommendations
    
    def compare_artists(
        self,
        reports: List[ArtistIntelligenceReport]
    ) -> Dict[str, Any]:
        """Compare multiple artist reports"""
        
        if len(reports) < 2:
            return {"error": "Need at least 2 artists to compare"}
        
        comparison = {
            "artists": [r.artist_name for r in reports],
            "scores": {r.artist_name: r.overall_score for r in reports},
            "tiers": {r.artist_name: r.tier.value for r in reports},
            "trends": {r.artist_name: r.overall_trend.value for r in reports},
            "fees": {
                r.artist_name: {
                    "min": r.booking_intelligence.estimated_fee_min,
                    "max": r.booking_intelligence.estimated_fee_max,
                    "optimal": r.booking_intelligence.optimal_fee
                }
                for r in reports
            },
            "best_value": min(reports, key=lambda r: r.booking_intelligence.optimal_fee / max(r.overall_score, 1)).artist_name,
            "highest_potential": max(reports, key=lambda r: r.opportunity_score).artist_name,
            "lowest_risk": min(reports, key=lambda r: r.risk_score).artist_name,
        }
        
        return comparison


# Singleton instance
intelligence_engine = ArtistIntelligenceEngine()
