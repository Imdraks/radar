"""
Web Artist Scanner - Scanne les sources fiables du web pour analyser un artiste
Utilise d'abord une base de données d'artistes connus pour des estimations précises.
"""
import re
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus
import logging
from bs4 import BeautifulSoup

# Playwright pour le scraping JavaScript (Spotify)
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .known_artists_db import get_known_artist, KnownArtistData
from .spotify_client import spotify_client

# Import du nouveau système de scoring
from app.scoring import (
    ArtistScorer,
    SpotifyData,
    SocialData,
    LiveData,
    Trend,
)

logger = logging.getLogger(__name__)


@dataclass
class SocialMetrics:
    """Métriques des réseaux sociaux"""
    platform: str
    followers: int = 0
    monthly_listeners: int = 0  # Spotify
    views: int = 0  # YouTube
    engagement_rate: float = 0.0
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'platform': self.platform,
            'followers': self.followers,
            'monthly_listeners': self.monthly_listeners,
            'views': self.views,
            'engagement_rate': self.engagement_rate,
            'url': self.url,
        }


@dataclass
class ConcertInfo:
    """Information sur un concert passé ou futur"""
    name: str
    date: Optional[str]
    venue: str
    city: str
    country: str = "France"
    ticket_price_min: Optional[float] = None
    ticket_price_max: Optional[float] = None
    is_sold_out: bool = False
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'date': self.date,
            'venue': self.venue,
            'city': self.city,
            'country': self.country,
            'ticket_price_range': {
                'min': self.ticket_price_min,
                'max': self.ticket_price_max,
            } if self.ticket_price_min else None,
            'is_sold_out': self.is_sold_out,
            'source': self.source,
        }


@dataclass
class WebArtistProfile:
    """Profil complet d'un artiste scanné depuis le web"""
    name: str
    real_name: Optional[str] = None
    genre: str = "Unknown"
    sub_genres: List[str] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)  # Alias pour sub_genres (compatibilité)
    nationality: str = "France"
    country: Optional[str] = None  # Pays détecté (Viberate)
    birth_year: Optional[int] = None
    image_url: Optional[str] = None  # Photo de l'artiste (Spotify)
    
    # Métriques sociales
    social_metrics: List[SocialMetrics] = field(default_factory=list)
    total_followers: int = 0
    spotify_monthly_listeners: int = 0
    spotify_followers: int = 0
    youtube_subscribers: int = 0
    youtube_total_views: int = 0
    instagram_followers: int = 0
    tiktok_followers: int = 0
    
    # Concerts et événements
    upcoming_concerts: List[ConcertInfo] = field(default_factory=list)
    past_concerts: List[ConcertInfo] = field(default_factory=list)
    festivals_played: List[str] = field(default_factory=list)
    
    # Estimation financière
    estimated_fee_min: float = 0
    estimated_fee_max: float = 0
    popularity_score: float = 0  # 0-100
    market_tier: str = "emerging"  # emerging, developing, established, star, superstar
    
    # Contacts et business
    record_label: Optional[str] = None
    management: Optional[str] = None
    booking_agency: Optional[str] = None
    booking_email: Optional[str] = None
    
    # Analyse
    market_trend: str = "stable"  # rising, stable, declining
    career_stage: str = "active"
    last_album: Optional[str] = None
    last_album_year: Optional[int] = None
    
    # Sources utilisées
    sources_scanned: List[str] = field(default_factory=list)
    scan_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence_score: float = 0  # 0-100 - confiance dans les données
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'real_name': self.real_name,
            'genre': self.genre,
            'sub_genres': self.sub_genres,
            'genres': self.genres,
            'nationality': self.nationality,
            'country': self.country,
            'birth_year': self.birth_year,
            'image_url': self.image_url,
            'social_metrics': {
                'total_followers': self.total_followers,
                'spotify_monthly_listeners': self.spotify_monthly_listeners,
                'spotify_followers': self.spotify_followers,
                'youtube_subscribers': self.youtube_subscribers,
                'youtube_total_views': self.youtube_total_views,
                'instagram_followers': self.instagram_followers,
                'tiktok_followers': self.tiktok_followers,
                'platforms': [m.to_dict() for m in self.social_metrics],
            },
            'concerts': {
                'upcoming': [c.to_dict() for c in self.upcoming_concerts],
                'past': [c.to_dict() for c in self.past_concerts],
                'festivals_played': self.festivals_played,
            },
            'financials': {
                'estimated_fee_min': self.estimated_fee_min,
                'estimated_fee_max': self.estimated_fee_max,
                'market_tier': self.market_tier,
                'popularity_score': self.popularity_score,
            },
            'business': {
                'record_label': self.record_label,
                'management': self.management,
                'booking_agency': self.booking_agency,
                'booking_email': self.booking_email,
            },
            'analysis': {
                'market_trend': self.market_trend,
                'career_stage': self.career_stage,
                'last_album': self.last_album,
                'last_album_year': self.last_album_year,
                'confidence_score': self.confidence_score,
            },
            'meta': {
                'sources_scanned': self.sources_scanned,
                'scan_timestamp': self.scan_timestamp,
            },
        }


