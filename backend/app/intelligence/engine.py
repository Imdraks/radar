"""
Intelligence Engine - Orchestration du moteur intelligent de collecte
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import quote_plus
import logging
import aiohttp
from bs4 import BeautifulSoup

from .smart_crawler import SmartCrawler
from .price_extractor import PriceExtractor, ExtractedPrice
from .contact_extractor import ContactExtractor, ExtractedContact
from .artist_analyzer import ArtistAnalyzer, ArtistProfile
from .opportunity_scorer import OpportunityScorer, ScoringResult

logger = logging.getLogger(__name__)

# ============================================================================
# 🎵 BASE DE DONNÉES MASSIVE DE SOURCES FIABLES
# ============================================================================

# ==================== BILLETTERIE FRANCE ====================
TICKETING_FR = [
    "https://www.fnacspectacles.com/recherche/{query}",
    "https://www.ticketmaster.fr/search?q={query}",
    "https://www.billetreduc.com/recherche.htm?keywords={query}",
    "https://www.digitick.com/recherche?q={query}",
    "https://www.francebillet.com/recherche/{query}",
    "https://www.carrefourspectacles.fr/recherche?q={query}",
    "https://www.seetickets.com/fr/search?q={query}",
    "https://www.eventim.fr/search/?searchterm={query}",
    "https://www.ticketac.com/recherche?q={query}",
    "https://www.billetnet.fr/recherche?q={query}",
    "https://www.ticketswap.fr/search?query={query}",
    "https://www.stubhub.fr/recherche?q={query}",
    "https://www.viagogo.fr/recherche?q={query}",
]

# ==================== BILLETTERIE INTERNATIONALE ====================
TICKETING_INTL = [
    "https://www.ticketmaster.com/search?q={query}",
    "https://www.axs.com/search?q={query}",
    "https://www.eventbrite.com/d/france/search?q={query}",
    "https://www.eventbrite.fr/d/france/search?q={query}",
    "https://dice.fm/search?query={query}",
    "https://www.residentadvisor.net/search?q={query}",
]

# ==================== CONCERTS & FESTIVALS ====================
CONCERTS_FESTIVALS = [
    "https://www.infoconcert.com/recherche?q={query}",
    "https://www.concertandco.com/recherche?q={query}",
    "https://www.sortiraparis.com/recherche?q={query}",
    "https://www.lyonpremiere.com/recherche?q={query}",
    "https://www.agenda-concerts.com/recherche.php?q={query}",
    "https://www.festivalfinder.eu/search?q={query}",
    "https://www.festivalsrock.com/recherche?q={query}",
    "https://www.touslesfestivals.com/recherche?q={query}",
    "https://www.timeout.fr/paris/search?q={query}",
    "https://www.offi.fr/recherche?q={query}",
    "https://www.parisbouge.com/recherche?q={query}",
    "https://www.lyonbouge.com/recherche?q={query}",
    "https://www.bordeauxbouge.com/recherche?q={query}",
    "https://www.lillebuzz.com/recherche?q={query}",
    "https://www.nantes.maville.com/recherche?q={query}",
]

# ==================== ARTISTES & ANALYTICS ====================
ARTIST_ANALYTICS = [
    "https://www.viberate.com/artist/{slug}/",
    "https://www.songkick.com/search?query={query}&type=artists",
    "https://www.bandsintown.com/search?search_term={query}",
    "https://www.setlist.fm/search?query={query}",
    "https://www.discogs.com/search/?q={query}&type=artist",
    "https://www.allmusic.com/search/artists/{query}",
    "https://musicbrainz.org/search?query={query}&type=artist",
    "https://www.last.fm/search/artists?q={query}",
    "https://www.genius.com/search?q={query}",
    "https://chartmetric.com/search?q={query}",
    "https://soundcharts.com/search?q={query}",
    "https://www.musicstax.com/search?q={query}",
]

# ==================== STREAMING & MUSIQUE ====================
STREAMING_MUSIC = [
    "https://open.spotify.com/search/{query}",
    "https://music.apple.com/fr/search?term={query}",
    "https://www.deezer.com/search/{query}",
    "https://soundcloud.com/search?q={query}",
    "https://www.youtube.com/results?search_query={query}",
    "https://music.youtube.com/search?q={query}",
    "https://tidal.com/search?q={query}",
    "https://www.qobuz.com/fr-fr/search?q={query}",
]

# ==================== BOOKING & MANAGEMENT ====================
BOOKING_AGENCIES = [
    "https://www.musicagent.fr/recherche?q={query}",
    "https://www.music-booking.com/recherche/{query}",
    "https://www.artiste-booking.com/recherche?q={query}",
    "https://www.zikinf.com/annuaire/recherche.php?q={query}",
    "https://www.unitedtalent.com/search?q={query}",
    "https://www.cfrench.fr/recherche?q={query}",
    "https://www.wagram-music.com/recherche?q={query}",
    "https://www.because.tv/recherche?q={query}",
    "https://www.musicast.fr/recherche?q={query}",
    "https://www.asterios.fr/recherche?q={query}",
]

# ==================== LABELS & MAISONS DE DISQUES ====================
RECORD_LABELS = [
    "https://www.universalmusic.fr/recherche?q={query}",
    "https://www.sonymusic.fr/recherche?q={query}",
    "https://www.warnermusic.fr/recherche?q={query}",
    "https://www.believe.com/search?q={query}",
    "https://www.musicasti.com/recherche?q={query}",
    "https://www.thelabelfrance.com/recherche?q={query}",
    "https://www.dfrench.fr/recherche?q={query}",
    "https://www.rec118.com/recherche?q={query}",
]

# ==================== MÉDIAS MUSIQUE FRANCE ====================
MEDIA_MUSIC_FR = [
    "https://www.mouv.fr/recherche?q={query}",
    "https://www.raprnb.com/?s={query}",
    "https://www.booska-p.com/?s={query}",
    "https://www.generations.fr/recherche?q={query}",
    "https://www.skyrock.fm/recherche?q={query}",
    "https://www.nrj.fr/recherche?q={query}",
    "https://www.funradio.fr/recherche?q={query}",
    "https://www.rtl2.fr/recherche?q={query}",
    "https://www.virginradio.fr/recherche?q={query}",
    "https://www.oui.fm/recherche?q={query}",
    "https://www.fip.fr/recherche?q={query}",
    "https://www.nova.fr/recherche?q={query}",
    "https://www.radiofrance.fr/recherche?q={query}",
]

# ==================== MÉDIAS RAP/URBAIN ====================
MEDIA_RAP_URBAN = [
    "https://www.booska-p.com/?s={query}",
    "https://www.rapelite.com/?s={query}",
    "https://www.rapfanz.com/?s={query}",
    "https://www.lacoccinelle.net/recherche?q={query}",
    "https://www.abcdrduson.com/recherche?q={query}",
    "https://www.lerapenfrance.fr/?s={query}",
    "https://www.hiphopcorner.fr/?s={query}",
    "https://www.rapgenius.fr/?s={query}",
    "https://www.culturedrap.com/?s={query}",
    "https://www.lerapfrancais.fr/?s={query}",
]

# ==================== MÉDIAS CULTURE/MUSIQUE GÉNÉRALISTES ====================
MEDIA_CULTURE = [
    "https://www.lesinrocks.com/recherche/?q={query}",
    "https://www.telerama.fr/recherche?q={query}",
    "https://www.rollingstone.fr/?s={query}",
    "https://www.lemonde.fr/recherche/?search_keywords={query}",
    "https://www.lefigaro.fr/recherche?q={query}",
    "https://www.liberation.fr/recherche?q={query}",
    "https://www.franceinter.fr/recherche?q={query}",
    "https://www.franceculture.fr/recherche?q={query}",
    "https://www.francetvinfo.fr/recherche?q={query}",
    "https://www.20minutes.fr/recherche?q={query}",
    "https://www.huffingtonpost.fr/recherche?q={query}",
    "https://www.konbini.com/recherche?q={query}",
    "https://www.vice.com/fr/search?q={query}",
    "https://www.tsugi.fr/?s={query}",
    "https://www.traxmag.com/?s={query}",
    "https://www.clique.tv/recherche?q={query}",
]

# ==================== MODE & LIFESTYLE ====================
FASHION_LIFESTYLE = [
    "https://www.vogue.fr/recherche?q={query}",
    "https://www.glamour.fr/recherche?q={query}",
    "https://www.marieclaire.fr/recherche?q={query}",
    "https://www.elle.fr/recherche?q={query}",
    "https://www.gq.com/fr/recherche?q={query}",
    "https://www.lofficiel.com/recherche?q={query}",
    "https://www.numero.com/recherche?q={query}",
    "https://www.hypebeast.com/fr/search?q={query}",
    "https://www.highsnobiety.com/search?q={query}",
    "https://www.complex.com/search?q={query}",
    "https://www.grazia.fr/recherche?q={query}",
    "https://www.cosmopolitan.fr/recherche?q={query}",
    "https://www.gala.fr/recherche?q={query}",
    "https://www.voici.fr/recherche?q={query}",
    "https://www.puretrend.com/recherche?q={query}",
    "https://www.fashionunited.fr/recherche?q={query}",
]

# ==================== ART & EXPOSITIONS ====================
ART_EXHIBITIONS = [
    "https://www.paris.fr/recherche?q={query}",
    "https://www.centrepompidou.fr/recherche?q={query}",
    "https://www.louvre.fr/recherche?q={query}",
    "https://www.musee-orsay.fr/recherche?q={query}",
    "https://www.grandpalais.fr/recherche?q={query}",
    "https://www.palaisdetokyo.com/recherche?q={query}",
    "https://www.fondationlouisvuitton.fr/recherche?q={query}",
    "https://www.beauxartsparis.fr/recherche?q={query}",
    "https://www.mairie-paris.fr/recherche?q={query}",
    "https://www.artnet.fr/recherche?q={query}",
    "https://www.artprice.com/recherche?q={query}",
    "https://www.connaissancedesarts.com/?s={query}",
    "https://www.beauxarts.com/?s={query}",
    "https://www.artactu.com/?s={query}",
    "https://www.slash-paris.com/?s={query}",
]

# ==================== THÉÂTRE & SPECTACLE VIVANT ====================
THEATER_LIVE = [
    "https://www.theatreonline.com/recherche?q={query}",
    "https://www.theatredesbouffesdunord.com/recherche?q={query}",
    "https://www.theatre-odeon.eu/recherche?q={query}",
    "https://www.comedie-francaise.fr/recherche?q={query}",
    "https://www.theatreduchene.fr/recherche?q={query}",
    "https://www.theatre-champs-elysees.fr/recherche?q={query}",
    "https://www.chatelet.com/recherche?q={query}",
    "https://www.opera-national-paris.fr/recherche?q={query}",
    "https://www.operadeparis.fr/recherche?q={query}",
    "https://www.theatreinparis.com/recherche?q={query}",
    "https://www.spectacles.carrefour.fr/recherche?q={query}",
]

# ==================== SALLES DE CONCERT FRANCE ====================
VENUES_FR = [
    "https://www.accorarenaparis.com/agenda?search={query}",
    "https://www.olympiahall.com/agenda?search={query}",
    "https://www.zenith-paris.com/agenda?search={query}",
    "https://www.bataclan.fr/recherche?q={query}",
    "https://www.elysee-montmartre.com/agenda?search={query}",
    "https://www.sallepleyel.com/recherche?q={query}",
    "https://www.philharmoniedeparis.fr/fr/recherche?q={query}",
    "https://www.casino-de-paris.fr/recherche?q={query}",
    "https://www.laflechedor.fr/recherche?q={query}",
    "https://www.trabendo.fr/recherche?q={query}",
    "https://www.lagaite-lyrique.net/recherche?q={query}",
    "https://www.104.fr/recherche?q={query}",
    "https://www.lamachine.fr/recherche?q={query}",
    "https://www.pointephemere.org/recherche?q={query}",
    "https://www.lescomblesdelachine.fr/recherche?q={query}",
    "https://www.stereolux.org/recherche?q={query}",
    "https://www.aeronef.fr/recherche?q={query}",
    "https://www.krakatoa.org/recherche?q={query}",
    "https://www.rockschool-barbey.com/recherche?q={query}",
    "https://www.transbordeur.fr/recherche?q={query}",
    "https://www.ninkasi.fr/recherche?q={query}",
    "https://www.summum-grenoble.com/recherche?q={query}",
    "https://www.zenith-nantes.com/recherche?q={query}",
    "https://www.zenith-toulouse.com/recherche?q={query}",
    "https://www.dome-marseille.com/recherche?q={query}",
]

# ==================== CLUBS & ÉLECTRO ====================
CLUBS_ELECTRO = [
    "https://www.residentadvisor.net/search?q={query}",
    "https://www.shotgun.live/recherche?q={query}",
    "https://www.traxmag.com/?s={query}",
    "https://www.electro-news.eu/?s={query}",
    "https://www.mixmag.fr/?s={query}",
    "https://www.djanemag.com/search?q={query}",
    "https://www.clubbingfrance.com/recherche?q={query}",
    "https://www.rfrenchtouch.com/?s={query}",
]

# ==================== ÉVÉNEMENTIEL & PRODUCTION ====================
EVENT_PRODUCTION = [
    "https://www.leliveparis.com/recherche?q={query}",
    "https://www.prodiss.org/recherche?q={query}",
    "https://www.irma.asso.fr/recherche?q={query}",
    "https://www.zone-events.net/recherche?q={query}",
    "https://www.adami.fr/recherche?q={query}",
    "https://www.sacem.fr/recherche?q={query}",
    "https://www.cnm.fr/recherche?q={query}",
    "https://www.francefestivals.com/recherche?q={query}",
]

# ==================== RÉSEAUX SOCIAUX & INFLUENCE ====================
SOCIAL_INFLUENCE = [
    "https://www.instagram.com/explore/tags/{slug}/",
    "https://www.tiktok.com/search?q={query}",
    "https://twitter.com/search?q={query}",
    "https://www.facebook.com/search/top?q={query}",
    "https://www.linkedin.com/search/results/all/?keywords={query}",
]

# ==================== MARCHÉS PUBLICS & APPELS D'OFFRES ====================
PUBLIC_MARKETS = [
    "https://www.boamp.fr/avis/search?q={query}",
    "https://www.marches-publics.gouv.fr/?q={query}",
    "https://www.achatpublic.com/recherche?q={query}",
    "https://www.klekoon.com/recherche?q={query}",
    "https://www.marchesonline.com/recherche?q={query}",
    "https://www.e-marchespublics.com/recherche?q={query}",
    "https://www.doubletrade.fr/recherche?q={query}",
]

# ==================== ANNUAIRES PROFESSIONNELS ====================
PRO_DIRECTORIES = [
    "https://www.societe.com/cgi-bin/search?champs={query}",
    "https://www.kompass.com/fr/searchCompanies?q={query}",
    "https://www.pagesjaunes.fr/recherche?q={query}",
    "https://annuaire-entreprises.data.gouv.fr/rechercher?terme={query}",
    "https://www.linkedin.com/search/results/companies/?keywords={query}",
]


class IntelligenceEngine:
    """
    Moteur d'intelligence principal qui :
    - Crawle intelligemment les sites web
    - Extrait prix, contacts, conditions
    - Analyse les artistes et leurs cachets
    - Score les opportunités
    - Retourne des données enrichies et structurées
    """
    
    def __init__(self, agency_profile: Optional[Dict[str, Any]] = None):
        self.crawler = SmartCrawler()
        self.price_extractor = PriceExtractor()
        self.contact_extractor = ContactExtractor()
        self.artist_analyzer = ArtistAnalyzer()
        self.opportunity_scorer = OpportunityScorer(agency_profile)
    
    async def search_and_analyze(
        self,
        query: str,
        search_params: Optional[Dict[str, Any]] = None,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Recherche intelligente et analyse complète
        
        Args:
            query: Terme de recherche (ex: "concert rap Paris", "PNL cachet")
            search_params: Paramètres additionnels (budget, région, etc.)
            sources: URLs sources à crawler
        """
        print(f"\n{'='*70}", flush=True)
        print(f"🧠 INTELLIGENCE ENGINE - search_and_analyze", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"   Query: {query}", flush=True)
        print(f"   Params: {search_params}", flush=True)
        print(f"   Sources fournies: {len(sources) if sources else 0} URLs", flush=True)
        
        results = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'opportunities': [],
            'artists': [],
            'contacts': [],
            'prices': [],
            'summary': {},
        }
        
        search_params = search_params or {}
        
        # Déterminer si c'est une recherche d'artiste
        is_artist_search = self._is_artist_query(query)
        print(f"   Is Artist Search: {is_artist_search}", flush=True)
        
        # Si pas de sources, utiliser les sources par défaut avec la query
        if not sources:
            print(f"   🔄 Pas de sources configurées, génération de sources automatiques...", flush=True)
            sources = await self._generate_search_sources(query, is_artist_search)
            print(f"   📡 {len(sources)} sources générées", flush=True)
        
        if sources:
            print(f"\n   📡 Analyse des {len(sources)} sources...", flush=True)
            # Crawler les sources fournies
            for i, source_url in enumerate(sources):
                try:
                    print(f"      [{i+1}/{len(sources)}] {source_url[:60]}...", flush=True)
                    data = await self._analyze_source(source_url, query, is_artist_search)
                    if data:
                        self._merge_results(results, data)
                        print(f"         ✅ +{len(data.get('opportunities', []))} opps, +{len(data.get('artists', []))} artistes", flush=True)
                    else:
                        print(f"         ⚠️ Aucune donnée", flush=True)
                except Exception as e:
                    print(f"         ❌ Erreur: {e}", flush=True)
                    logger.error(f"Error analyzing {source_url}: {e}")
        else:
            print(f"   ⚠️ Aucune source disponible!", flush=True)
        
        # Post-traitement et scoring
        print(f"\n   📊 Post-traitement...", flush=True)
        results = self._post_process(results, search_params)
        
        # Générer le résumé
        results['summary'] = self._generate_summary(results)
        
        print(f"\n   ✅ RÉSULTATS FINAUX:", flush=True)
        print(f"      Opportunités: {len(results.get('opportunities', []))}", flush=True)
        print(f"      Artistes: {len(results.get('artists', []))}", flush=True)
        print(f"      Contacts: {len(results.get('contacts', []))}", flush=True)
        print(f"      Prix: {len(results.get('prices', []))}", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        return results
    
    async def _analyze_source(
        self,
        url: str,
        query: str,
        is_artist_search: bool
    ) -> Dict[str, Any]:
        """Analyse une source URL"""
        result = {
            'opportunities': [],
            'artists': [],
            'contacts': [],
            'prices': [],
        }
        
        try:
            # Crawler la page
            crawl_data = await self.crawler.crawl(url, max_depth=2, max_pages=10)
            
            if not crawl_data.get('pages'):
                return result
            
            for page in crawl_data['pages']:
                content = page.get('content', '')
                page_url = page.get('url', url)
                
                # Extraire les prix
                prices = self.price_extractor.extract_prices(content)
                for price in prices:
                    price_dict = price.to_dict()
                    price_dict['source_url'] = page_url
                    result['prices'].append(price_dict)
                
                # Extraire les contacts
                contacts = self.contact_extractor.extract_contacts(content)
                for contact in contacts:
                    contact_dict = contact.to_dict()
                    contact_dict['source_url'] = page_url
                    result['contacts'].append(contact_dict)
                
                # Si recherche artiste, analyser
                if is_artist_search:
                    artist = self.artist_analyzer.analyze_from_text(content, query)
                    if artist:
                        result['artists'].append(artist.to_dict())
                
                # Vérifier si c'est une opportunité
                if self._is_opportunity_page(content, page):
                    opportunity = self._extract_opportunity(page, prices, contacts)
                    if opportunity:
                        result['opportunities'].append(opportunity)
        
        except Exception as e:
            logger.error(f"Error in _analyze_source for {url}: {e}")
        
        return result
    
    async def _generate_search_sources(self, query: str, is_artist_search: bool) -> List[str]:
        """
        Génère automatiquement des URLs de recherche basées sur la query.
        Utilise des sites fiables de billetterie, événements et booking français/internationaux.
        """
        sources = []
        
        # Extraire le nom de l'artiste/recherche propre
        query_encoded = quote_plus(query)
        query_slug = query.lower().replace(' ', '-').replace("'", "").replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ù", "u").replace("ô", "o").replace("î", "i")
        
        # Fonction helper pour formatter les URLs
        def format_sources(source_list: List[str]) -> List[str]:
            formatted = []
            for url in source_list:
                try:
                    formatted.append(url.format(query=query_encoded, slug=query_slug))
                except:
                    pass
            return formatted
        
        # Détecter le type de recherche pour adapter les sources
        query_lower = query.lower()
        is_rap_urban = any(k in query_lower for k in ['rap', 'trap', 'drill', 'rnb', 'r&b', 'hip-hop', 'hip hop', 'urbain'])
        is_electro = any(k in query_lower for k in ['dj', 'electro', 'techno', 'house', 'edm', 'club'])
        is_fashion = any(k in query_lower for k in ['mode', 'fashion', 'style', 'vêtement', 'marque', 'designer'])
        is_art = any(k in query_lower for k in ['art', 'expo', 'musée', 'galerie', 'peintre', 'sculpteur'])
        is_theater = any(k in query_lower for k in ['théâtre', 'theatre', 'comédie', 'spectacle', 'pièce', 'opéra'])
        
        if is_artist_search:
            # === SOURCES POUR RECHERCHE D'ARTISTE ===
            
            # 1. Billetterie France (prioritaire)
            sources.extend(format_sources(TICKETING_FR[:8]))
            
            # 2. Artistes & Analytics (très important)
            sources.extend(format_sources(ARTIST_ANALYTICS))
            
            # 3. Streaming (pour les stats)
            sources.extend(format_sources(STREAMING_MUSIC[:5]))
            
            # 4. Concerts & festivals
            sources.extend(format_sources(CONCERTS_FESTIVALS[:8]))
            
            # 5. Booking agencies
            sources.extend(format_sources(BOOKING_AGENCIES))
            
            # 6. Labels
            sources.extend(format_sources(RECORD_LABELS[:4]))
            
            # 7. Salles de concert
            sources.extend(format_sources(VENUES_FR[:10]))
            
            # 8. Médias selon le genre
            if is_rap_urban:
                sources.extend(format_sources(MEDIA_RAP_URBAN))
                sources.extend(format_sources(MEDIA_MUSIC_FR[:5]))
            elif is_electro:
                sources.extend(format_sources(CLUBS_ELECTRO))
                sources.extend(format_sources(MEDIA_MUSIC_FR[:5]))
            else:
                sources.extend(format_sources(MEDIA_MUSIC_FR))
                sources.extend(format_sources(MEDIA_CULTURE[:5]))
            
            # 9. Mode/Lifestyle (pour les collabs)
            sources.extend(format_sources(FASHION_LIFESTYLE[:5]))
            
        elif is_fashion:
            # === SOURCES MODE ===
            sources.extend(format_sources(FASHION_LIFESTYLE))
            sources.extend(format_sources(MEDIA_CULTURE[:5]))
            sources.extend(format_sources(PRO_DIRECTORIES[:3]))
            
        elif is_art:
            # === SOURCES ART ===
            sources.extend(format_sources(ART_EXHIBITIONS))
            sources.extend(format_sources(MEDIA_CULTURE[:5]))
            sources.extend(format_sources(PUBLIC_MARKETS[:3]))
            
        elif is_theater:
            # === SOURCES THÉÂTRE ===
            sources.extend(format_sources(THEATER_LIVE))
            sources.extend(format_sources(TICKETING_FR[:5]))
            sources.extend(format_sources(MEDIA_CULTURE[:5]))
            
        else:
            # === SOURCES GÉNÉRALISTES (événements/marchés) ===
            
            # 1. Billetterie
            sources.extend(format_sources(TICKETING_FR))
            
            # 2. Concerts & festivals
            sources.extend(format_sources(CONCERTS_FESTIVALS))
            
            # 3. Marchés publics
            sources.extend(format_sources(PUBLIC_MARKETS))
            
            # 4. Événementiel
            sources.extend(format_sources(EVENT_PRODUCTION))
            
            # 5. Annuaires
            sources.extend(format_sources(PRO_DIRECTORIES[:3]))
        
        # Dédupliquer et limiter à 40 sources max
        seen = set()
        unique_sources = []
        for s in sources:
            if s not in seen:
                seen.add(s)
                unique_sources.append(s)
        sources = unique_sources[:40]
        
        print(f"   📋 {len(sources)} sources générées:", flush=True)
        for s in sources[:10]:
            print(f"      - {s[:65]}...", flush=True)
        if len(sources) > 10:
            print(f"      ... et {len(sources) - 10} autres sources", flush=True)
        
        return sources
    
    def _is_artist_query(self, query: str) -> bool:
        """Détecte si la recherche concerne un artiste"""
        artist_indicators = [
            'cachet', 'prix artiste', 'booking', 'fee',
            'concert', 'dj', 'rappeur', 'chanteur', 'groupe',
            'artiste', 'musicien', 'band', 'singer', 'rapper',
            'contact', 'management', 'label', 'tournée', 'tour'
        ]
        query_lower = query.lower()
        
        # Vérifier si nom propre (majuscule)
        words = query.split()
        has_proper_noun = any(w[0].isupper() for w in words if len(w) > 1)
        
        return has_proper_noun or any(ind in query_lower for ind in artist_indicators)
    
    def _is_opportunity_page(self, content: str, page_data: Dict) -> bool:
        """Vérifie si la page contient une opportunité"""
        indicators = [
            'appel d\'offres', 'marché public', 'consultation',
            'budget', 'candidature', 'dépôt', 'date limite',
            'lot', 'prestation', 'cahier des charges',
            'événement', 'festival', 'concert', 'spectacle',
            'recherche', 'cherche', 'casting'
        ]
        
        content_lower = content.lower()
        score = sum(1 for ind in indicators if ind in content_lower)
        
        return score >= 3
    
    def _extract_opportunity(
        self,
        page_data: Dict,
        prices: List[ExtractedPrice],
        contacts: List[ExtractedContact]
    ) -> Optional[Dict[str, Any]]:
        """Extrait une opportunité structurée"""
        content = page_data.get('content', '')
        
        opportunity = {
            'title': page_data.get('title', 'Opportunité'),
            'description': content[:1000] if len(content) > 1000 else content,
            'source_url': page_data.get('url'),
            'discovered_at': datetime.now().isoformat(),
            'contacts': [c.to_dict() for c in contacts[:3]],
            'prices': [p.to_dict() for p in prices[:5]],
            'deadline': self._extract_deadline(content),
            'budget': self._extract_main_budget(prices),
            'location': self._extract_location(content),
        }
        
        return opportunity
    
    def _extract_deadline(self, content: str) -> Optional[str]:
        """Extrait la date limite"""
        import re
        
        patterns = [
            r'date limite[:\s]+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'avant le[:\s]+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'deadline[:\s]+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'clôture[:\s]+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_main_budget(self, prices: List) -> Optional[float]:
        """Extrait le budget principal"""
        if not prices:
            return None
        
        # Chercher un prix de type BUDGET
        budget_prices = [p for p in prices if hasattr(p, 'price_type') and 'BUDGET' in str(p.price_type)]
        if budget_prices:
            return budget_prices[0].value if hasattr(budget_prices[0], 'value') else budget_prices[0].get('value')
        
        # Sinon, prendre le prix le plus élevé
        values = []
        for p in prices:
            if hasattr(p, 'value'):
                values.append(p.value)
            elif isinstance(p, dict) and p.get('value'):
                values.append(p['value'])
        
        return max(values) if values else None
    
    def _extract_location(self, content: str) -> Optional[str]:
        """Extrait la localisation"""
        import re
        
        cities = [
            'paris', 'lyon', 'marseille', 'bordeaux', 'toulouse',
            'nantes', 'lille', 'strasbourg', 'nice', 'montpellier',
            'rennes', 'reims', 'le havre', 'saint-étienne', 'toulon'
        ]
        
        regions = [
            'île-de-france', 'ile-de-france', 'paca', 'occitanie',
            'nouvelle-aquitaine', 'bretagne', 'grand est'
        ]
        
        content_lower = content.lower()
        
        for city in cities:
            if city in content_lower:
                return city.title()
        
        for region in regions:
            if region in content_lower:
                return region.title()
        
        return None
    
    def _merge_results(self, results: Dict, new_data: Dict):
        """Fusionne les résultats"""
        results['opportunities'].extend(new_data.get('opportunities', []))
        results['artists'].extend(new_data.get('artists', []))
        results['contacts'].extend(new_data.get('contacts', []))
        results['prices'].extend(new_data.get('prices', []))
    
    def _post_process(
        self,
        results: Dict,
        search_params: Dict
    ) -> Dict:
        """Post-traitement des résultats"""
        
        # Dédupliquer les contacts
        seen_emails = set()
        unique_contacts = []
        for contact in results['contacts']:
            email = contact.get('email')
            if email and email.lower() not in seen_emails:
                seen_emails.add(email.lower())
                unique_contacts.append(contact)
            elif not email:
                unique_contacts.append(contact)
        results['contacts'] = unique_contacts[:20]  # Max 20 contacts
        
        # Scorer les opportunités
        scored_opportunities = []
        for opp in results['opportunities']:
            score_result = self.opportunity_scorer.score(opp)
            opp['scoring'] = score_result.to_dict()
            scored_opportunities.append(opp)
        
        # Trier par score
        results['opportunities'] = sorted(
            scored_opportunities,
            key=lambda x: x['scoring']['total_score'],
            reverse=True
        )[:50]  # Max 50 opportunités
        
        # Filtrer par budget si spécifié
        if search_params.get('budget_min') or search_params.get('budget_max'):
            results['opportunities'] = self._filter_by_budget(
                results['opportunities'],
                search_params.get('budget_min'),
                search_params.get('budget_max')
            )
        
        # Filtrer par région si spécifié
        if search_params.get('region'):
            results['opportunities'] = [
                opp for opp in results['opportunities']
                if opp.get('location') and 
                   search_params['region'].lower() in opp['location'].lower()
            ]
        
        return results
    
    def _filter_by_budget(
        self,
        opportunities: List[Dict],
        min_budget: Optional[float],
        max_budget: Optional[float]
    ) -> List[Dict]:
        """Filtre par fourchette de budget"""
        filtered = []
        
        for opp in opportunities:
            budget = opp.get('budget')
            if not budget:
                filtered.append(opp)  # Garder si pas de budget connu
                continue
            
            if min_budget and budget < min_budget:
                continue
            if max_budget and budget > max_budget:
                continue
            
            filtered.append(opp)
        
        return filtered
    
    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """Génère un résumé des résultats"""
        opportunities = results.get('opportunities', [])
        
        # Compter les grades
        grade_counts = {}
        for opp in opportunities:
            grade = opp.get('scoring', {}).get('grade', 'unknown')
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Budget moyen
        budgets = [o.get('budget') for o in opportunities if o.get('budget')]
        avg_budget = sum(budgets) / len(budgets) if budgets else 0
        
        # Artistes trouvés
        artists = results.get('artists', [])
        artist_summary = []
        for artist in artists[:5]:
            artist_summary.append({
                'name': artist.get('name'),
                'fee_range': artist.get('fee_range'),
                'trend': artist.get('market_trend'),
            })
        
        return {
            'total_opportunities': len(opportunities),
            'high_quality_count': grade_counts.get('A+', 0) + grade_counts.get('A', 0),
            'grade_distribution': grade_counts,
            'avg_budget': round(avg_budget, 2) if avg_budget else None,
            'total_contacts': len(results.get('contacts', [])),
            'total_prices': len(results.get('prices', [])),
            'artists_found': artist_summary,
            'top_opportunity': opportunities[0] if opportunities else None,
        }
    
    async def analyze_artist(self, artist_name: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        Analyse spécifique d'un artiste
        """
        result = {
            'artist_name': artist_name,
            'profiles': [],
            'estimated_fee': None,
            'recent_events': [],
            'booking_contacts': [],
            'market_analysis': {},
        }
        
        # Sources par défaut pour les artistes
        default_sources = [
            f'https://www.google.com/search?q={artist_name}+cachet+concert',
            f'https://www.irma.asso.fr/recherche?q={artist_name}',
        ]
        
        sources = sources or default_sources
        
        for url in sources:
            try:
                crawl_data = await self.crawler.crawl(url, max_depth=1, max_pages=5)
                
                for page in crawl_data.get('pages', []):
                    content = page.get('content', '')
                    
                    # Analyser l'artiste
                    artist = self.artist_analyzer.analyze_from_text(content, artist_name)
                    if artist:
                        result['profiles'].append(artist.to_dict())
                    
                    # Contacts booking
                    contacts = self.contact_extractor.extract_contacts(content)
                    booking_contacts = [c for c in contacts if c.contact_type.value == 'booking']
                    for contact in booking_contacts:
                        result['booking_contacts'].append(contact.to_dict())
                    
                    # Prix/cachets
                    fee = self.price_extractor.extract_artist_fee(content)
                    if fee:
                        result['estimated_fee'] = fee.to_dict()
            
            except Exception as e:
                logger.error(f"Error analyzing artist from {url}: {e}")
        
        # Consolider les résultats
        if result['profiles']:
            # Moyenne des fees
            fees = [p.get('fee_range', {}) for p in result['profiles']]
            min_fees = [f.get('min', 0) for f in fees if f.get('min')]
            max_fees = [f.get('max', 0) for f in fees if f.get('max')]
            
            result['market_analysis'] = {
                'estimated_fee_range': {
                    'min': sum(min_fees) / len(min_fees) if min_fees else None,
                    'max': sum(max_fees) / len(max_fees) if max_fees else None,
                },
                'profiles_found': len(result['profiles']),
                'booking_contacts_found': len(result['booking_contacts']),
            }
        
        return result


# Instance globale pour utilisation dans les workers
_engine: Optional[IntelligenceEngine] = None

def get_intelligence_engine() -> IntelligenceEngine:
    """Retourne l'instance du moteur d'intelligence"""
    global _engine
    if _engine is None:
        _engine = IntelligenceEngine()
    return _engine
