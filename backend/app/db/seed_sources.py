"""
Script pour peupler la base de données avec toutes les sources fiables.
Exécuter avec: python -m app.db.seed_sources
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import get_db
from app.db.models.source import SourceConfig
from app.db.models.opportunity import SourceType

# ============================================================================
# 🎵 TOUTES LES SOURCES FIABLES PAR CATÉGORIE
# ============================================================================

SOURCES = [
    # ==================== BILLETTERIE FRANCE ====================
    {"name": "Fnac Spectacles", "url": "https://www.fnacspectacles.com", "category": "billetterie", "description": "Billetterie Fnac - Concerts, spectacles, théâtre"},
    {"name": "Ticketmaster France", "url": "https://www.ticketmaster.fr", "category": "billetterie", "description": "Leader mondial de la billetterie"},
    {"name": "Billetreduc", "url": "https://www.billetreduc.com", "category": "billetterie", "description": "Réductions sur les spectacles"},
    {"name": "Digitick", "url": "https://www.digitick.com", "category": "billetterie", "description": "Billetterie en ligne"},
    {"name": "France Billet", "url": "https://www.francebillet.com", "category": "billetterie", "description": "Billetterie spectacles France"},
    {"name": "Carrefour Spectacles", "url": "https://www.carrefourspectacles.fr", "category": "billetterie", "description": "Billetterie Carrefour"},
    {"name": "SeeTickets France", "url": "https://www.seetickets.com/fr", "category": "billetterie", "description": "Billetterie internationale"},
    {"name": "Eventim France", "url": "https://www.eventim.fr", "category": "billetterie", "description": "Billetterie Eventim"},
    {"name": "TicketSwap France", "url": "https://www.ticketswap.fr", "category": "billetterie", "description": "Revente de billets sécurisée"},
    
    # ==================== BILLETTERIE INTERNATIONALE ====================
    {"name": "Eventbrite France", "url": "https://www.eventbrite.fr", "category": "billetterie", "description": "Événements et billetterie"},
    {"name": "DICE", "url": "https://dice.fm", "category": "billetterie", "description": "Billetterie mobile"},
    {"name": "Resident Advisor", "url": "https://www.residentadvisor.net", "category": "électro", "description": "Référence mondiale musique électronique"},
    
    # ==================== CONCERTS & FESTIVALS ====================
    {"name": "Infoconcert", "url": "https://www.infoconcert.com", "category": "concerts", "description": "Agenda des concerts en France"},
    {"name": "Concert and Co", "url": "https://www.concertandco.com", "category": "concerts", "description": "Billetterie concerts"},
    {"name": "Sortir à Paris", "url": "https://www.sortiraparis.com", "category": "concerts", "description": "Sorties et événements Paris"},
    {"name": "Lyon Première", "url": "https://www.lyonpremiere.com", "category": "concerts", "description": "Sorties et événements Lyon"},
    {"name": "Agenda Concerts", "url": "https://www.agenda-concerts.com", "category": "concerts", "description": "Agenda national des concerts"},
    {"name": "Festival Finder", "url": "https://www.festivalfinder.eu", "category": "festivals", "description": "Festivals européens"},
    {"name": "Tous les Festivals", "url": "https://www.touslesfestivals.com", "category": "festivals", "description": "Guide des festivals français"},
    {"name": "Timeout Paris", "url": "https://www.timeout.fr/paris", "category": "concerts", "description": "Guide sorties Paris"},
    {"name": "L'Officiel des Spectacles", "url": "https://www.offi.fr", "category": "concerts", "description": "Programme spectacles Paris"},
    {"name": "Paris Bouge", "url": "https://www.parisbouge.com", "category": "concerts", "description": "Guide sorties Paris"},
    
    # ==================== ARTISTES & ANALYTICS ====================
    {"name": "Viberate", "url": "https://www.viberate.com", "category": "analytics", "description": "Analytics et données artistes"},
    {"name": "Songkick", "url": "https://www.songkick.com", "category": "concerts", "description": "Concerts et tournées mondiales"},
    {"name": "Bandsintown", "url": "https://www.bandsintown.com", "category": "concerts", "description": "Alertes concerts et tournées"},
    {"name": "Setlist.fm", "url": "https://www.setlist.fm", "category": "concerts", "description": "Historique des setlists"},
    {"name": "Discogs", "url": "https://www.discogs.com", "category": "musique", "description": "Base de données musicale"},
    {"name": "AllMusic", "url": "https://www.allmusic.com", "category": "musique", "description": "Encyclopédie musicale"},
    {"name": "MusicBrainz", "url": "https://musicbrainz.org", "category": "musique", "description": "Base de données open source"},
    {"name": "Last.fm", "url": "https://www.last.fm", "category": "musique", "description": "Scrobbling et recommandations"},
    {"name": "Genius", "url": "https://genius.com", "category": "musique", "description": "Paroles et annotations"},
    
    # ==================== STREAMING ====================
    {"name": "Spotify", "url": "https://open.spotify.com", "category": "streaming", "description": "Plateforme de streaming n°1"},
    {"name": "Apple Music", "url": "https://music.apple.com/fr", "category": "streaming", "description": "Streaming Apple"},
    {"name": "Deezer", "url": "https://www.deezer.com", "category": "streaming", "description": "Streaming français"},
    {"name": "SoundCloud", "url": "https://soundcloud.com", "category": "streaming", "description": "Plateforme artistes indépendants"},
    {"name": "YouTube Music", "url": "https://music.youtube.com", "category": "streaming", "description": "Streaming YouTube"},
    {"name": "Tidal", "url": "https://tidal.com", "category": "streaming", "description": "Streaming haute qualité"},
    {"name": "Qobuz", "url": "https://www.qobuz.com/fr-fr", "category": "streaming", "description": "Streaming audiophile français"},
    
    # ==================== BOOKING & MANAGEMENT ====================
    {"name": "MusicAgent", "url": "https://www.musicagent.fr", "category": "booking", "description": "Annuaire booking France"},
    {"name": "Music Booking", "url": "https://www.music-booking.com", "category": "booking", "description": "Plateforme booking"},
    {"name": "Artiste Booking", "url": "https://www.artiste-booking.com", "category": "booking", "description": "Booking artistes"},
    {"name": "Zikinf", "url": "https://www.zikinf.com", "category": "booking", "description": "Annuaire musique"},
    {"name": "Wagram Music", "url": "https://www.wagram-music.com", "category": "label", "description": "Label et booking français"},
    {"name": "Because Music", "url": "https://www.because.tv", "category": "label", "description": "Label indépendant français"},
    
    # ==================== LABELS ====================
    {"name": "Universal Music France", "url": "https://www.universalmusic.fr", "category": "label", "description": "Major Universal"},
    {"name": "Sony Music France", "url": "https://www.sonymusic.fr", "category": "label", "description": "Major Sony"},
    {"name": "Warner Music France", "url": "https://www.warnermusic.fr", "category": "label", "description": "Major Warner"},
    {"name": "Believe Digital", "url": "https://www.believe.com", "category": "label", "description": "Distribution digitale"},
    
    # ==================== MÉDIAS MUSIQUE ====================
    {"name": "Mouv'", "url": "https://www.mouv.fr", "category": "média", "description": "Radio urbaine Radio France"},
    {"name": "Skyrock", "url": "https://www.skyrock.fm", "category": "média", "description": "Radio rap/RnB n°1"},
    {"name": "NRJ", "url": "https://www.nrj.fr", "category": "média", "description": "Radio hits"},
    {"name": "Fun Radio", "url": "https://www.funradio.fr", "category": "média", "description": "Radio dance/électro"},
    {"name": "RTL2", "url": "https://www.rtl2.fr", "category": "média", "description": "Radio pop/rock"},
    {"name": "Virgin Radio", "url": "https://www.virginradio.fr", "category": "média", "description": "Radio rock/pop"},
    {"name": "Nova", "url": "https://www.nova.fr", "category": "média", "description": "Radio indépendante"},
    {"name": "FIP", "url": "https://www.fip.fr", "category": "média", "description": "Radio éclectique Radio France"},
    {"name": "Generations", "url": "https://www.generations.fr", "category": "média", "description": "Radio rap/RnB"},
    
    # ==================== MÉDIAS RAP/URBAIN ====================
    {"name": "Booska-P", "url": "https://www.booska-p.com", "category": "média rap", "description": "Média rap n°1 France"},
    {"name": "Rap RnB", "url": "https://www.raprnb.com", "category": "média rap", "description": "Actualité rap/RnB"},
    {"name": "ABCDR du Son", "url": "https://www.abcdrduson.com", "category": "média rap", "description": "Webzine rap culture"},
    {"name": "Hip Hop Corner", "url": "https://www.hiphopcorner.fr", "category": "média rap", "description": "Actualité hip-hop"},
    {"name": "Culturedrap", "url": "https://www.culturedrap.com", "category": "média rap", "description": "Culture rap française"},
    
    # ==================== MÉDIAS CULTURE ====================
    {"name": "Les Inrockuptibles", "url": "https://www.lesinrocks.com", "category": "média culture", "description": "Magazine culturel"},
    {"name": "Télérama", "url": "https://www.telerama.fr", "category": "média culture", "description": "Critique culturelle"},
    {"name": "Rolling Stone France", "url": "https://www.rollingstone.fr", "category": "média culture", "description": "Magazine rock/pop"},
    {"name": "Konbini", "url": "https://www.konbini.com", "category": "média culture", "description": "Pop culture"},
    {"name": "Vice France", "url": "https://www.vice.com/fr", "category": "média culture", "description": "Culture alternative"},
    {"name": "Tsugi", "url": "https://www.tsugi.fr", "category": "média électro", "description": "Magazine électro"},
    {"name": "Trax Magazine", "url": "https://www.traxmag.com", "category": "média électro", "description": "Magazine électro/clubbing"},
    {"name": "Clique TV", "url": "https://www.clique.tv", "category": "média culture", "description": "Pop culture Mouloud Achour"},
    
    # ==================== MODE & LIFESTYLE ====================
    {"name": "Vogue France", "url": "https://www.vogue.fr", "category": "mode", "description": "Magazine mode référence"},
    {"name": "Elle", "url": "https://www.elle.fr", "category": "mode", "description": "Magazine féminin mode"},
    {"name": "GQ France", "url": "https://www.gqmagazine.fr", "category": "mode", "description": "Magazine masculin"},
    {"name": "L'Officiel", "url": "https://www.lofficiel.com", "category": "mode", "description": "Magazine mode luxe"},
    {"name": "Hypebeast", "url": "https://hypebeast.com/fr", "category": "streetwear", "description": "Streetwear et sneakers"},
    {"name": "Highsnobiety", "url": "https://www.highsnobiety.com", "category": "streetwear", "description": "Street culture"},
    {"name": "Complex France", "url": "https://www.complex.com", "category": "streetwear", "description": "Pop culture et streetwear"},
    {"name": "Grazia", "url": "https://www.grazia.fr", "category": "mode", "description": "Magazine mode"},
    {"name": "Marie Claire", "url": "https://www.marieclaire.fr", "category": "mode", "description": "Magazine féminin"},
    {"name": "Glamour", "url": "https://www.glamour.fr", "category": "mode", "description": "Magazine lifestyle"},
    
    # ==================== ART & EXPOSITIONS ====================
    {"name": "Centre Pompidou", "url": "https://www.centrepompidou.fr", "category": "art", "description": "Art moderne et contemporain"},
    {"name": "Musée du Louvre", "url": "https://www.louvre.fr", "category": "art", "description": "Plus grand musée du monde"},
    {"name": "Musée d'Orsay", "url": "https://www.musee-orsay.fr", "category": "art", "description": "Impressionnisme"},
    {"name": "Grand Palais", "url": "https://www.grandpalais.fr", "category": "art", "description": "Grandes expositions"},
    {"name": "Palais de Tokyo", "url": "https://www.palaisdetokyo.com", "category": "art", "description": "Art contemporain"},
    {"name": "Fondation Louis Vuitton", "url": "https://www.fondationlouisvuitton.fr", "category": "art", "description": "Art contemporain"},
    {"name": "Connaissance des Arts", "url": "https://www.connaissancedesarts.com", "category": "art", "description": "Magazine art"},
    {"name": "Beaux Arts Magazine", "url": "https://www.beauxarts.com", "category": "art", "description": "Magazine art"},
    
    # ==================== THÉÂTRE ====================
    {"name": "Théâtre Online", "url": "https://www.theatreonline.com", "category": "théâtre", "description": "Billetterie théâtre"},
    {"name": "Théâtre de l'Odéon", "url": "https://www.theatre-odeon.eu", "category": "théâtre", "description": "Théâtre national"},
    {"name": "Comédie-Française", "url": "https://www.comedie-francaise.fr", "category": "théâtre", "description": "Théâtre national"},
    {"name": "Opéra de Paris", "url": "https://www.operadeparis.fr", "category": "opéra", "description": "Opéra national"},
    {"name": "Théâtre des Champs-Élysées", "url": "https://www.theatrechampselysees.fr", "category": "théâtre", "description": "Spectacle vivant"},
    {"name": "Châtelet", "url": "https://www.chatelet.com", "category": "théâtre", "description": "Théâtre musical"},
    
    # ==================== SALLES DE CONCERT ====================
    {"name": "Accor Arena Paris", "url": "https://www.accorarenaparis.com", "category": "salle", "description": "Plus grande salle de France"},
    {"name": "L'Olympia", "url": "https://www.olympiahall.com", "category": "salle", "description": "Salle mythique Paris"},
    {"name": "Zénith Paris", "url": "https://www.zenith-paris.com", "category": "salle", "description": "Grande salle Paris"},
    {"name": "Le Bataclan", "url": "https://www.bataclan.fr", "category": "salle", "description": "Salle concerts Paris"},
    {"name": "L'Élysée Montmartre", "url": "https://www.elysee-montmartre.com", "category": "salle", "description": "Salle concerts Paris"},
    {"name": "Salle Pleyel", "url": "https://www.sallepleyel.com", "category": "salle", "description": "Salle classique Paris"},
    {"name": "Philharmonie de Paris", "url": "https://www.philharmoniedeparis.fr", "category": "salle", "description": "Grande salle classique"},
    {"name": "Casino de Paris", "url": "https://www.casinodeparis.fr", "category": "salle", "description": "Salle concerts Paris"},
    {"name": "La Flèche d'Or", "url": "https://www.flechedor.fr", "category": "salle", "description": "Salle concerts Paris"},
    {"name": "Le Trabendo", "url": "https://www.trabendo.fr", "category": "salle", "description": "Salle concerts Paris"},
    {"name": "La Gaîté Lyrique", "url": "https://www.gaite-lyrique.net", "category": "salle", "description": "Arts numériques et musique"},
    {"name": "Le 104", "url": "https://www.104.fr", "category": "salle", "description": "Centre culturel Paris"},
    {"name": "Point Éphémère", "url": "https://www.pointephemere.org", "category": "salle", "description": "Salle alternative Paris"},
    {"name": "Stereolux Nantes", "url": "https://www.stereolux.org", "category": "salle", "description": "Salle concerts Nantes"},
    {"name": "L'Aéronef Lille", "url": "https://www.aeronef.fr", "category": "salle", "description": "Salle concerts Lille"},
    {"name": "Le Transbordeur Lyon", "url": "https://www.transbordeur.fr", "category": "salle", "description": "Salle concerts Lyon"},
    {"name": "Rock School Barbey Bordeaux", "url": "https://www.rockschool-barbey.com", "category": "salle", "description": "Salle concerts Bordeaux"},
    
    # ==================== CLUBS ÉLECTRO ====================
    {"name": "Shotgun", "url": "https://shotgun.live", "category": "électro", "description": "Billetterie événements électro"},
    {"name": "Clubbing France", "url": "https://www.clubbingfrance.com", "category": "électro", "description": "Guide clubbing France"},
    {"name": "Mixmag France", "url": "https://mixmag.fr", "category": "électro", "description": "Magazine DJ/électro"},
    
    # ==================== ÉVÉNEMENTIEL ====================
    {"name": "IRMA", "url": "https://www.irma.asso.fr", "category": "pro", "description": "Centre d'information musique"},
    {"name": "SACEM", "url": "https://www.sacem.fr", "category": "pro", "description": "Droits d'auteur musique"},
    {"name": "CNM", "url": "https://www.cnm.fr", "category": "pro", "description": "Centre National de la Musique"},
    {"name": "ADAMI", "url": "https://www.adami.fr", "category": "pro", "description": "Droits artistes-interprètes"},
    {"name": "Prodiss", "url": "https://www.prodiss.org", "category": "pro", "description": "Syndicat producteurs"},
    {"name": "France Festivals", "url": "https://www.francefestivals.com", "category": "festivals", "description": "Fédération des festivals"},
    
    # ==================== MARCHÉS PUBLICS ====================
    {"name": "BOAMP", "url": "https://www.boamp.fr", "category": "marchés publics", "description": "Bulletin officiel annonces marchés publics"},
    {"name": "Marchés Publics Gouv", "url": "https://www.marches-publics.gouv.fr", "category": "marchés publics", "description": "Plateforme officielle marchés publics"},
    {"name": "Achat Public", "url": "https://www.achatpublic.com", "category": "marchés publics", "description": "Marchés publics France"},
    {"name": "Klekoon", "url": "https://www.klekoon.com", "category": "marchés publics", "description": "Veille marchés publics"},
    
    # ==================== ANNUAIRES PROFESSIONNELS ====================
    {"name": "Société.com", "url": "https://www.societe.com", "category": "annuaire", "description": "Informations entreprises"},
    {"name": "Kompass", "url": "https://www.kompass.com/fr", "category": "annuaire", "description": "Annuaire B2B mondial"},
    {"name": "Pages Jaunes", "url": "https://www.pagesjaunes.fr", "category": "annuaire", "description": "Annuaire professionnel"},
    {"name": "Annuaire Entreprises", "url": "https://annuaire-entreprises.data.gouv.fr", "category": "annuaire", "description": "Annuaire officiel entreprises"},
]


def seed_sources():
    """Ajoute toutes les sources à la base de données"""
    db = next(get_db())
    
    added = 0
    skipped = 0
    
    print(f"\n{'='*60}")
    print(f"🌱 PEUPLEMENT DES SOURCES")
    print(f"{'='*60}\n")
    
    for source_data in SOURCES:
        # Vérifier si la source existe déjà
        existing = db.query(SourceConfig).filter(
            SourceConfig.name == source_data["name"]
        ).first()
        
        if existing:
            print(f"   ⏭️  {source_data['name']} (existe déjà)")
            skipped += 1
            continue
        
        # Créer la source
        source = SourceConfig(
            name=source_data["name"],
            url=source_data["url"],
            description=source_data.get("description", ""),
            source_type=SourceType.HTML,
            is_active=True,
            poll_interval_minutes=360,  # 6 heures
        )
        
        db.add(source)
        print(f"   ✅ {source_data['name']}")
        added += 1
    
    db.commit()
    db.close()
    
    print(f"\n{'='*60}")
    print(f"✅ TERMINÉ: {added} sources ajoutées, {skipped} ignorées")
    print(f"{'='*60}\n")
    
    return added, skipped


if __name__ == "__main__":
    seed_sources()