class WebArtistScanner:
    """
    Scanner web pour analyser les artistes depuis des sources fiables:
    - Spotify (via web scraping de la page artiste)
    - YouTube (chaîne officielle)
    - Instagram (profil public)
    - Wikipedia / Wikidata
    - Discogs (discographie)
    - Songkick / Bandsintown (concerts)
    - Google (recherche générale)
    - Sites de billetterie (Fnac, Ticketmaster)
    """
    
    # User agent pour simuler un navigateur
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # Venues connues avec capacité (pour estimation)
    KNOWN_VENUES = {
        'stade de france': 80000,
        'paris la défense arena': 40000,
        'accor arena': 20000,
        'accorhotels arena': 20000,
        'bercy': 20000,
        'zénith de paris': 6293,
        'zénith': 6000,
        'olympia': 1996,
        'bataclan': 1500,
        'élysée montmartre': 1500,
        'cigale': 1400,
        'trianon': 1000,
        'alhambra': 800,
        'new morning': 450,
        'café de la danse': 400,
        'trabendo': 700,
        'le divan du monde': 350,
        'pop up du label': 200,
        # Festivals
        'solidays': 200000,
        'rock en seine': 120000,
        'vieilles charrues': 280000,
        'francofolies': 150000,
        'eurockéennes': 130000,
        'main square festival': 100000,
        'lollapalooza paris': 100000,
        'garorock': 140000,
        'hellfest': 180000,
        'download festival': 90000,
        'peacock society': 30000,
        'we love green': 80000,
        'pitchfork music festival': 60000,
    }
    
    # Grille tarifaire par niveau
    FEE_TIERS = {
        'emerging': (1500, 5000),
        'developing': (5000, 15000),
        'established': (15000, 40000),
        'star': (40000, 100000),
        'superstar': (100000, 300000),
        'mega_star': (300000, 1000000),
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def scan_artist(self, artist_name: str, force_refresh: bool = False) -> WebArtistProfile:
        """
        Scanne toutes les sources fiables pour un artiste.
        Combine les données de la base de données ET du web pour plus de fiabilité.
        
        Args:
            artist_name: Nom de l'artiste à scanner
            force_refresh: Si True, scanne toujours le web même si l'artiste est dans la base
        """
        print(f"\n{'='*70}", flush=True)
        print(f"🔍 WEB ARTIST SCANNER - {artist_name.upper()}", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"   Force Refresh: {force_refresh}", flush=True)
        
        logger.info(f"🔍 Démarrage du scan web pour: {artist_name} (force_refresh={force_refresh})")
        
        profile = WebArtistProfile(name=artist_name)
        # Static catalog values have no dated collection evidence. Keep its helpers
        # archived for reference, but never seed a live artist scan from that catalog.

        # Scanner le web pour actualiser/compléter les données
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": self.USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=30)
            )
        
        try:
            # Lancer les scans en parallèle - Viberate en premier (source la plus fiable)
            print(f"\n   🌐 Lancement des scans parallèles...", flush=True)
            tasks = [
                self._scan_viberate(artist_name, profile),  # Priority: Real Spotify + social data
                self._scan_wikipedia(artist_name, profile),
                self._scan_spotify_web(artist_name, profile),
                self._scan_youtube(artist_name, profile),
                self._scan_discogs(artist_name, profile),
                self._scan_songkick(artist_name, profile),
                self._scan_bandsintown(artist_name, profile),
                self._scan_ticketmaster(artist_name, profile),
                self._scan_fnac_spectacles(artist_name, profile),
                self._scan_google(artist_name, profile),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Afficher les erreurs de scan
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_names = ['Viberate', 'Wikipedia', 'Spotify', 'YouTube', 'Discogs', 
                                  'Songkick', 'Bandsintown', 'Ticketmaster', 'Fnac', 'Google']
                    print(f"   ⚠️ {task_names[i]} error: {result}", flush=True)
            
            print(f"\n   📊 Sources scannées: {profile.sources_scanned}", flush=True)
            
            self._calculate_total_metrics(profile)
            self._estimate_fees(profile)

            self._analyze_market_trend(profile)
            self._calculate_confidence(profile)
            
            print(f"\n   ✅ SCAN TERMINÉ", flush=True)
            print(f"      Spotify: {profile.spotify_monthly_listeners:,}", flush=True)
            print(f"      YouTube: {profile.youtube_subscribers:,}", flush=True)
            print(f"      Instagram: {profile.instagram_followers:,}", flush=True)
            print(f"      TikTok: {profile.tiktok_followers:,}", flush=True)
            print(f"      Tier: {profile.market_tier}", flush=True)
            print(f"      Fee: {profile.estimated_fee_min:,.0f}€ - {profile.estimated_fee_max:,.0f}€", flush=True)
            print(f"{'='*70}\n", flush=True)
            
            logger.info(f"✅ Scan terminé pour {artist_name}: score={profile.popularity_score:.1f}, tier={profile.market_tier}, fee={profile.estimated_fee_min:,.0f}€-{profile.estimated_fee_max:,.0f}€")
            
        except Exception as e:
            print(f"\n   ❌ ERREUR SCAN: {e}", flush=True)
            import traceback
            print(f"   {traceback.format_exc()}", flush=True)
            logger.error(f"Erreur lors du scan de {artist_name}: {e}")
            
        return profile
    
    def _merge_with_known_data(self, profile: WebArtistProfile, base_data: dict, known_artist: KnownArtistData) -> WebArtistProfile:
        """
        Fusionne les données scannées avec les données de la base.
        Privilégie les données de la base pour les estimations financières (plus fiables),
        mais utilise les données web pour les métriques sociales (plus actuelles).
        """
        # Pour les métriques sociales: prendre les données web si cohérentes
        if profile.spotify_monthly_listeners > 0 and base_data['spotify'] > 0:
            ratio = profile.spotify_monthly_listeners / base_data['spotify']
            diff_percent = abs(profile.spotify_monthly_listeners - base_data['spotify']) / base_data['spotify'] * 100
            
            # Si la différence est > 100% (valeur doublée ou divisée par 2), c'est suspect
            # Probablement une erreur de scraping (mauvais artiste)
            if ratio > 2.0 or ratio < 0.5:
                logger.warning(f"⚠️ Spotify web ({profile.spotify_monthly_listeners:,}) trop différent de base ({base_data['spotify']:,}) - ratio {ratio:.1f}x - on garde la base")
                profile.spotify_monthly_listeners = base_data['spotify']
            elif diff_percent > 10:
                # Différence raisonnable (10-100%), on accepte la mise à jour
                logger.info(f"📊 Spotify mis à jour: {base_data['spotify']:,} → {profile.spotify_monthly_listeners:,} ({diff_percent:.0f}% diff)")
            else:
                # Différence négligeable (<10%), on garde la base
                profile.spotify_monthly_listeners = base_data['spotify']
        elif profile.spotify_monthly_listeners == 0:
            profile.spotify_monthly_listeners = base_data['spotify']
        
        if profile.youtube_subscribers > 0:
            if profile.youtube_subscribers > base_data['youtube'] * 0.9:
                logger.info(f"📊 YouTube mis à jour: {base_data['youtube']:,} → {profile.youtube_subscribers:,}")
            else:
                profile.youtube_subscribers = base_data['youtube']
        else:
            profile.youtube_subscribers = base_data['youtube']
        
        if profile.instagram_followers == 0:
            profile.instagram_followers = base_data['instagram']
        
        if profile.tiktok_followers == 0:
            profile.tiktok_followers = base_data['tiktok']
        
        # Pour les estimations financières: TOUJOURS privilégier la base de données (plus fiable)
        profile.estimated_fee_min = base_data['fee_min']
        profile.estimated_fee_max = base_data['fee_max']
        profile.market_tier = base_data['market_tier']
        
        # Recalculer le total des followers
        profile.total_followers = (
            profile.instagram_followers +
            profile.youtube_subscribers +
            profile.tiktok_followers
        )
        
        # Recalculer le score de popularité
        profile.popularity_score = self._calculate_popularity_score(profile)
        
        # Augmenter la confiance car on a les deux sources
        profile.confidence_score = min(98.0, profile.confidence_score + 10)
        
        return profile
    
    def _calculate_popularity_score(self, profile: WebArtistProfile) -> float:
        """
        Calcule un score de popularité 0-100 basé sur les métriques
        Utilise le nouveau système de scoring avec formules avancées
        """
        try:
            # Utiliser le nouveau scorer
            result = self._calculate_advanced_score(profile)
            return result.final_score
        except Exception as e:
            logger.warning(f"Erreur scoring avancé, fallback simple: {e}")
            # Fallback: méthode simple
            return self._calculate_simple_popularity_score(profile)
    
    def _calculate_simple_popularity_score(self, profile: WebArtistProfile) -> float:
        """Fallback: calcul simple du score"""
        score = 0.0
        
        # Spotify (poids 40%)
        if profile.spotify_monthly_listeners > 0:
            if profile.spotify_monthly_listeners >= 10000000:
                score += 40
            elif profile.spotify_monthly_listeners >= 5000000:
                score += 35
            elif profile.spotify_monthly_listeners >= 1000000:
                score += 30
            elif profile.spotify_monthly_listeners >= 500000:
                score += 25
            elif profile.spotify_monthly_listeners >= 100000:
                score += 20
            elif profile.spotify_monthly_listeners >= 50000:
                score += 15
            else:
                score += 10
        
        # YouTube (poids 25%)
        if profile.youtube_subscribers > 0:
            if profile.youtube_subscribers >= 5000000:
                score += 25
            elif profile.youtube_subscribers >= 1000000:
                score += 20
            elif profile.youtube_subscribers >= 500000:
                score += 15
            elif profile.youtube_subscribers >= 100000:
                score += 10
            else:
                score += 5
        
        # Instagram (poids 20%)
        if profile.instagram_followers > 0:
            if profile.instagram_followers >= 5000000:
                score += 20
            elif profile.instagram_followers >= 1000000:
                score += 15
            elif profile.instagram_followers >= 500000:
                score += 10
            else:
                score += 5
        
        # TikTok (poids 15%)
        if profile.tiktok_followers > 0:
            if profile.tiktok_followers >= 5000000:
                score += 15
            elif profile.tiktok_followers >= 1000000:
                score += 10
            else:
                score += 5
        
        return min(100.0, score)
    
    def _calculate_advanced_score(self, profile: WebArtistProfile):
        """
        Calcule le score avec le nouveau système avancé:
        - SpotifyScore (0-40): Popularity + Followers + Monthly Listeners
        - SocialScore (0-40): YouTube + Instagram + TikTok
        - LiveBonus (0-20): Concerts + Festivals + Venues
        - QualityFactor (0.60-1.10): Anti-vanity adjustment
        """
        scorer = ArtistScorer()
        
        # Essayer d'obtenir la popularité Spotify (via API si dispo)
        spotify_popularity = 0
        spotify_followers = 0
        
        # Chercher dans les métriques sociales
        for sm in profile.social_metrics:
            if sm.platform.lower() == 'spotify':
                spotify_followers = sm.followers
                break
        
        # Si on n'a pas les followers, estimer à partir des monthly listeners
        if spotify_followers == 0 and profile.spotify_monthly_listeners > 0:
            # Estimation: followers ≈ monthly_listeners / 20 (ratio typique)
            spotify_followers = profile.spotify_monthly_listeners // 20
        
        # Estimer la popularité Spotify à partir des monthly listeners
        if profile.spotify_monthly_listeners > 0:
            ml = profile.spotify_monthly_listeners
            if ml >= 50_000_000:
                spotify_popularity = 95
            elif ml >= 20_000_000:
                spotify_popularity = 85
            elif ml >= 10_000_000:
                spotify_popularity = 75
            elif ml >= 5_000_000:
                spotify_popularity = 65
            elif ml >= 1_000_000:
                spotify_popularity = 55
            elif ml >= 500_000:
                spotify_popularity = 45
            elif ml >= 100_000:
                spotify_popularity = 35
            elif ml >= 50_000:
                spotify_popularity = 25
            else:
                spotify_popularity = 15
        
        # Construire SpotifyData
        spotify_data = SpotifyData(
            popularity=spotify_popularity,
            followers=spotify_followers,
            monthly_listeners=profile.spotify_monthly_listeners,
            monthly_listeners_source="viberate" if profile.spotify_monthly_listeners > 0 else None
        )
        
        # Construire SocialData
        social_data = SocialData(
            youtube_subscribers=profile.youtube_subscribers,
            youtube_total_views=profile.youtube_total_views,
            instagram_followers=profile.instagram_followers,
            instagram_engagement_rate=None,  # Pas de données d'engagement
            tiktok_followers=profile.tiktok_followers,
            tiktok_total_views=None
        )
        
        # Construire LiveData à partir des concerts
        live_data = None
        if profile.upcoming_concerts or profile.past_concerts or profile.festivals_played:
            concerts_count = len(profile.upcoming_concerts) + len(profile.past_concerts)
            festivals_count = len(profile.festivals_played)
            
            # Compter les grandes salles (10K+) et moyennes (5K-10K)
            large_venues = 0
            medium_venues = 0
            
            for concert in profile.upcoming_concerts + profile.past_concerts:
                venue_lower = concert.venue.lower()
                for known_venue, capacity in self.KNOWN_VENUES.items():
                    if known_venue in venue_lower:
                        if capacity >= 10000:
                            large_venues += 1
                        elif capacity >= 5000:
                            medium_venues += 1
                        break
            
            live_data = LiveData(
                concerts_count=concerts_count,
                festivals_count=festivals_count,
                large_venues_10k_plus=large_venues,
                medium_venues_5k_10k=medium_venues
            )
        
        # Déterminer la tendance
        trend = None
        if profile.market_trend == "rising":
            trend = Trend.RISING
        elif profile.market_trend == "declining":
            trend = Trend.DECLINING
        else:
            trend = Trend.STABLE
        
        # Calculer le score
        result = scorer.calculate(
            spotify=spotify_data,
            social=social_data,
            live=live_data,
            trend=trend
        )
        
        return result
    
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Récupère le contenu d'une URL"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            logger.debug(f"Erreur fetch {url}: {e}")
        return None
    
    async def _scan_wikipedia(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Wikipedia pour les infos biographiques"""
        try:
            # Recherche Wikipedia FR
            search_url = f"https://fr.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(artist_name)}&format=json"
            
            async with self.session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('query', {}).get('search'):
                        page_title = data['query']['search'][0]['title']
                        
                        # Récupérer le contenu de la page
                        content_url = f"https://fr.wikipedia.org/w/api.php?action=query&titles={quote_plus(page_title)}&prop=extracts&exintro=1&format=json"
                        async with self.session.get(content_url) as content_resp:
                            if content_resp.status == 200:
                                content_data = await content_resp.json()
                                pages = content_data.get('query', {}).get('pages', {})
                                for page_id, page in pages.items():
                                    if page_id != '-1' and 'extract' in page:
                                        extract = page['extract']
                                        self._parse_wikipedia_content(extract, profile)
                                        profile.sources_scanned.append('Wikipedia FR')
                                        break
        except Exception as e:
            logger.debug(f"Wikipedia scan error: {e}")
    
    def _parse_wikipedia_content(self, content: str, profile: WebArtistProfile):
        """Parse le contenu Wikipedia"""
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # Extraire l'année de naissance
        birth_match = re.search(r'né[e]?\s+(?:le\s+)?(?:\d{1,2}\s+\w+\s+)?(\d{4})', text, re.IGNORECASE)
        if birth_match:
            profile.birth_year = int(birth_match.group(1))
        
        # Extraire le vrai nom
        name_match = re.search(r'(?:de son vrai nom|née?)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)+)', text)
        if name_match:
            profile.real_name = name_match.group(1)
        
        # Détecter le genre
        genres = {
            'rap': ['rappeur', 'rappeuse', 'hip-hop', 'trap', 'drill'],
            'pop': ['pop', 'variété', 'chanson française'],
            'electro': ['dj', 'producteur', 'électronique', 'house', 'techno'],
            'rock': ['rock', 'metal', 'punk'],
            'rnb': ['r&b', 'rnb', 'soul'],
            'reggae': ['reggae', 'dancehall'],
        }
        
        text_lower = text.lower()
        for genre, keywords in genres.items():
            if any(kw in text_lower for kw in keywords):
                profile.genre = genre.upper()
                break
        
        # Extraire le label
        label_match = re.search(r'(?:signé chez|label|maison de disques?)\s+([^,.]+)', text, re.IGNORECASE)
        if label_match:
            profile.record_label = label_match.group(1).strip()
    
    async def _scan_spotify_web(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Spotify via l'API officielle - PAS d'estimation des monthly listeners"""
        try:
            # Vérifier si l'API Spotify est disponible
            if not spotify_client.is_available():
                logger.warning("Spotify API not configured - skipping Spotify scan")
                return
            
            # Rechercher l'artiste via l'API Spotify
            artist_data = spotify_client.search_artist(artist_name)
            
            if artist_data:
                # IMPORTANT: Ne pas utiliser les estimations bidon !
                # Les monthly listeners viendront de Viberate ou du scraping Spotify direct
                monthly_listeners = artist_data.get('monthly_listeners', 0)
                source = artist_data.get('monthly_listeners_source', 'estimated')
                
                # Si c'est une estimation, ne PAS l'utiliser - laisser à 0
                if source == 'estimated':
                    logger.info(f"⚠️ Spotify API: estimation ignorée ({monthly_listeners:,}) - Viberate/scraping utilisé à la place")
                    monthly_listeners = 0
                    source_label = '⏳ pending'
                else:
                    # C'est une vraie valeur (viberate ou autre source fiable)
                    profile.spotify_monthly_listeners = monthly_listeners
                    source_label = '✅ REAL'
                
                # Récupérer les social stats si disponibles
                social_stats = artist_data.get('social_stats', {})
                if social_stats:
                    if social_stats.get('youtube_subscribers'):
                        profile.youtube_subscribers = social_stats['youtube_subscribers']
                    if social_stats.get('instagram_followers'):
                        profile.instagram_followers = social_stats['instagram_followers']
                    if social_stats.get('tiktok_followers'):
                        profile.tiktok_followers = social_stats['tiktok_followers']
                
                # Mettre à jour le genre si disponible
                if artist_data['genres'] and len(artist_data['genres']) > 0:
                    # Prendre le premier genre et le formater
                    main_genre = artist_data['genres'][0].upper()
                    
                    # Mapper les genres Spotify vers nos catégories
                    genre_map = {
                        'RAP': 'RAP',
                        'HIP HOP': 'RAP',
                        'FRENCH HIP HOP': 'RAP',
                        'POP': 'POP',
                        'FRENCH POP': 'POP',
                        'ELECTRO': 'ELECTRO',
                        'ELECTRONIC': 'ELECTRO',
                        'ROCK': 'ROCK',
                        'FRENCH ROCK': 'ROCK',
                        'R&B': 'R&B',
                        'RNB': 'R&B',
                        'SOUL': 'R&B',
                        'INDIE': 'INDIE',
                        'ALTERNATIVE': 'INDIE',
                        'REGGAE': 'REGGAE',
                        'DANCEHALL': 'REGGAE',
                        'AFROBEAT': 'AFRO',
                        'AFROPOP': 'AFRO',
                    }
                    
                    # Essayer de trouver une correspondance
                    matched_genre = None
                    for spotify_genre_key, our_genre in genre_map.items():
                        if spotify_genre_key in main_genre.upper():
                            matched_genre = our_genre
                            break
                    
                    if matched_genre:
                        profile.genre = matched_genre
                    else:
                        # Garder le genre Spotify original formaté
                        profile.genre = main_genre.replace(' ', '_').upper()
                    
                    # Ajouter tous les genres comme sub_genres
                    profile.sub_genres = [g.title() for g in artist_data['genres'][:5]]
                
                # Récupérer l'image de l'artiste depuis Spotify
                if artist_data.get('image_url'):
                    profile.image_url = artist_data['image_url']
                    logger.info(f"🖼️ Image from Spotify: {profile.image_url[:60]}...")
                
                # Ajouter label et management si disponibles (via enrichissement)
                if 'label' in artist_data:
                    profile.record_label = artist_data['label']
                    logger.info(f"📀 Label from enrichment: {profile.record_label}")
                
                if 'management' in artist_data:
                    profile.booking_agency = artist_data['management']
                    logger.info(f"👔 Management from enrichment: {profile.booking_agency}")
                
                # Ajouter les métriques sociales (sans monthly_listeners si estimé)
                profile.social_metrics.append(SocialMetrics(
                    platform='Spotify',
                    followers=artist_data['followers'],
                    monthly_listeners=monthly_listeners if monthly_listeners > 0 else None,
                    url=artist_data['spotify_url']
                ))
                
                # Mettre à jour spotify_followers dans le profil
                profile.spotify_followers = artist_data['followers']
                
                # Utiliser la popularité Spotify (0-100) pour améliorer notre score
                spotify_popularity = artist_data['popularity']
                profile.popularity_score = max(profile.popularity_score, spotify_popularity)
                
                profile.sources_scanned.append(f'Spotify API (pop:{spotify_popularity}, followers:{artist_data["followers"]:,})')
                
                # Log différent selon si on a les vrais listeners ou pas
                if monthly_listeners > 0:
                    logger.info(f"✅ Spotify API: {artist_data['name']} - {artist_data['followers']:,} followers, {monthly_listeners:,} listeners (REAL), genre: {profile.genre}, popularity: {spotify_popularity}")
                else:
                    logger.info(f"✅ Spotify API: {artist_data['name']} - {artist_data['followers']:,} followers, genre: {profile.genre}, popularity: {spotify_popularity} (listeners via Viberate)")
                
        except Exception as e:
            logger.error(f"Spotify API error for {artist_name}: {e}")
    
    async def _scan_viberate(self, artist_name: str, profile: WebArtistProfile):
        """
        Scanne Viberate.com pour les vraies données Spotify et réseaux sociaux.
        Utilise le JSON __NEXT_DATA__ intégré dans la page (pas de JS nécessaire).
        URL: https://www.viberate.com/artist/{artist_name}/
        """
        import json
        import unicodedata
        
        try:
            # Normaliser le nom pour l'URL
            # 1. Convertir en minuscules
            url_name = artist_name.lower().strip()
            
            # 2. Supprimer les accents (é→e, à→a, etc.)
            url_name = unicodedata.normalize('NFD', url_name)
            url_name = ''.join(c for c in url_name if unicodedata.category(c) != 'Mn')
            
            # 3. Remplacer espaces et caractères spéciaux par des tirets
            url_name = url_name.replace(' ', '-').replace("'", "").replace(".", "").replace(",", "")
            url_name = url_name.replace("--", "-").strip("-")
            
            viberate_url = f"https://www.viberate.com/artist/{url_name}/"
            
            # DEBUG: Afficher l'URL construite
            logger.info(f"")
            logger.info(f"{'='*60}")
            logger.info(f"🎵 VIBERATE SCAN - {artist_name.upper()}")
            logger.info(f"{'='*60}")
            logger.info(f"📍 URL: {viberate_url}")
            logger.debug(f"   url_name transformé: '{artist_name}' → '{url_name}'")
            
            html = await self._fetch_url(viberate_url)
            
            if not html:
                logger.warning(f"❌ VIBERATE: Pas de réponse HTML pour {artist_name}")
                return
            
            if 'Page not found' in html or '404' in html:
                logger.warning(f"❌ VIBERATE: Page non trouvée pour {artist_name}")
                return
            
            logger.info(f"✅ VIBERATE: Page chargée ({len(html)} caractères)")
            
            viberate_data_found = False
            spotify_artist_id = None
            
            # === PARSER LE JSON __NEXT_DATA__ ===
            # Viberate utilise Next.js, les données sont dans un script JSON
            logger.info(f"")
            logger.info(f"🔍 Extraction du JSON __NEXT_DATA__...")
            
            next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            
            if next_data_match:
                try:
                    json_str = next_data_match.group(1)
                    next_data = json.loads(json_str)
                    artist_data = next_data.get('props', {}).get('pageProps', {}).get('data', {})
                    
                    if artist_data:
                        logger.info(f"   ✅ JSON trouvé! Artiste: {artist_data.get('name', 'N/A')}")
                        viberate_data_found = True
                        
                        # === RANGS ===
                        overall_rank = artist_data.get('rank', 0)
                        rank_categories = artist_data.get('rank_categories', {}).get('current', {})
                        country_rank = rank_categories.get('country', 0)
                        genre_rank = rank_categories.get('genre', 0)
                        
                        if overall_rank > 0:
                            logger.info(f"   📊 RANG GLOBAL: #{overall_rank:,}")
                        if country_rank > 0:
                            country_info = artist_data.get('country', {})
                            country_name = country_info.get('name', country_info.get('code', 'N/A'))
                            logger.info(f"   🏳️ RANG {country_name.upper()}: #{country_rank}")
                        if genre_rank > 0:
                            genre_info = artist_data.get('genre', {})
                            genre_name = genre_info.get('name', 'N/A')
                            logger.info(f"   🎶 RANG {genre_name.upper()}: #{genre_rank}")
                        
                        # === CHANNEL RANKS (Spotify, YouTube, etc.) ===
                        channel_ranks = artist_data.get('channel_ranks', {})
                        
                        spotify_ranks = channel_ranks.get('spotify', {}).get('current', {})
                        if spotify_ranks:
                            sp_overall = spotify_ranks.get('overall', 0)
                            sp_country = spotify_ranks.get('country', 0)
                            if sp_overall > 0:
                                logger.info(f"   🎧 SPOTIFY RANK: #{sp_overall:,} (pays: #{sp_country})")
                        
                        youtube_ranks = channel_ranks.get('youtube', {}).get('current', {})
                        if youtube_ranks:
                            yt_overall = youtube_ranks.get('overall', 0)
                            yt_country = youtube_ranks.get('country', 0)
                            if yt_overall > 0:
                                logger.info(f"   🎬 YOUTUBE RANK: #{yt_overall:,} (pays: #{yt_country})")
                        
                        social_ranks = channel_ranks.get('social', {}).get('current', {})
                        if social_ranks:
                            social_overall = social_ranks.get('overall', 0)
                            if social_overall > 0:
                                logger.info(f"   📱 SOCIAL RANK: #{social_overall:,}")
                        
                        # === SOCIAL LINKS - EXTRAIRE LES IDs ===
                        logger.info(f"")
                        logger.info(f"🔗 Liens sociaux trouvés:")
                        social_links = artist_data.get('social_links', [])
                        
                        for link in social_links:
                            channel = link.get('channel', '')
                            url = link.get('link', '')
                            
                            if channel == 'spotify' and url:
                                # Extraire l'ID Spotify: https://open.spotify.com/artist/3CnCGFxXbOA8bAK54jR8js
                                sp_match = re.search(r'/artist/([a-zA-Z0-9]+)', url)
                                if sp_match:
                                    spotify_artist_id = sp_match.group(1)
                                    logger.info(f"   🎧 SPOTIFY: {url}")
                                    logger.info(f"      → Artist ID: {spotify_artist_id}")
                            
                            elif channel == 'youtube' and url:
                                logger.info(f"   🎬 YOUTUBE: {url}")
                            
                            elif channel == 'instagram' and url:
                                logger.info(f"   📸 INSTAGRAM: {url}")
                            
                            elif channel == 'tiktok' and url:
                                logger.info(f"   🎵 TIKTOK: {url}")
                            
                            elif channel == 'twitter' and url:
                                logger.info(f"   🐦 TWITTER: {url}")
                            
                            elif channel == 'facebook' and url:
                                logger.info(f"   📘 FACEBOOK: {url}")
                            
                            elif channel == 'deezer' and url:
                                logger.info(f"   🎶 DEEZER: {url}")
                        
                        # === GENRE ET PAYS ===
                        country_info = artist_data.get('country', {})
                        if country_info:
                            country_name = country_info.get('name', country_info.get('code', ''))
                            if country_name:
                                profile.country = country_name
                                if profile.nationality == "France":
                                    profile.nationality = country_name
                        
                        genre_info = artist_data.get('genre', {})
                        subgenres = artist_data.get('subgenres', [])
                        if genre_info or subgenres:
                            genres = []
                            if genre_info and genre_info.get('name'):
                                genres.append(genre_info.get('name'))
                            for sg in subgenres:
                                if sg.get('name'):
                                    genres.append(sg.get('name'))
                            if genres:
                                profile.genres = genres
                                if len(profile.sub_genres) == 0:
                                    profile.sub_genres = genres
                                logger.info(f"   🎼 GENRES: {', '.join(genres)}")
                    else:
                        logger.warning(f"   ⚠️ JSON trouvé mais pas de données artiste")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"   ⚠️ Erreur parsing JSON: {e}")
            else:
                logger.warning(f"   ⚠️ Script __NEXT_DATA__ non trouvé")
            
            # === SCRAPING SPOTIFY POUR LES VRAIS MONTHLY LISTENERS ===
            # Toujours essayer le scraping Spotify si on a l'ID (priorité sur Viberate)
            if spotify_artist_id and PLAYWRIGHT_AVAILABLE:
                logger.info(f"")
                logger.info(f"🎧 Scraping Spotify pour les VRAIS monthly listeners...")
                logger.info(f"   Artist ID: {spotify_artist_id}")
                
                # Sauvegarder la valeur Viberate pour comparaison
                viberate_listeners = profile.spotify_monthly_listeners
                
                # Scraper la page Spotify
                await self._fetch_spotify_monthly_listeners(spotify_artist_id, profile)
                
                # Log la différence si Viberate avait une valeur
                if viberate_listeners > 0 and profile.spotify_monthly_listeners != viberate_listeners:
                    logger.info(f"   📊 Comparaison: Viberate={viberate_listeners:,} vs Spotify={profile.spotify_monthly_listeners:,}")
            elif spotify_artist_id and not PLAYWRIGHT_AVAILABLE:
                logger.warning(f"   ⚠️ Playwright non disponible - impossible de scraper Spotify")
            
            # === RÉSUMÉ DEBUG ===
            logger.info(f"")
            logger.info(f"{'='*60}")
            logger.info(f"📊 RÉSUMÉ VIBERATE - {artist_name.upper()}")
            logger.info(f"{'='*60}")
            if spotify_artist_id:
                logger.info(f"   🆔 Spotify ID: {spotify_artist_id}")
            if profile.spotify_monthly_listeners > 0:
                if profile.spotify_monthly_listeners >= 1_000_000:
                    formatted = f"{profile.spotify_monthly_listeners/1_000_000:.1f}M"
                elif profile.spotify_monthly_listeners >= 1_000:
                    formatted = f"{profile.spotify_monthly_listeners/1_000:.1f}K"
                else:
                    formatted = str(profile.spotify_monthly_listeners)
                logger.info(f"   🎧 Spotify Monthly: {profile.spotify_monthly_listeners:,} ({formatted})")
                
                # Estimer les followers si pas encore remplis (ratio typique: followers ≈ monthly_listeners / 20)
                if profile.spotify_followers == 0:
                    profile.spotify_followers = profile.spotify_monthly_listeners // 20
                    logger.info(f"   🎧 Spotify Followers (estimé): {profile.spotify_followers:,}")
            if profile.spotify_followers > 0 and profile.spotify_monthly_listeners > 0 and profile.spotify_followers != profile.spotify_monthly_listeners // 20:
                logger.info(f"   🎧 Spotify Followers: {profile.spotify_followers:,}")
            if profile.youtube_subscribers > 0:
                logger.info(f"   🎬 YouTube: {profile.youtube_subscribers:,}")
            if profile.tiktok_followers > 0:
                logger.info(f"   🎵 TikTok: {profile.tiktok_followers:,}")
            if profile.instagram_followers > 0:
                logger.info(f"   📸 Instagram: {profile.instagram_followers:,}")
            if profile.country:
                logger.info(f"   🌍 Pays: {profile.country}")
            if profile.genres:
                logger.info(f"   🎼 Genres: {', '.join(profile.genres)}")
            logger.info(f"{'='*60}")
            logger.info(f"")
            
            if viberate_data_found:
                profile.sources_scanned.append('Viberate')
                
        except Exception as e:
            logger.error(f"❌ VIBERATE ERROR for {artist_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _fetch_spotify_monthly_listeners(self, spotify_artist_id: str, profile: WebArtistProfile):
        """
        Récupère les monthly listeners depuis la page artiste Spotify.
        Spotify est une SPA qui nécessite JavaScript pour afficher les données.
        On utilise Playwright pour exécuter le JS et récupérer le HTML rendu.
        URL format: https://open.spotify.com/intl-fr/artist/{ARTIST_ID}
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("   ⚠️ Playwright non disponible - skip Spotify scraping")
            return
            
        try:
            spotify_url = f"https://open.spotify.com/intl-fr/artist/{spotify_artist_id}"
            logger.info(f"   🎭 Playwright: {spotify_url}")
            
            html = None
            async with async_playwright() as p:
                # Lancer Chromium en mode headless
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='fr-FR'
                )
                page = await context.new_page()
                
                try:
                    # Aller sur la page avec timeout de 15 secondes
                    await page.goto(spotify_url, wait_until='networkidle', timeout=15000)
                    
                    # Attendre que le contenu soit chargé (chercher le texte "auditeurs")
                    try:
                        await page.wait_for_selector('text=auditeurs', timeout=5000)
                    except:
                        # Essayer en anglais
                        try:
                            await page.wait_for_selector('text=listeners', timeout=3000)
                        except:
                            pass
                    
                    # Récupérer le HTML rendu
                    html = await page.content()
                    logger.info(f"   📄 Page Spotify rendue ({len(html)} caractères)")
                    
                finally:
                    await browser.close()
            
            if not html:
                logger.warning(f"   ⚠️ Pas de contenu Spotify")
                return
            
            # Nettoyer les espaces insécables
            html_clean = html.replace('\u202f', ' ').replace('\xa0', ' ').replace('&nbsp;', ' ')
            
            patterns = [
                # Format français (ex: "3 274 825 auditeurs mensuels")
                r'([\d\s]+)\s*auditeurs?\s*mensuels?',
                # Format anglais (ex: "3,274,825 monthly listeners")
                r'([\d,]+)\s*monthly\s*listeners',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_clean, re.IGNORECASE)
                if match:
                    raw_value = match.group(1)
                    logger.info(f"   🔍 Pattern trouvé: '{raw_value}'")
                    
                    # Nettoyer
                    clean_value = raw_value.replace(' ', '').replace(',', '').replace('.', '')
                    
                    try:
                        listeners = int(clean_value)
                        if listeners > 1000:
                            profile.spotify_monthly_listeners = listeners
                            if listeners >= 1_000_000:
                                formatted = f"{listeners/1_000_000:.1f}M"
                            elif listeners >= 1_000:
                                formatted = f"{listeners/1_000:.1f}K"
                            else:
                                formatted = str(listeners)
                            logger.info(f"   ✅ SPOTIFY MONTHLY: {listeners:,} ({formatted})")
                            return
                    except ValueError as e:
                        logger.warning(f"   ⚠️ Erreur parsing '{clean_value}': {e}")
                        continue
            
            logger.info(f"   ⚠️ Monthly listeners non trouvés dans la page Spotify")
            
        except Exception as e:
            logger.warning(f"   ⚠️ Erreur Playwright Spotify: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    async def _scan_youtube(self, artist_name: str, profile: WebArtistProfile):
        """Scanne YouTube pour les stats de la chaîne"""
        try:
            search_url = f"https://www.youtube.com/results?search_query={quote_plus(artist_name + ' official')}"
            html = await self._fetch_url(search_url)
            
            if html:
                # Chercher le nombre d'abonnés dans le JSON de la page
                subs_match = re.search(r'"subscriberCountText":\s*\{"simpleText":\s*"([\d,\.KMBkmb]+)', html)
                if subs_match:
                    subs_str = subs_match.group(1)
                    profile.youtube_subscribers = self._parse_number(subs_str)
                    profile.sources_scanned.append('YouTube')
                    
                    profile.social_metrics.append(SocialMetrics(
                        platform='YouTube',
                        followers=profile.youtube_subscribers,
                    ))
        except Exception as e:
            logger.debug(f"YouTube scan error: {e}")
    
    async def _scan_discogs(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Discogs pour la discographie"""
        try:
            search_url = f"https://www.discogs.com/search/?q={quote_plus(artist_name)}&type=artist"
            html = await self._fetch_url(search_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Chercher le dernier album
                releases = soup.select('.card-release-title')
                if releases:
                    profile.last_album = releases[0].get_text(strip=True)
                    profile.sources_scanned.append('Discogs')
                    
                    # Chercher l'année
                    year_match = re.search(r'\((\d{4})\)', str(releases[0].parent))
                    if year_match:
                        profile.last_album_year = int(year_match.group(1))
        except Exception as e:
            logger.debug(f"Discogs scan error: {e}")
    
    async def _scan_songkick(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Songkick pour les concerts"""
        try:
            search_url = f"https://www.songkick.com/search?query={quote_plus(artist_name)}&type=artists"
            html = await self._fetch_url(search_url)
            
            if html and 'No results found' not in html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Chercher les événements
                events = soup.select('.event-listing')[:10]
                for event in events:
                    venue_el = event.select_one('.venue-name')
                    date_el = event.select_one('.date')
                    city_el = event.select_one('.location')
                    
                    if venue_el and date_el:
                        concert = ConcertInfo(
                            name=f"Concert @ {venue_el.get_text(strip=True)}",
                            date=date_el.get_text(strip=True),
                            venue=venue_el.get_text(strip=True),
                            city=city_el.get_text(strip=True) if city_el else "",
                            source='Songkick'
                        )
                        profile.upcoming_concerts.append(concert)
                
                if events:
                    profile.sources_scanned.append('Songkick')
        except Exception as e:
            logger.debug(f"Songkick scan error: {e}")
    
    async def _scan_bandsintown(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Bandsintown pour les concerts"""
        try:
            url = f"https://www.bandsintown.com/{quote_plus(artist_name.replace(' ', '-'))}"
            html = await self._fetch_url(url)
            
            if html and 'Oops! We couldn' not in html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Compter les dates de tournée
                tour_dates = soup.select('[data-testid="event-list-item"]')
                
                for event in tour_dates[:10]:
                    venue_el = event.select_one('[data-testid="venue-name"]')
                    date_el = event.select_one('[data-testid="event-date"]')
                    location_el = event.select_one('[data-testid="event-location"]')
                    
                    if venue_el:
                        concert = ConcertInfo(
                            name=f"Concert @ {venue_el.get_text(strip=True)}",
                            date=date_el.get_text(strip=True) if date_el else "",
                            venue=venue_el.get_text(strip=True),
                            city=location_el.get_text(strip=True) if location_el else "",
                            source='Bandsintown'
                        )
                        
                        # Éviter les doublons
                        if not any(c.venue == concert.venue for c in profile.upcoming_concerts):
                            profile.upcoming_concerts.append(concert)
                
                if tour_dates:
                    profile.sources_scanned.append('Bandsintown')
        except Exception as e:
            logger.debug(f"Bandsintown scan error: {e}")
    
    async def _scan_ticketmaster(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Ticketmaster pour les prix des billets"""
        try:
            url = f"https://www.ticketmaster.fr/search?query={quote_plus(artist_name)}"
            html = await self._fetch_url(url)
            
            if html:
                # Chercher les prix
                price_matches = re.findall(r'(\d+(?:,\d{2})?)\s*€', html)
                if price_matches:
                    prices = [float(p.replace(',', '.')) for p in price_matches]
                    prices = [p for p in prices if 15 <= p <= 500]  # Filtrer les prix réalistes
                    
                    if prices:
                        for concert in profile.upcoming_concerts:
                            if not concert.ticket_price_min:
                                concert.ticket_price_min = min(prices)
                                concert.ticket_price_max = max(prices)
                        
                        profile.sources_scanned.append('Ticketmaster')
        except Exception as e:
            logger.debug(f"Ticketmaster scan error: {e}")
    
    async def _scan_fnac_spectacles(self, artist_name: str, profile: WebArtistProfile):
        """Scanne Fnac Spectacles"""
        try:
            url = f"https://www.fnacspectacles.com/recherche/{quote_plus(artist_name)}.htm"
            html = await self._fetch_url(url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Chercher les événements
                events = soup.select('.event-item, .show-card')
                for event in events[:5]:
                    venue = event.select_one('.venue, .location')
                    date = event.select_one('.date')
                    price = event.select_one('.price')
                    
                    if venue:
                        concert = ConcertInfo(
                            name=f"Concert @ {venue.get_text(strip=True)}",
                            date=date.get_text(strip=True) if date else "",
                            venue=venue.get_text(strip=True),
                            city="",
                            source='Fnac Spectacles'
                        )
                        
                        if price:
                            price_match = re.search(r'(\d+)', price.get_text())
                            if price_match:
                                concert.ticket_price_min = float(price_match.group(1))
                        
                        if not any(c.venue == concert.venue for c in profile.upcoming_concerts):
                            profile.upcoming_concerts.append(concert)
                
                if events:
                    profile.sources_scanned.append('Fnac Spectacles')
        except Exception as e:
            logger.debug(f"Fnac scan error: {e}")
    
    async def _scan_google(self, artist_name: str, profile: WebArtistProfile):
        """Recherche Google pour infos supplémentaires"""
        try:
            # Rechercher le cachet / booking
            queries = [
                f'"{artist_name}" booking contact email',
                f'"{artist_name}" management tournée',
                f'"{artist_name}" cachet prix concert',
            ]
            
            for query in queries:
                url = f"https://www.google.com/search?q={quote_plus(query)}"
                html = await self._fetch_url(url)
                
                if html:
                    # Chercher les emails de booking
                    email_match = re.search(
                        r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
                        html
                    )
                    if email_match and not profile.booking_email:
                        email = email_match.group(1)
                        if 'booking' in email.lower() or 'contact' in email.lower():
                            profile.booking_email = email
                    
                    # Chercher le management
                    mgmt_match = re.search(
                        r'(?:management|manager|tourneur)[:\s]+([^<,\n]+)',
                        html, re.IGNORECASE
                    )
                    if mgmt_match and not profile.management:
                        profile.management = mgmt_match.group(1).strip()[:50]
            
            profile.sources_scanned.append('Google Search')
        except Exception as e:
            logger.debug(f"Google scan error: {e}")
    
    def _create_profile_from_known_artist(self, known: KnownArtistData) -> WebArtistProfile:
        """
        Crée un profil complet à partir des données d'un artiste connu.
        Utilise les données fiables de notre base de données.
        """
        profile = WebArtistProfile(
            name=known.name,
            real_name=known.real_name,
            genre=known.genre,
            nationality="France",
            
            # Métriques sociales
            spotify_monthly_listeners=known.spotify_monthly_listeners,
            youtube_subscribers=known.youtube_subscribers,
            instagram_followers=known.instagram_followers,
            tiktok_followers=known.tiktok_followers,
            total_followers=(
                known.spotify_monthly_listeners +
                known.youtube_subscribers +
                known.instagram_followers +
                known.tiktok_followers
            ),
            
            # Estimation financière
            estimated_fee_min=known.fee_min,
            estimated_fee_max=known.fee_max,
            market_tier=known.market_tier,
            
            # Business
            record_label=known.record_label,
            management=known.management,
            booking_agency=known.booking_agency,
            
            # Analyse
            market_trend='stable',
            career_stage='active',
        )
        
        # Calculer le score de popularité basé sur Spotify
        if known.spotify_monthly_listeners >= 20000000:
            profile.popularity_score = 100
        elif known.spotify_monthly_listeners >= 10000000:
            profile.popularity_score = 90
        elif known.spotify_monthly_listeners >= 5000000:
            profile.popularity_score = 80
        elif known.spotify_monthly_listeners >= 2000000:
            profile.popularity_score = 70
        elif known.spotify_monthly_listeners >= 1000000:
            profile.popularity_score = 60
        elif known.spotify_monthly_listeners >= 500000:
            profile.popularity_score = 50
        elif known.spotify_monthly_listeners >= 100000:
            profile.popularity_score = 40
        else:
            profile.popularity_score = 30
        
        # Ajouter les métriques sociales détaillées
        if known.spotify_monthly_listeners > 0:
            profile.social_metrics.append(SocialMetrics(
                platform='Spotify',
                monthly_listeners=known.spotify_monthly_listeners,
                url=f'https://open.spotify.com/search/{known.name}'
            ))
        
        if known.youtube_subscribers > 0:
            profile.social_metrics.append(SocialMetrics(
                platform='YouTube',
                followers=known.youtube_subscribers,
                url=f'https://youtube.com/results?search_query={known.name}'
            ))
        
        if known.instagram_followers > 0:
            profile.social_metrics.append(SocialMetrics(
                platform='Instagram',
                followers=known.instagram_followers,
            ))
        
        if known.tiktok_followers > 0:
            profile.social_metrics.append(SocialMetrics(
                platform='TikTok',
                followers=known.tiktok_followers,
            ))
        
        # Déterminer la tendance du marché
        if known.market_tier in ['superstar', 'mega_star']:
            profile.market_trend = 'stable'  # Les superstars sont stables
        elif known.spotify_monthly_listeners >= 3000000:
            profile.market_trend = 'rising'
        else:
            profile.market_trend = 'stable'
        
        return profile
    
    def _parse_number(self, text: str) -> int:
        """Parse un nombre avec K, M, B suffixes"""
        text = text.strip().upper().replace(' ', '').replace(',', '.')
        
        multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
        
        for suffix, mult in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, ''))
                    return int(num * mult)
                except ValueError:
                    pass
        
        try:
            return int(float(text.replace('.', '')))
        except ValueError:
            return 0
    
    def _calculate_total_metrics(self, profile: WebArtistProfile):
        """Calcule les métriques totales"""
        profile.total_followers = (
            profile.spotify_monthly_listeners +
            profile.youtube_subscribers +
            profile.instagram_followers +
            profile.tiktok_followers
        )
    
    def _estimate_fees(self, profile: WebArtistProfile):
        """
        Estime les cachets basés sur le nouveau système de scoring avancé.
        
        Formule:
        - SpotifyScore (0-40) + SocialScore (0-40) + LiveBonus (0-20)
        - Ajustement QualityFactor (0.60-1.10)
        - 6 tiers de tarification
        """
        try:
            result = self._calculate_advanced_score(profile)
            
            # Mettre à jour le profil avec les résultats
            profile.popularity_score = result.final_score
            profile.estimated_fee_min = result.fee_min
            profile.estimated_fee_max = result.fee_max
            
            # Mapper les tiers
            tier_mapping = {
                1: 'emerging',
                2: 'developing',
                3: 'established',
                4: 'star',
                5: 'superstar',
                6: 'mega_star',
            }
            profile.market_tier = tier_mapping.get(result.tier.value, 'emerging')
            
            # Mettre à jour la tendance
            profile.market_trend = result.trend.value
            
            logger.info(
                f"📊 Score avancé pour {profile.name}: "
                f"score={result.final_score:.1f}, "
                f"spotify={result.spotify_score:.1f}/40, "
                f"social={result.social_score:.1f}/40, "
                f"live={result.live_bonus_effective:.1f}/20, "
                f"QF={result.quality_factor:.2f}, "
                f"tier={profile.market_tier}, "
                f"fee={result.fee_min:,}€-{result.fee_max:,}€, "
                f"confidence={result.confidence:.0f}%"
            )
            
        except Exception as e:
            logger.warning(f"Erreur scoring avancé, utilisation fallback: {e}")
            self._estimate_fees_fallback(profile)
    
    def _estimate_fees_fallback(self, profile: WebArtistProfile):
        """Méthode de fallback pour l'estimation des cachets"""
        # Score basé sur les métriques
        score = 0
        has_data = False  # Vérifier si on a des données fiables
        
        # Spotify (très important)
        if profile.spotify_monthly_listeners > 0:
            has_data = True
            if profile.spotify_monthly_listeners >= 10000000:
                score += 40
            elif profile.spotify_monthly_listeners >= 5000000:
                score += 35
            elif profile.spotify_monthly_listeners >= 1000000:
                score += 28
            elif profile.spotify_monthly_listeners >= 500000:
                score += 22
            elif profile.spotify_monthly_listeners >= 100000:
                score += 15
            elif profile.spotify_monthly_listeners >= 50000:
                score += 10
            elif profile.spotify_monthly_listeners >= 10000:
                score += 5
            else:
                score += 2
        
        # YouTube
        if profile.youtube_subscribers > 0:
            has_data = True
            if profile.youtube_subscribers >= 5000000:
                score += 20
            elif profile.youtube_subscribers >= 1000000:
                score += 15
            elif profile.youtube_subscribers >= 500000:
                score += 10
            elif profile.youtube_subscribers >= 100000:
                score += 5
            else:
                score += 2
        
        # Nombre de concerts programmés (indicateur de demande)
        concerts_count = len(profile.upcoming_concerts)
        if concerts_count > 0:
            has_data = True
            if concerts_count >= 20:
                score += 15
            elif concerts_count >= 10:
                score += 10
            elif concerts_count >= 5:
                score += 5
            else:
                score += 2
        
        # Festivals (indicateur de notoriété)
        festivals = [c for c in profile.upcoming_concerts 
                    if any(f in c.venue.lower() for f in ['festival', 'solidays', 'rock en seine', 'vieilles charrues'])]
        score += len(festivals) * 5
        
        # Grandes salles
        for concert in profile.upcoming_concerts:
            venue_lower = concert.venue.lower()
            for known_venue, capacity in self.KNOWN_VENUES.items():
                if known_venue in venue_lower:
                    if capacity >= 10000:
                        score += 10
                    elif capacity >= 5000:
                        score += 5
                    break
        
        # Si pas de données fiables, être très conservateur
        if not has_data:
            profile.market_tier = 'emerging'
            profile.estimated_fee_min = 1000
            profile.estimated_fee_max = 3000
            profile.popularity_score = 5
            logger.warning(f"Pas de données fiables pour {profile.name}, estimation très conservatrice")
            return
        
        # Définir le tier avec prudence
        profile.popularity_score = min(100, score)
        
        if score >= 70:
            profile.market_tier = 'superstar'
            profile.estimated_fee_min, profile.estimated_fee_max = self.FEE_TIERS['superstar']
        elif score >= 55:
            profile.market_tier = 'star'
            profile.estimated_fee_min, profile.estimated_fee_max = self.FEE_TIERS['star']
        elif score >= 40:
            profile.market_tier = 'established'
            profile.estimated_fee_min, profile.estimated_fee_max = self.FEE_TIERS['established']
        elif score >= 25:
            profile.market_tier = 'developing'
            profile.estimated_fee_min, profile.estimated_fee_max = self.FEE_TIERS['developing']
        elif score >= 10:
            profile.market_tier = 'emerging'
            profile.estimated_fee_min, profile.estimated_fee_max = self.FEE_TIERS['emerging']
        else:
            # Score très faible = artiste local/débutant
            profile.market_tier = 'emerging'
            profile.estimated_fee_min = 800
            profile.estimated_fee_max = 2500
    
    def _analyze_market_trend(self, profile: WebArtistProfile):
        """Analyse la tendance du marché pour l'artiste"""
        # Basé sur l'activité récente
        if len(profile.upcoming_concerts) >= 10:
            profile.market_trend = 'rising'
        elif len(profile.upcoming_concerts) >= 3:
            profile.market_trend = 'stable'
        else:
            profile.market_trend = 'declining' if profile.spotify_monthly_listeners < 50000 else 'stable'
        
        # Album récent = en hausse
        if profile.last_album_year and profile.last_album_year >= datetime.now().year - 1:
            profile.market_trend = 'rising'
    
    def _calculate_confidence(self, profile: WebArtistProfile):
        """Calcule le score de confiance dans les données"""
        score = 0
        
        # Sources
        score += len(profile.sources_scanned) * 10
        
        # Données complètes
        if profile.spotify_monthly_listeners > 0:
            score += 15
        if profile.youtube_subscribers > 0:
            score += 10
        if len(profile.upcoming_concerts) > 0:
            score += 15
        if profile.record_label:
            score += 5
        if profile.booking_email:
            score += 10
        if profile.genre != 'Unknown':
            score += 5
        
        profile.confidence_score = min(100, score)


# Fonction utilitaire pour usage synchrone
def scan_artist_sync(artist_name: str) -> Dict[str, Any]:
    """Version synchrone du scanner"""
    async def _scan():
        async with WebArtistScanner() as scanner:
            profile = await scanner.scan_artist(artist_name)
            return profile.to_dict()
    
    return asyncio.run(_scan())
