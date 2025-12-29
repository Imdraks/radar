"""
Intelligence module - Smart crawling and analysis
Moteur intelligent de collecte et d'analyse d'opportunités
"""
from .smart_crawler import SmartCrawler
from .price_extractor import PriceExtractor, PriceType, ExtractedPrice
from .contact_extractor import ContactExtractor, ContactType, ExtractedContact
from .artist_analyzer import ArtistAnalyzer, ArtistProfile, ArtistEvent
from .radar_scorer import RadarScorer, ScoringResult, LeadGrade, TimingScore
# Alias for backward compatibility
OpportunityScorer = RadarScorer
OpportunityGrade = LeadGrade
from .engine import IntelligenceEngine, get_intelligence_engine

__all__ = [
    # Main components
    "SmartCrawler",
    "PriceExtractor",
    "ContactExtractor",
    "ArtistAnalyzer",
    "OpportunityScorer",
    "IntelligenceEngine",
    # Factory
    "get_intelligence_engine",
    # Types
    "PriceType",
    "ExtractedPrice",
    "ContactType",
    "ExtractedContact",
    "ArtistProfile",
    "ArtistEvent",
    "ScoringResult",
    "OpportunityGrade",
    "TimingScore",
]
