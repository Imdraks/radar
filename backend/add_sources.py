#!/usr/bin/env python3
"""
Script d'ajout de sources pour Radar
Plus de 200 sources dans l'industrie musicale
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.source import Source, SourceType

# Sources organisées par catégorie
SOURCES = [
    # ========================================
    # MÉDIAS MUSIQUE FRANCE
    # ========================================
    {"name": "Les Inrockuptibles", "type": "rss", "url": "https://www.lesinrocks.com/feed/", "category": "media_fr"},
    {"name": "Télérama Musique", "type": "rss", "url": "https://www.telerama.fr/rss/musique.xml", "category": "media_fr"},
    {"name": "Libération Musique", "type": "rss", "url": "https://www.liberation.fr/rss/musique/", "category": "media_fr"},
    {"name": "Le Monde Musique", "type": "rss", "url": "https://www.lemonde.fr/musiques/rss_full.xml", "category": "media_fr"},
    {"name": "France Inter Culture", "type": "rss", "url": "https://www.franceinter.fr/rss/culture.xml", "category": "media_fr"},
    {"name": "France Culture Musique", "type": "rss", "url": "https://www.franceculture.fr/rss/musique.xml", "category": "media_fr"},
    {"name": "Tsugi", "type": "rss", "url": "https://www.tsugi.fr/feed/", "category": "media_fr"},
    {"name": "Trax Magazine", "type": "rss", "url": "https://www.traxmag.com/feed/", "category": "media_fr"},
    {"name": "Mouv'", "type": "rss", "url": "https://www.mouv.fr/rss/musique.xml", "category": "media_fr"},
    {"name": "Nova", "type": "rss", "url": "https://www.nova.fr/feed/", "category": "media_fr"},
    {"name": "FIP", "type": "rss", "url": "https://www.fip.fr/rss/actualites.xml", "category": "media_fr"},
    {"name": "Music Actu", "type": "rss", "url": "https://www.music-actu.com/feed/", "category": "media_fr"},
    {"name": "Gonzai", "type": "rss", "url": "https://gonzai.com/feed/", "category": "media_fr"},
    {"name": "Pan European Recording", "type": "rss", "url": "https://pan-european-recording.com/feed/", "category": "media_fr"},
    {"name": "Brain Magazine", "type": "rss", "url": "https://www.brain-magazine.fr/feed", "category": "media_fr"},
    
    # ========================================
    # MÉDIAS MUSIQUE INTERNATIONAL
    # ========================================
    {"name": "Pitchfork", "type": "rss", "url": "https://pitchfork.com/rss/news/", "category": "media_int"},
    {"name": "Pitchfork Reviews", "type": "rss", "url": "https://pitchfork.com/rss/reviews/albums/", "category": "media_int"},
    {"name": "NME", "type": "rss", "url": "https://www.nme.com/music/feed", "category": "media_int"},
    {"name": "Rolling Stone", "type": "rss", "url": "https://www.rollingstone.com/music/feed/", "category": "media_int"},
    {"name": "Billboard", "type": "rss", "url": "https://www.billboard.com/feed/", "category": "media_int"},
    {"name": "Consequence", "type": "rss", "url": "https://consequence.net/feed/", "category": "media_int"},
    {"name": "Stereogum", "type": "rss", "url": "https://www.stereogum.com/feed/", "category": "media_int"},
    {"name": "The Line of Best Fit", "type": "rss", "url": "https://www.thelineofbestfit.com/feed", "category": "media_int"},
    {"name": "DIY Magazine", "type": "rss", "url": "https://diymag.com/feed", "category": "media_int"},
    {"name": "Clash Magazine", "type": "rss", "url": "https://www.clashmusic.com/feed/", "category": "media_int"},
    {"name": "The Quietus", "type": "rss", "url": "https://thequietus.com/feed", "category": "media_int"},
    {"name": "Loud and Quiet", "type": "rss", "url": "https://www.loudandquiet.com/feed/", "category": "media_int"},
    {"name": "The Fader", "type": "rss", "url": "https://www.thefader.com/rss.xml", "category": "media_int"},
    {"name": "Complex Music", "type": "rss", "url": "https://www.complex.com/music/rss", "category": "media_int"},
    {"name": "Hypebeast Music", "type": "rss", "url": "https://hypebeast.com/music/feed", "category": "media_int"},
    {"name": "Highsnobiety Music", "type": "rss", "url": "https://www.highsnobiety.com/music/feed/", "category": "media_int"},
    {"name": "Resident Advisor News", "type": "rss", "url": "https://ra.co/xml/news.xml", "category": "media_int"},
    {"name": "Mixmag", "type": "rss", "url": "https://mixmag.net/feed", "category": "media_int"},
    {"name": "DJ Mag", "type": "rss", "url": "https://djmag.com/feed", "category": "media_int"},
    {"name": "Electronic Beats", "type": "rss", "url": "https://www.electronicbeats.net/feed/", "category": "media_int"},
    {"name": "XLR8R", "type": "rss", "url": "https://xlr8r.com/feed/", "category": "media_int"},
    {"name": "Bandcamp Daily", "type": "rss", "url": "https://daily.bandcamp.com/feed", "category": "media_int"},
    
    # ========================================
    # INDUSTRIE MUSICALE / BUSINESS
    # ========================================
    {"name": "Music Business Worldwide", "type": "rss", "url": "https://www.musicbusinessworldwide.com/feed/", "category": "industry"},
    {"name": "Hypebot", "type": "rss", "url": "https://www.hypebot.com/feed/", "category": "industry"},
    {"name": "Music Ally", "type": "rss", "url": "https://musically.com/feed/", "category": "industry"},
    {"name": "Digital Music News", "type": "rss", "url": "https://www.digitalmusicnews.com/feed/", "category": "industry"},
    {"name": "Music Week", "type": "rss", "url": "https://www.musicweek.com/rss/musicweek/news", "category": "industry"},
    {"name": "Record of the Day", "type": "rss", "url": "https://www.recordoftheday.com/feed", "category": "industry"},
    {"name": "Complete Music Update", "type": "rss", "url": "https://completemusicupdate.com/feed/", "category": "industry"},
    {"name": "IRMA Actus", "type": "rss", "url": "https://www.irma.asso.fr/spip.php?page=backend", "category": "industry"},
    {"name": "CNM Actualités", "type": "rss", "url": "https://cnm.fr/feed/", "category": "industry"},
    {"name": "SNEP Actualités", "type": "rss", "url": "https://snepmusique.com/feed/", "category": "industry"},
    {"name": "UPFI News", "type": "rss", "url": "https://www.upfi.fr/feed/", "category": "industry"},
    {"name": "Audiofanzine Pro", "type": "rss", "url": "https://fr.audiofanzine.com/rss/news.xml", "category": "industry"},
    
    # ========================================
    # FESTIVALS & ÉVÉNEMENTS
    # ========================================
    {"name": "Festival Eurockéennes", "type": "rss", "url": "https://www.eurockeennes.fr/feed/", "category": "festivals"},
    {"name": "Hellfest", "type": "rss", "url": "https://www.hellfest.fr/feed/", "category": "festivals"},
    {"name": "Printemps de Bourges", "type": "rss", "url": "https://www.printemps-bourges.com/feed/", "category": "festivals"},
    {"name": "Francofolies", "type": "rss", "url": "https://www.francofolies.fr/feed/", "category": "festivals"},
    {"name": "Vieilles Charrues", "type": "rss", "url": "https://www.vieillescharrues.asso.fr/feed/", "category": "festivals"},
    {"name": "Solidays", "type": "rss", "url": "https://www.solidays.org/feed/", "category": "festivals"},
    {"name": "Rock en Seine", "type": "rss", "url": "https://www.rockenseine.com/feed/", "category": "festivals"},
    {"name": "Main Square Festival", "type": "rss", "url": "https://www.mainsquarefestival.fr/feed/", "category": "festivals"},
    {"name": "Garorock", "type": "rss", "url": "https://www.garorock.com/feed/", "category": "festivals"},
    {"name": "Musilac", "type": "rss", "url": "https://www.musilac.com/feed/", "category": "festivals"},
    {"name": "Nuits Sonores", "type": "rss", "url": "https://www.nuits-sonores.com/feed/", "category": "festivals"},
    {"name": "Pitchfork Paris", "type": "rss", "url": "https://pitchforkmusicfestival.fr/feed/", "category": "festivals"},
    {"name": "We Love Green", "type": "rss", "url": "https://www.welovegreen.fr/feed/", "category": "festivals"},
    {"name": "Transmusicales", "type": "rss", "url": "https://www.lestrans.com/feed/", "category": "festivals"},
    {"name": "MaMA Festival", "type": "rss", "url": "https://www.mamafestival.com/feed/", "category": "festivals"},
    {"name": "Bise Festival", "type": "rss", "url": "https://www.bisefestival.com/feed/", "category": "festivals"},
    {"name": "Cabaret Vert", "type": "rss", "url": "https://www.cabaretvert.com/feed/", "category": "festivals"},
    {"name": "Papillons de Nuit", "type": "rss", "url": "https://www.papillonsdenuit.com/feed/", "category": "festivals"},
    {"name": "Sziget Festival", "type": "rss", "url": "https://szigetfestival.com/feed/", "category": "festivals"},
    {"name": "Primavera Sound", "type": "rss", "url": "https://www.primaverasound.com/feed/", "category": "festivals"},
    {"name": "Glastonbury", "type": "rss", "url": "https://www.glastonburyfestivals.co.uk/feed/", "category": "festivals"},
    {"name": "Coachella", "type": "rss", "url": "https://www.coachella.com/feed/", "category": "festivals"},
    {"name": "Tomorrowland", "type": "rss", "url": "https://www.tomorrowland.com/feed/", "category": "festivals"},
    {"name": "Sonar Festival", "type": "rss", "url": "https://sonar.es/feed/", "category": "festivals"},
    {"name": "ADE Amsterdam", "type": "rss", "url": "https://www.amsterdam-dance-event.nl/feed/", "category": "festivals"},
    
    # ========================================
    # SALLES DE CONCERT FRANCE
    # ========================================
    {"name": "Olympia Paris", "type": "rss", "url": "https://www.olympiahall.com/feed/", "category": "venues"},
    {"name": "Zénith Paris", "type": "rss", "url": "https://www.zenith-paris.com/feed/", "category": "venues"},
    {"name": "Accor Arena", "type": "rss", "url": "https://www.accorarena.com/feed/", "category": "venues"},
    {"name": "La Cigale", "type": "rss", "url": "https://www.lacigale.fr/feed/", "category": "venues"},
    {"name": "Le Bataclan", "type": "rss", "url": "https://www.bataclan.fr/feed/", "category": "venues"},
    {"name": "L'Élysée Montmartre", "type": "rss", "url": "https://www.elysee-montmartre.com/feed/", "category": "venues"},
    {"name": "La Maroquinerie", "type": "rss", "url": "https://www.lamaroquinerie.fr/feed/", "category": "venues"},
    {"name": "Le Trabendo", "type": "rss", "url": "https://www.letrabendo.net/feed/", "category": "venues"},
    {"name": "La Gaîté Lyrique", "type": "rss", "url": "https://gaite-lyrique.net/feed/", "category": "venues"},
    {"name": "Philharmonie de Paris", "type": "rss", "url": "https://philharmoniedeparis.fr/feed/", "category": "venues"},
    {"name": "Le Transbordeur Lyon", "type": "rss", "url": "https://www.transbordeur.fr/feed/", "category": "venues"},
    {"name": "Le Rocher de Palmer", "type": "rss", "url": "https://lerocherdepalmer.fr/feed/", "category": "venues"},
    {"name": "Stereolux Nantes", "type": "rss", "url": "https://www.stereolux.org/feed/", "category": "venues"},
    {"name": "La Belle Électrique Grenoble", "type": "rss", "url": "https://www.la-belle-electrique.com/feed/", "category": "venues"},
    {"name": "L'Aéronef Lille", "type": "rss", "url": "https://www.aeronef.fr/feed/", "category": "venues"},
    {"name": "Le Krakatoa Bordeaux", "type": "rss", "url": "https://www.krakatoa.org/feed/", "category": "venues"},
    {"name": "Le Bikini Toulouse", "type": "rss", "url": "https://www.lebikini.com/feed/", "category": "venues"},
    {"name": "La Laiterie Strasbourg", "type": "rss", "url": "https://www.artefact.org/feed/", "category": "venues"},
    {"name": "Le Cargö Caen", "type": "rss", "url": "https://www.lecargo.fr/feed/", "category": "venues"},
    {"name": "La Coopérative de Mai", "type": "rss", "url": "https://www.lacoope.org/feed/", "category": "venues"},
    
    # ========================================
    # LABELS INDÉPENDANTS
    # ========================================
    {"name": "Because Music", "type": "rss", "url": "https://www.because.tv/feed/", "category": "labels"},
    {"name": "Wagram Music", "type": "rss", "url": "https://www.wagrammusic.com/feed/", "category": "labels"},
    {"name": "Naïve Records", "type": "rss", "url": "https://www.naive.fr/feed/", "category": "labels"},
    {"name": "Tricatel", "type": "rss", "url": "https://tricatel.com/feed/", "category": "labels"},
    {"name": "Ed Banger Records", "type": "rss", "url": "https://www.edbangerrecords.com/feed/", "category": "labels"},
    {"name": "Bromance Records", "type": "rss", "url": "https://bromancerecords.com/feed/", "category": "labels"},
    {"name": "Roche Musique", "type": "rss", "url": "https://www.rfrmusique.com/feed/", "category": "labels"},
    {"name": "Nowadays Records", "type": "rss", "url": "https://nowadaysrecords.com/feed/", "category": "labels"},
    {"name": "Ninja Tune", "type": "rss", "url": "https://ninjatune.net/feed", "category": "labels"},
    {"name": "Warp Records", "type": "rss", "url": "https://warp.net/feed/", "category": "labels"},
    {"name": "4AD", "type": "rss", "url": "https://4ad.com/feed/", "category": "labels"},
    {"name": "Domino Records", "type": "rss", "url": "https://www.dominomusic.com/feed/", "category": "labels"},
    {"name": "Rough Trade", "type": "rss", "url": "https://www.roughtraderecords.com/feed/", "category": "labels"},
    {"name": "XL Recordings", "type": "rss", "url": "https://xlrecordings.com/feed/", "category": "labels"},
    {"name": "Sub Pop", "type": "rss", "url": "https://www.subpop.com/feed/", "category": "labels"},
    {"name": "Secretly Canadian", "type": "rss", "url": "https://secretlycanadian.com/feed/", "category": "labels"},
    {"name": "Jagjaguwar", "type": "rss", "url": "https://jagjaguwar.com/feed/", "category": "labels"},
    {"name": "Stones Throw", "type": "rss", "url": "https://www.stonesthrow.com/feed/", "category": "labels"},
    {"name": "Brainfeeder", "type": "rss", "url": "https://brainfeedersite.com/feed/", "category": "labels"},
    {"name": "Kompakt", "type": "rss", "url": "https://kompakt.fm/feed/", "category": "labels"},
    {"name": "Innervisions", "type": "rss", "url": "https://www.innervisions.de/feed/", "category": "labels"},
    {"name": "Running Back", "type": "rss", "url": "https://runningback.org/feed/", "category": "labels"},
    {"name": "Beats in Space", "type": "rss", "url": "https://www.beatsinspace.net/feed/", "category": "labels"},
    
    # ========================================
    # RAP / HIP-HOP FR
    # ========================================
    {"name": "Booska-P", "type": "rss", "url": "https://www.booska-p.com/feed/", "category": "hiphop_fr"},
    {"name": "Rapelite", "type": "rss", "url": "https://rapelite.com/feed/", "category": "hiphop_fr"},
    {"name": "Générations", "type": "rss", "url": "https://generations.fr/feed/", "category": "hiphop_fr"},
    {"name": "L'Abcdr du Son", "type": "rss", "url": "https://www.abcdrduson.com/feed/", "category": "hiphop_fr"},
    {"name": "Mouv' Rap FR", "type": "rss", "url": "https://www.mouv.fr/rap-francais/feed/", "category": "hiphop_fr"},
    {"name": "Le Rap en France", "type": "rss", "url": "https://lerapenfrance.fr/feed/", "category": "hiphop_fr"},
    {"name": "SURL Magazine", "type": "rss", "url": "https://surlmag.fr/feed/", "category": "hiphop_fr"},
    {"name": "Yard", "type": "rss", "url": "https://yard.media/feed/", "category": "hiphop_fr"},
    {"name": "Red Bull Music FR", "type": "rss", "url": "https://www.redbull.com/fr-fr/music/feed", "category": "hiphop_fr"},
    {"name": "Trace Urban", "type": "rss", "url": "https://trace.tv/feed/", "category": "hiphop_fr"},
    
    # ========================================
    # APPELS À PROJETS / SUBVENTIONS
    # ========================================
    {"name": "CNM Appels à projets", "type": "rss", "url": "https://cnm.fr/aides/feed/", "category": "funding"},
    {"name": "SACEM Aides", "type": "rss", "url": "https://www.sacem.fr/feed/", "category": "funding"},
    {"name": "ADAMI Aides", "type": "rss", "url": "https://www.adami.fr/feed/", "category": "funding"},
    {"name": "SPEDIDAM Aides", "type": "rss", "url": "https://www.spedidam.fr/feed/", "category": "funding"},
    {"name": "FCM Aides", "type": "rss", "url": "https://www.fcm.fr/feed/", "category": "funding"},
    {"name": "Culture.gouv.fr Musique", "type": "rss", "url": "https://www.culture.gouv.fr/rss/musique", "category": "funding"},
    {"name": "Transfo", "type": "rss", "url": "https://transfo-lemans.fr/feed/", "category": "funding"},
    {"name": "Fair", "type": "rss", "url": "https://www.lefair.org/feed/", "category": "funding"},
    {"name": "Région Île-de-France Culture", "type": "rss", "url": "https://www.iledefrance.fr/culture/feed/", "category": "funding"},
    {"name": "Région Occitanie Culture", "type": "rss", "url": "https://www.laregion.fr/culture/feed/", "category": "funding"},
    {"name": "Région AURA Spectacle", "type": "rss", "url": "https://www.auvergnerhonealpes.fr/culture/feed/", "category": "funding"},
    {"name": "Creative Europe Music", "type": "rss", "url": "https://culture.ec.europa.eu/rss/music", "category": "funding"},
    
    # ========================================
    # TREMPLINS & CONCOURS
    # ========================================
    {"name": "Victoires de la Musique", "type": "rss", "url": "https://www.lesvictoires.com/feed/", "category": "contests"},
    {"name": "Prix Constantin", "type": "rss", "url": "https://www.prixconstantin.com/feed/", "category": "contests"},
    {"name": "Inouïs du Printemps", "type": "rss", "url": "https://www.printemps-bourges.com/inouis/feed/", "category": "contests"},
    {"name": "Chorus des Hauts-de-Seine", "type": "rss", "url": "https://www.chorus.hauts-de-seine.fr/feed/", "category": "contests"},
    {"name": "Buzzcocks", "type": "rss", "url": "https://buzzcocks.fr/feed/", "category": "contests"},
    {"name": "Pépites", "type": "rss", "url": "https://lespepites.com/feed/", "category": "contests"},
    {"name": "Talent Adami", "type": "rss", "url": "https://www.adami.fr/talents/feed/", "category": "contests"},
    
    # ========================================
    # BLOGS & DÉCOUVERTES
    # ========================================
    {"name": "La Blogothèque", "type": "rss", "url": "https://www.blogotheque.net/feed/", "category": "blogs"},
    {"name": "Colors Berlin", "type": "rss", "url": "https://www.colorsxstudios.com/feed/", "category": "blogs"},
    {"name": "KEXP", "type": "rss", "url": "https://www.kexp.org/feed/", "category": "blogs"},
    {"name": "Tiny Desk NPR", "type": "rss", "url": "https://www.npr.org/rss/rss.php?id=152914736", "category": "blogs"},
    {"name": "Indie Shuffle", "type": "rss", "url": "https://www.indieshuffle.com/feed/", "category": "blogs"},
    {"name": "The Burning Ear", "type": "rss", "url": "https://www.theburningear.com/feed/", "category": "blogs"},
    {"name": "Gorilla vs Bear", "type": "rss", "url": "https://www.gorillavsbear.net/feed/", "category": "blogs"},
    {"name": "Pigeons and Planes", "type": "rss", "url": "https://www.complex.com/pigeons-and-planes/feed", "category": "blogs"},
    {"name": "Earmilk", "type": "rss", "url": "https://earmilk.com/feed/", "category": "blogs"},
    {"name": "Hype Machine", "type": "rss", "url": "https://hypem.com/feed/", "category": "blogs"},
    {"name": "The 405", "type": "rss", "url": "https://www.thefourohfive.com/feed/", "category": "blogs"},
    {"name": "Gold Flake Paint", "type": "rss", "url": "https://www.goldflakepaint.co.uk/feed/", "category": "blogs"},
    {"name": "Atwood Magazine", "type": "rss", "url": "https://atwoodmagazine.com/feed/", "category": "blogs"},
    
    # ========================================
    # RADIO & PODCASTS
    # ========================================
    {"name": "France Inter Pop", "type": "rss", "url": "https://www.franceinter.fr/emissions/pop-n-co/rss", "category": "radio"},
    {"name": "RTL2 Pop Rock", "type": "rss", "url": "https://www.rtl2.fr/feed/", "category": "radio"},
    {"name": "OÜI FM", "type": "rss", "url": "https://www.ouifm.fr/feed/", "category": "radio"},
    {"name": "Le Mouv' Playlist", "type": "rss", "url": "https://www.mouv.fr/emissions/mouv-inside/feed", "category": "radio"},
    {"name": "FIP Découvertes", "type": "rss", "url": "https://www.fip.fr/emissions/fip-decouvertes/feed", "category": "radio"},
    {"name": "Radio Meuh", "type": "rss", "url": "https://www.radiomeuh.com/feed/", "category": "radio"},
    {"name": "Rinse France", "type": "rss", "url": "https://rinse.fr/feed/", "category": "radio"},
    {"name": "NTS Radio", "type": "rss", "url": "https://www.nts.live/feed", "category": "radio"},
    {"name": "Boiler Room", "type": "rss", "url": "https://boilerroom.tv/feed/", "category": "radio"},
    {"name": "LeMellotron", "type": "rss", "url": "https://www.lemellotron.com/feed/", "category": "radio"},
    
    # ========================================
    # TECH & STREAMING
    # ========================================
    {"name": "Spotify for Artists Blog", "type": "rss", "url": "https://artists.spotify.com/blog/feed", "category": "tech"},
    {"name": "Apple Music for Artists", "type": "rss", "url": "https://artists.apple.com/feed/", "category": "tech"},
    {"name": "Deezer for Creators", "type": "rss", "url": "https://www.deezer-blog.com/feed/", "category": "tech"},
    {"name": "Bandcamp Blog", "type": "rss", "url": "https://blog.bandcamp.com/feed/", "category": "tech"},
    {"name": "SoundCloud Blog", "type": "rss", "url": "https://blog.soundcloud.com/feed/", "category": "tech"},
    {"name": "DistroKid Blog", "type": "rss", "url": "https://news.distrokid.com/feed/", "category": "tech"},
    {"name": "TuneCore Blog", "type": "rss", "url": "https://www.tunecore.com/blog/feed", "category": "tech"},
    {"name": "CD Baby Blog", "type": "rss", "url": "https://diymusician.cdbaby.com/feed/", "category": "tech"},
    {"name": "Ari's Take", "type": "rss", "url": "https://aristake.com/feed/", "category": "tech"},
    
    # ========================================
    # SYNC & PLACEMENTS
    # ========================================
    {"name": "Music Supervisor", "type": "rss", "url": "https://www.musicsupervisor.com/feed/", "category": "sync"},
    {"name": "Synchtank Blog", "type": "rss", "url": "https://www.synchtank.com/blog/feed/", "category": "sync"},
    {"name": "Production Music Live", "type": "rss", "url": "https://www.productionmusiclive.com/feed/", "category": "sync"},
    {"name": "Musicbed Blog", "type": "rss", "url": "https://www.musicbed.com/blog/feed/", "category": "sync"},
    {"name": "Artlist Blog", "type": "rss", "url": "https://artlist.io/blog/feed/", "category": "sync"},
    {"name": "Epidemic Sound Blog", "type": "rss", "url": "https://www.epidemicsound.com/blog/feed/", "category": "sync"},
    
    # ========================================
    # PRODUCTION & STUDIO
    # ========================================
    {"name": "Sound on Sound", "type": "rss", "url": "https://www.soundonsound.com/rss/news", "category": "production"},
    {"name": "MusicRadar", "type": "rss", "url": "https://www.musicradar.com/rss", "category": "production"},
    {"name": "Attack Magazine", "type": "rss", "url": "https://www.attackmagazine.com/feed/", "category": "production"},
    {"name": "Reverb Machine", "type": "rss", "url": "https://reverbmachine.com/feed/", "category": "production"},
    {"name": "Pro Tools Expert", "type": "rss", "url": "https://www.pro-tools-expert.com/feed/", "category": "production"},
    {"name": "Tape Op", "type": "rss", "url": "https://tapeop.com/feed/", "category": "production"},
    {"name": "Recording Magazine", "type": "rss", "url": "https://www.recordingmag.com/feed/", "category": "production"},
    {"name": "Gearslutz", "type": "rss", "url": "https://gearspace.com/board/external.php?type=RSS2", "category": "production"},
    
    # ========================================
    # BOOKING & TOURNÉES
    # ========================================
    {"name": "Pollstar", "type": "rss", "url": "https://www.pollstar.com/rss/", "category": "booking"},
    {"name": "IQ Magazine", "type": "rss", "url": "https://www.iq-mag.net/feed/", "category": "booking"},
    {"name": "Live Nation Blog", "type": "rss", "url": "https://www.livenation.fr/feed/", "category": "booking"},
    {"name": "Songkick Blog", "type": "rss", "url": "https://blog.songkick.com/feed/", "category": "booking"},
    {"name": "Bandsintown for Artists", "type": "rss", "url": "https://artists.bandsintown.com/feed/", "category": "booking"},
    
    # ========================================
    # JAZZ & CLASSIQUE
    # ========================================
    {"name": "Jazz Magazine", "type": "rss", "url": "https://www.jazzmagazine.com/feed/", "category": "jazz"},
    {"name": "Citizen Jazz", "type": "rss", "url": "https://www.citizenjazz.com/spip.php?page=backend", "category": "jazz"},
    {"name": "Jazz News", "type": "rss", "url": "https://www.jazznews.fr/feed/", "category": "jazz"},
    {"name": "All About Jazz", "type": "rss", "url": "https://www.allaboutjazz.com/rss/feed.xml", "category": "jazz"},
    {"name": "Classica", "type": "rss", "url": "https://www.classica.fr/feed/", "category": "jazz"},
    {"name": "Diapason", "type": "rss", "url": "https://www.diapasonmag.fr/feed/", "category": "jazz"},
    {"name": "ResMusica", "type": "rss", "url": "https://www.resmusica.com/feed/", "category": "jazz"},
    
    # ========================================
    # METAL & ROCK
    # ========================================
    {"name": "Metal France", "type": "rss", "url": "https://www.metalfrance.net/feed/", "category": "metal"},
    {"name": "Metalorgie", "type": "rss", "url": "https://www.metalorgie.com/feed/", "category": "metal"},
    {"name": "Versus Magazine", "type": "rss", "url": "https://www.yourwebsite.fr/feed/", "category": "metal"},
    {"name": "Bloody Blackbird", "type": "rss", "url": "https://www.bloodyblackbird.com/feed/", "category": "metal"},
    {"name": "Metal Hammer", "type": "rss", "url": "https://www.metalhammer.de/feed/", "category": "metal"},
    {"name": "Kerrang!", "type": "rss", "url": "https://www.kerrang.com/feed/", "category": "metal"},
    {"name": "Revolver Magazine", "type": "rss", "url": "https://www.revolvermag.com/rss.xml", "category": "metal"},
    {"name": "Blabbermouth", "type": "rss", "url": "https://www.blabbermouth.net/feed/", "category": "metal"},
    {"name": "Metal Injection", "type": "rss", "url": "https://metalinjection.net/feed", "category": "metal"},
    {"name": "Loudwire", "type": "rss", "url": "https://loudwire.com/feed/", "category": "metal"},
]


def add_sources():
    """Ajoute toutes les sources à la base de données"""
    db: Session = SessionLocal()
    
    added = 0
    skipped = 0
    errors = 0
    
    try:
        for source_data in SOURCES:
            try:
                # Vérifier si la source existe déjà
                existing = db.query(Source).filter(
                    Source.url == source_data["url"]
                ).first()
                
                if existing:
                    skipped += 1
                    print(f"⏭️  Skip (existe): {source_data['name']}")
                    continue
                
                # Créer la source
                source = Source(
                    name=source_data["name"],
                    source_type=SourceType(source_data["type"]),
                    url=source_data["url"],
                    category=source_data.get("category", "other"),
                    is_active=True,
                    priority=1,
                    config={}
                )
                
                db.add(source)
                db.commit()
                added += 1
                print(f"✅ Ajouté: {source_data['name']}")
                
            except Exception as e:
                db.rollback()
                errors += 1
                print(f"❌ Erreur ({source_data['name']}): {e}")
                continue
        
        print("\n" + "="*50)
        print(f"📊 RÉSUMÉ:")
        print(f"   ✅ Ajoutées: {added}")
        print(f"   ⏭️  Skippées: {skipped}")
        print(f"   ❌ Erreurs: {errors}")
        print(f"   📁 Total sources: {db.query(Source).count()}")
        print("="*50)
        
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Ajout des sources Radar...")
    print(f"📋 {len(SOURCES)} sources à traiter\n")
    add_sources()
