"""
Map & Calendar API for Opportunities
Geographic visualization, artist events map, and calendar export
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
logger = logging.getLogger(__name__)
import json
import hashlib
import random as stdlib_random

from app.db import get_db
from app.db.models.user import User
from app.db.models.opportunity import Opportunity, OpportunityStatus
from app.api.deps import get_current_user, get_user_workspace_id
from app.core.cache import cache_get, cache_set

router = APIRouter(prefix="/map", tags=["map"])

CACHE_TTL = 300  # 5 minutes

# French regions with approximate center coordinates
REGION_COORDS = {
    # Régions métropolitaines
    "ile-de-france": {"lat": 48.8566, "lng": 2.3522, "name": "Île-de-France"},
    "ile de france": {"lat": 48.8566, "lng": 2.3522, "name": "Île-de-France"},
    "paris": {"lat": 48.8566, "lng": 2.3522, "name": "Paris"},
    "auvergne-rhone-alpes": {"lat": 45.7640, "lng": 4.8357, "name": "Auvergne-Rhône-Alpes"},
    "auvergne rhone alpes": {"lat": 45.7640, "lng": 4.8357, "name": "Auvergne-Rhône-Alpes"},
    "rhone-alpes": {"lat": 45.7640, "lng": 4.8357, "name": "Rhône-Alpes"},
    "lyon": {"lat": 45.7640, "lng": 4.8357, "name": "Lyon"},
    "nouvelle-aquitaine": {"lat": 44.8378, "lng": -0.5792, "name": "Nouvelle-Aquitaine"},
    "nouvelle aquitaine": {"lat": 44.8378, "lng": -0.5792, "name": "Nouvelle-Aquitaine"},
    "bordeaux": {"lat": 44.8378, "lng": -0.5792, "name": "Bordeaux"},
    "occitanie": {"lat": 43.6047, "lng": 1.4442, "name": "Occitanie"},
    "toulouse": {"lat": 43.6047, "lng": 1.4442, "name": "Toulouse"},
    "montpellier": {"lat": 43.6108, "lng": 3.8767, "name": "Montpellier"},
    "provence-alpes-cote-d-azur": {"lat": 43.2965, "lng": 5.3698, "name": "PACA"},
    "paca": {"lat": 43.2965, "lng": 5.3698, "name": "PACA"},
    "provence": {"lat": 43.2965, "lng": 5.3698, "name": "Provence"},
    "marseille": {"lat": 43.2965, "lng": 5.3698, "name": "Marseille"},
    "nice": {"lat": 43.7102, "lng": 7.2620, "name": "Nice"},
    "hauts-de-france": {"lat": 49.8941, "lng": 2.2958, "name": "Hauts-de-France"},
    "hauts de france": {"lat": 49.8941, "lng": 2.2958, "name": "Hauts-de-France"},
    "lille": {"lat": 50.6292, "lng": 3.0573, "name": "Lille"},
    "grand-est": {"lat": 48.5734, "lng": 7.7521, "name": "Grand Est"},
    "grand est": {"lat": 48.5734, "lng": 7.7521, "name": "Grand Est"},
    "strasbourg": {"lat": 48.5734, "lng": 7.7521, "name": "Strasbourg"},
    "bretagne": {"lat": 48.1173, "lng": -1.6778, "name": "Bretagne"},
    "rennes": {"lat": 48.1173, "lng": -1.6778, "name": "Rennes"},
    "brest": {"lat": 48.3904, "lng": -4.4861, "name": "Brest"},
    "normandie": {"lat": 49.1829, "lng": -0.3707, "name": "Normandie"},
    "caen": {"lat": 49.1829, "lng": -0.3707, "name": "Caen"},
    "rouen": {"lat": 49.4432, "lng": 1.0993, "name": "Rouen"},
    "pays-de-la-loire": {"lat": 47.2184, "lng": -1.5536, "name": "Pays de la Loire"},
    "pays de la loire": {"lat": 47.2184, "lng": -1.5536, "name": "Pays de la Loire"},
    "nantes": {"lat": 47.2184, "lng": -1.5536, "name": "Nantes"},
    "centre-val-de-loire": {"lat": 47.9029, "lng": 1.9039, "name": "Centre-Val de Loire"},
    "centre": {"lat": 47.9029, "lng": 1.9039, "name": "Centre"},
    "orleans": {"lat": 47.9029, "lng": 1.9039, "name": "Orléans"},
    "tours": {"lat": 47.3941, "lng": 0.6848, "name": "Tours"},
    "bourgogne-franche-comte": {"lat": 47.3220, "lng": 5.0415, "name": "Bourgogne-Franche-Comté"},
    "bourgogne": {"lat": 47.3220, "lng": 5.0415, "name": "Bourgogne"},
    "dijon": {"lat": 47.3220, "lng": 5.0415, "name": "Dijon"},
    "corse": {"lat": 42.0396, "lng": 9.0129, "name": "Corse"},
    "ajaccio": {"lat": 41.9192, "lng": 8.7386, "name": "Ajaccio"},
    # DOM-TOM
    "guadeloupe": {"lat": 16.2650, "lng": -61.5510, "name": "Guadeloupe"},
    "martinique": {"lat": 14.6415, "lng": -61.0242, "name": "Martinique"},
    "guyane": {"lat": 4.9372, "lng": -52.3260, "name": "Guyane"},
    "reunion": {"lat": -21.1151, "lng": 55.5364, "name": "Réunion"},
    "la reunion": {"lat": -21.1151, "lng": 55.5364, "name": "Réunion"},
    "mayotte": {"lat": -12.8275, "lng": 45.1662, "name": "Mayotte"},
    # Autres pays courants
    "belgique": {"lat": 50.8503, "lng": 4.3517, "name": "Belgique"},
    "suisse": {"lat": 46.8182, "lng": 8.2275, "name": "Suisse"},
    "luxembourg": {"lat": 49.6117, "lng": 6.1319, "name": "Luxembourg"},
    "monaco": {"lat": 43.7384, "lng": 7.4246, "name": "Monaco"},
    # Venues / cities commonly returned by Ticketmaster
    "saint denis": {"lat": 48.9362, "lng": 2.3574, "name": "Saint-Denis"},
    "saint-denis": {"lat": 48.9362, "lng": 2.3574, "name": "Saint-Denis"},
    "nanterre": {"lat": 48.8924, "lng": 2.2071, "name": "Nanterre"},
    "la defense": {"lat": 48.8918, "lng": 2.2380, "name": "La Défense"},
    "la défense": {"lat": 48.8918, "lng": 2.2380, "name": "La Défense"},
    "bercy": {"lat": 48.8386, "lng": 2.3786, "name": "Bercy"},
    "villeurbanne": {"lat": 45.7716, "lng": 4.8902, "name": "Villeurbanne"},
    "decines": {"lat": 45.7695, "lng": 4.9570, "name": "Décines"},
    "décines": {"lat": 45.7695, "lng": 4.9570, "name": "Décines"},
    "puteaux": {"lat": 48.8845, "lng": 2.2392, "name": "Puteaux"},
    "aix-en-provence": {"lat": 43.5297, "lng": 5.4474, "name": "Aix-en-Provence"},
    "clermont-ferrand": {"lat": 45.7772, "lng": 3.0870, "name": "Clermont-Ferrand"},
    "metz": {"lat": 49.1193, "lng": 6.1757, "name": "Metz"},
    "nancy": {"lat": 48.6921, "lng": 6.1844, "name": "Nancy"},
    "angers": {"lat": 47.4784, "lng": -0.5632, "name": "Angers"},
    "grenoble": {"lat": 45.1885, "lng": 5.7245, "name": "Grenoble"},
    "toulon": {"lat": 43.1242, "lng": 5.9280, "name": "Toulon"},
    "le mans": {"lat": 48.0061, "lng": 0.1996, "name": "Le Mans"},
    "reims": {"lat": 49.2583, "lng": 4.0317, "name": "Reims"},
    "saint-etienne": {"lat": 45.4397, "lng": 4.3872, "name": "Saint-Étienne"},
    "perpignan": {"lat": 42.6887, "lng": 2.8948, "name": "Perpignan"},
    "limoges": {"lat": 45.8315, "lng": 1.2578, "name": "Limoges"},
    "amiens": {"lat": 49.8941, "lng": 2.2958, "name": "Amiens"},
    "besancon": {"lat": 47.2378, "lng": 6.0241, "name": "Besançon"},
    "pau": {"lat": 43.2951, "lng": -0.3708, "name": "Pau"},
    "la rochelle": {"lat": 46.1603, "lng": -1.1511, "name": "La Rochelle"},
    "avignon": {"lat": 43.9493, "lng": 4.8055, "name": "Avignon"},
    "le havre": {"lat": 49.4944, "lng": 0.1079, "name": "Le Havre"},
    "cannes": {"lat": 43.5513, "lng": 7.0128, "name": "Cannes"},
    # National
    "france": {"lat": 46.2276, "lng": 2.2137, "name": "France"},
    "national": {"lat": 46.2276, "lng": 2.2137, "name": "National"},
}


def get_coordinates_for_location(location: str) -> Optional[Dict[str, Any]]:
    """Get coordinates for a location string"""
    if not location:
        return None
    
    location_lower = location.lower().strip()
    
    # Direct match
    if location_lower in REGION_COORDS:
        return REGION_COORDS[location_lower]
    
    # Partial match
    for key, coords in REGION_COORDS.items():
        if key in location_lower or location_lower in key:
            return coords
    
    return None


# ============================================================================
# MAP ENDPOINTS
# ============================================================================

@router.get("/opportunities")
def get_map_opportunities(
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get opportunities with geographic coordinates for map display"""
    cache_key = f"map:opps:{current_user.id}:{db.info.get('workspace_id')}:{status}:{category}:{min_score}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    query = db.query(Opportunity)
    
    # Filters
    if status:
        try:
            status_enum = OpportunityStatus(status)
            query = query.filter(Opportunity.status == status_enum)
        except ValueError:
            pass
    
    if min_score:
        query = query.filter(Opportunity.score >= min_score)
    
    # Exclude closed opportunities
    query = query.filter(
        Opportunity.status.notin_([
            OpportunityStatus.CANCELLED
        ])
    )
    
    opportunities = query.limit(500).all()
    
    # Group by location
    markers = []
    clusters = {}  # Group by region for clustering
    
    for opp in opportunities:
        location = opp.location_region or opp.location_city
        coords = get_coordinates_for_location(location)
        
        if coords:
            # Add some jitter to avoid exact overlaps
            import random
            jitter_lat = (random.random() - 0.5) * 0.1
            jitter_lng = (random.random() - 0.5) * 0.1
            
            marker = {
                "id": opp.id,
                "title": opp.title[:80] if opp.title else "Sans titre",
                "lat": coords["lat"] + jitter_lat,
                "lng": coords["lng"] + jitter_lng,
                "score": opp.score or 0,
                "status": opp.status.value if opp.status else "new",
                "category": opp.category.value if opp.category else None,
                "budget": float(opp.budget_amount) if opp.budget_amount else None,
                "deadline": opp.deadline_at.isoformat() if opp.deadline_at else None,
                "organization": opp.organization,
                "region": coords["name"]
            }
            markers.append(marker)
            
            # Cluster tracking
            region_name = coords["name"]
            if region_name not in clusters:
                clusters[region_name] = {
                    "name": region_name,
                    "lat": coords["lat"],
                    "lng": coords["lng"],
                    "count": 0,
                    "total_value": 0
                }
            clusters[region_name]["count"] += 1
            if opp.budget_amount:
                clusters[region_name]["total_value"] += float(opp.budget_amount)
    
    result = {
        "markers": markers,
        "clusters": list(clusters.values()),
        "total": len(markers),
        "center": {"lat": 46.2276, "lng": 2.2137},  # France center
        "zoom": 6
    }
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


@router.get("/regions/stats")
def get_region_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get statistics per region"""
    cache_key = f"map:regions:{current_user.id}:{db.info.get('workspace_id')}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    opportunities = db.query(Opportunity).filter(
        Opportunity.status.notin_([OpportunityStatus.CANCELLED])
    ).all()
    
    regions = {}
    for opp in opportunities:
        location = opp.location_region or opp.location_city
        coords = get_coordinates_for_location(location)
        
        if coords:
            region = coords["name"]
            if region not in regions:
                regions[region] = {
                    "name": region,
                    "lat": coords["lat"],
                    "lng": coords["lng"],
                    "count": 0,
                    "won": 0,
                    "total_value": 0,
                    "avg_score": []
                }
            
            regions[region]["count"] += 1
            if opp.status == OpportunityStatus.WON:
                regions[region]["won"] += 1
            if opp.budget_amount:
                regions[region]["total_value"] += float(opp.budget_amount)
            if opp.score:
                regions[region]["avg_score"].append(opp.score)
    
    result = []
    for region_data in regions.values():
        scores = region_data.pop("avg_score")
        region_data["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        region_data["total_value"] = round(region_data["total_value"], 2)
        result.append(region_data)
    
    result.sort(key=lambda x: x["count"], reverse=True)
    
    cache_set(cache_key, result, CACHE_TTL)
    return result


# ============================================================================
# ARTIST EVENTS MAP
# ============================================================================

# French cities with venues for event generation
FRENCH_VENUES = [
    # Paris & IDF
    {"city": "Paris", "lat": 48.8566, "lng": 2.3522, "venues": [
        {"name": "Accor Arena", "type": "concert", "capacity": 20300},
        {"name": "Olympia", "type": "concert", "capacity": 2000},
        {"name": "Zénith de Paris", "type": "concert", "capacity": 6293},
        {"name": "Stade de France", "type": "concert", "capacity": 80000},
        {"name": "La Cigale", "type": "concert", "capacity": 1400},
        {"name": "Le Bataclan", "type": "concert", "capacity": 1500},
        {"name": "Élysée Montmartre", "type": "concert", "capacity": 1500},
        {"name": "Fondation Louis Vuitton", "type": "brand_event", "capacity": 1000},
        {"name": "Palais de Tokyo", "type": "popup_store", "capacity": 500},
        {"name": "Grand Palais", "type": "brand_event", "capacity": 5000},
        {"name": "Le Marais Pop-Up", "type": "popup_store", "capacity": 200},
        {"name": "Galeries Lafayette Haussmann", "type": "popup_store", "capacity": 300},
    ]},
    # Lyon
    {"city": "Lyon", "lat": 45.7640, "lng": 4.8357, "venues": [
        {"name": "LDLC Arena", "type": "concert", "capacity": 16000},
        {"name": "Le Transbordeur", "type": "concert", "capacity": 1800},
        {"name": "Nuits de Fourvière", "type": "festival", "capacity": 8000},
        {"name": "Nuits Sonores", "type": "festival", "capacity": 60000},
        {"name": "Confluence Pop-Up", "type": "popup_store", "capacity": 150},
    ]},
    # Marseille
    {"city": "Marseille", "lat": 43.2965, "lng": 5.3698, "venues": [
        {"name": "Orange Vélodrome", "type": "concert", "capacity": 67394},
        {"name": "Le Dôme", "type": "concert", "capacity": 8500},
        {"name": "Le Moulin", "type": "concert", "capacity": 800},
        {"name": "Fiesta des Suds", "type": "festival", "capacity": 20000},
        {"name": "Terrasses du Port Pop-Up", "type": "popup_store", "capacity": 200},
    ]},
    # Bordeaux
    {"city": "Bordeaux", "lat": 44.8378, "lng": -0.5792, "venues": [
        {"name": "Arkéa Arena", "type": "concert", "capacity": 11300},
        {"name": "Le Rocher de Palmer", "type": "concert", "capacity": 1200},
        {"name": "Les Nuits Atypiques", "type": "festival", "capacity": 5000},
        {"name": "Relache Festival", "type": "festival", "capacity": 8000},
    ]},
    # Toulouse
    {"city": "Toulouse", "lat": 43.6047, "lng": 1.4442, "venues": [
        {"name": "Zénith de Toulouse", "type": "concert", "capacity": 9000},
        {"name": "Le Bikini", "type": "concert", "capacity": 1500},
        {"name": "Rio Loco", "type": "festival", "capacity": 15000},
    ]},
    # Lille
    {"city": "Lille", "lat": 50.6292, "lng": 3.0573, "venues": [
        {"name": "Zénith de Lille", "type": "concert", "capacity": 7200},
        {"name": "L'Aéronef", "type": "concert", "capacity": 2200},
        {"name": "Série Série", "type": "festival", "capacity": 10000},
    ]},
    # Nantes
    {"city": "Nantes", "lat": 47.2184, "lng": -1.5536, "venues": [
        {"name": "Zénith Nantes Métropole", "type": "concert", "capacity": 9000},
        {"name": "Stereolux", "type": "concert", "capacity": 1200},
        {"name": "Hellfest", "type": "festival", "capacity": 60000},
    ]},
    # Strasbourg
    {"city": "Strasbourg", "lat": 48.5734, "lng": 7.7521, "venues": [
        {"name": "Zénith de Strasbourg", "type": "concert", "capacity": 12079},
        {"name": "La Laiterie", "type": "concert", "capacity": 900},
        {"name": "Ososphère", "type": "festival", "capacity": 8000},
    ]},
    # Nice
    {"city": "Nice", "lat": 43.7102, "lng": 7.2620, "venues": [
        {"name": "Palais Nikaïa", "type": "concert", "capacity": 6000},
        {"name": "Nice Jazz Festival", "type": "festival", "capacity": 35000},
        {"name": "Promenade des Anglais Pop-Up", "type": "popup_store", "capacity": 150},
    ]},
    # Montpellier
    {"city": "Montpellier", "lat": 43.6108, "lng": 3.8767, "venues": [
        {"name": "Sud de France Arena", "type": "concert", "capacity": 14800},
        {"name": "Le Rockstore", "type": "concert", "capacity": 700},
        {"name": "Les Internationales de la Guitare", "type": "festival", "capacity": 5000},
    ]},
    # Rennes
    {"city": "Rennes", "lat": 48.1173, "lng": -1.6778, "venues": [
        {"name": "Le Liberté", "type": "concert", "capacity": 3000},
        {"name": "Trans Musicales", "type": "festival", "capacity": 60000},
    ]},
    # Festivals majeurs
    {"city": "Carhaix", "lat": 48.2759, "lng": -3.5714, "venues": [
        {"name": "Vieilles Charrues", "type": "festival", "capacity": 55000},
    ]},
    {"city": "Belfort", "lat": 47.6400, "lng": 6.8497, "venues": [
        {"name": "Eurockéennes", "type": "festival", "capacity": 30000},
    ]},
    {"city": "Arles", "lat": 43.6767, "lng": 4.6278, "venues": [
        {"name": "Les Rencontres d'Arles", "type": "brand_event", "capacity": 5000},
    ]},
    {"city": "La Rochelle", "lat": 46.1591, "lng": -1.1520, "venues": [
        {"name": "Francofolies", "type": "festival", "capacity": 80000},
    ]},
    {"city": "Aix-en-Provence", "lat": 43.5297, "lng": 5.4474, "venues": [
        {"name": "Festival d'Aix", "type": "festival", "capacity": 10000},
    ]},
    {"city": "Cannes", "lat": 43.5528, "lng": 7.0174, "venues": [
        {"name": "Palais des Festivals", "type": "brand_event", "capacity": 2300},
        {"name": "Croisette Pop-Up", "type": "popup_store", "capacity": 200},
    ]},
]

EVENT_TYPE_LABELS = {
    "concert": "Concert",
    "festival": "Festival",
    "popup_store": "Pop-up Store",
    "brand_event": "Événement de marque",
}


def _generate_deterministic_events(artists: list, workspace_id: str) -> List[Dict[str, Any]]:
    """Generate deterministic events from discovered artists.
    Uses artist+venue hash as seed for reproducible results."""
    events = []
    now = datetime.utcnow()
    
    for artist in artists:
        artist_name = artist.get("name", "Artiste")
        artist_id = artist.get("id", "")
        genres = artist.get("genres", [])
        image_url = artist.get("image_url")
        score = artist.get("score", 50)
        monthly_listeners = artist.get("monthly_listeners", 0)
        
        # Deterministic seed based on artist
        seed_str = f"{workspace_id}:{artist_id}:{artist_name}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = stdlib_random.Random(seed)
        
        # Number of events depends on artist popularity
        if score >= 80 or monthly_listeners >= 1000000:
            num_events = rng.randint(4, 8)
        elif score >= 60 or monthly_listeners >= 100000:
            num_events = rng.randint(2, 5)
        elif score >= 40:
            num_events = rng.randint(1, 3)
        else:
            num_events = rng.randint(0, 2)
        
        if num_events == 0:
            continue
        
        # Pick random venues
        all_venues = []
        for city_data in FRENCH_VENUES:
            for venue in city_data["venues"]:
                all_venues.append({
                    **venue,
                    "city": city_data["city"],
                    "lat": city_data["lat"],
                    "lng": city_data["lng"],
                })
        
        selected_venues = rng.sample(all_venues, min(num_events, len(all_venues)))
        
        for venue in selected_venues:
            # Generate a date in next 6 months
            days_ahead = rng.randint(1, 180)
            event_date = now + timedelta(days=days_ahead)
            
            # Add small jitter to coordinates to avoid exact overlap
            jitter_lat = (rng.random() - 0.5) * 0.02
            jitter_lng = (rng.random() - 0.5) * 0.02
            
            # Price range based on venue capacity and artist score
            base = venue.get("capacity", 1000)
            if base > 10000:
                price_min = rng.randint(35, 65)
                price_max = rng.randint(80, 180)
            elif base > 2000:
                price_min = rng.randint(25, 40)
                price_max = rng.randint(50, 95)
            else:
                price_min = rng.randint(15, 30)
                price_max = rng.randint(35, 60)
            
            event_id = hashlib.md5(f"{artist_id}:{venue['name']}:{event_date.date()}".encode()).hexdigest()[:12]
            
            events.append({
                "id": event_id,
                "artist_name": artist_name,
                "artist_id": str(artist_id),
                "artist_image": image_url,
                "artist_score": score,
                "artist_genres": genres[:3] if genres else [],
                "monthly_listeners": monthly_listeners,
                "event_type": venue["type"],
                "event_type_label": EVENT_TYPE_LABELS.get(venue["type"], venue["type"]),
                "venue": venue["name"],
                "city": venue["city"],
                "lat": venue["lat"] + jitter_lat,
                "lng": venue["lng"] + jitter_lng,
                "date": event_date.isoformat(),
                "date_label": event_date.strftime("%d %b %Y"),
                "capacity": venue.get("capacity"),
                "price_min": price_min,
                "price_max": price_max,
            })
    
    events.sort(key=lambda e: e["date"])
    return events


@router.get("/artist-events")
def get_artist_events(
    event_type: Optional[str] = Query(None, description="Filter by: concert, festival, popup_store, brand_event"),
    city: Optional[str] = Query(None, description="Filter by city"),
    artist: Optional[str] = Query(None, description="Filter by artist name (partial match)"),
    date_from: Optional[str] = Query(None, description="ISO date start filter"),
    date_to: Optional[str] = Query(None, description="ISO date end filter"),
    score_min: Optional[int] = Query(None, description="Minimum artist score (0-100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
) -> Dict[str, Any]:
    """Get artist events for the map.
    Returns collected events only. Missing data never generates fictitious events."""

    cache_key = f"map:verified-artist-events:{workspace_id}:{event_type}:{city}:{artist}:{date_from}:{date_to}:{score_min}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # ---- Try real events from artist_events table first ----
    try:
        from app.db.models.artist_event import ArtistEvent

        q = db.query(ArtistEvent).filter(
            ArtistEvent.workspace_id == workspace_id,
            ArtistEvent.is_deleted == False,
        )

        if event_type:
            q = q.filter(ArtistEvent.event_type == event_type)
        if city:
            q = q.filter(ArtistEvent.city.ilike(f"%{city}%"))
        if artist:
            q = q.filter(ArtistEvent.artist_name.ilike(f"%{artist}%"))
        if date_from:
            q = q.filter(ArtistEvent.event_date >= date_from)
        if date_to:
            q = q.filter(ArtistEvent.event_date <= date_to)

        if score_min is not None:
            q = q.filter(ArtistEvent.artist_score >= score_min)

        q = q.order_by(ArtistEvent.event_date.asc()).limit(500)
        rows = q.all()

        if rows:
            # Real events exist — use them
            filtered = [r.to_map_dict() for r in rows]

            # Enrich with fee estimates & contact status from discovery tables
            try:
                from app.db.models.discovery import DiscoveryArtist as DA, DiscoveryComputedMetrics as DCM
                artist_ids = list({r.artist_id for r in rows if r.artist_id})
                if artist_ids:
                    enrichment_rows = (
                        db.query(
                            DA.id,
                            DCM.fee_estimate_min,
                            DCM.fee_estimate_max,
                            DA.instagram_url,
                            DA.spotify_artist_id,
                        )
                        .outerjoin(DCM, DA.id == DCM.artist_id)
                        .filter(DA.id.in_(artist_ids))
                        .all()
                    )
                    enrichment_map = {
                        str(r.id): {
                            "fee_estimate_min": int(r.fee_estimate_min) if r.fee_estimate_min else None,
                            "fee_estimate_max": int(r.fee_estimate_max) if r.fee_estimate_max else None,
                            "has_contact": bool(r.instagram_url or r.spotify_artist_id),
                        }
                        for r in enrichment_rows
                    }
                    for ev in filtered:
                        aid = ev.get("artist_id")
                        if aid and aid in enrichment_map:
                            ev.update(enrichment_map[aid])
                        else:
                            ev["fee_estimate_min"] = None
                            ev["fee_estimate_max"] = None
                            ev["has_contact"] = False
                else:
                    for ev in filtered:
                        ev["fee_estimate_min"] = None
                        ev["fee_estimate_max"] = None
                        ev["has_contact"] = False
            except Exception:
                for ev in filtered:
                    ev["fee_estimate_min"] = None
                    ev["fee_estimate_max"] = None
                    ev["has_contact"] = False

            # Also get all cities for the filter dropdown
            all_cities_q = (
                db.query(ArtistEvent.city)
                .filter(ArtistEvent.workspace_id == workspace_id, ArtistEvent.is_deleted == False)
                .distinct()
            )
            cities = sorted([c[0] for c in all_cities_q.all() if c[0]])

            type_counts = {}
            city_counts = {}
            for e in filtered:
                t = e["event_type"]
                type_counts[t] = type_counts.get(t, 0) + 1
                c = e.get("city", "")
                if c:
                    city_counts[c] = city_counts.get(c, 0) + 1

            result = {
                "events": filtered,
                "total": len(filtered),
                "stats": {
                    "by_type": type_counts,
                    "by_city": city_counts,
                    "total_artists": len(set(e["artist_name"] for e in filtered)),
                },
                "cities": cities,
                "source": "ticketmaster+bandsintown",
            }
            cache_set(cache_key, result, 120)
            return result
    except Exception as exc:
        logger.exception("Artist event retrieval failed")
        raise HTTPException(status_code=503, detail="Impossible de charger les événements vérifiés") from exc
    return {"events": [], "stats": {}, "cities": [], "total": 0, "source": "no_collected_events"}


@router.post("/sync-events")
def trigger_event_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace_id: int = Depends(get_user_workspace_id),
) -> Dict[str, Any]:
    """Manually trigger a Ticketmaster event sync for the current workspace."""
    from app.core.config import settings as _settings
    if not _settings.ticketmaster_api_key:
        return {"status": "error", "message": "TICKETMASTER_API_KEY not configured"}

    from app.workers.event_sync_tasks import sync_artist_events
    task = sync_artist_events.delay(workspace_id=workspace_id)
    return {"status": "queued", "task_id": str(task.id)}


# ============================================================================
# CALENDAR ENDPOINTS
# ============================================================================

calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])


@calendar_router.get("/ical")
def get_ical_feed(
    token: str = Query(..., description="User API token"),
    db: Session = Depends(get_db),
) -> Response:
    """
    Generate iCal feed for deadlines
    Subscribe to this URL in Google Calendar, Outlook, etc.
    """
    # Validate token and get user
    from app.core.security import decode_token
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return Response(content="Invalid token", status_code=401)
    except Exception:
        return Response(content="Invalid token", status_code=401)
    
    # Get opportunities with deadlines
    now = datetime.utcnow()
    opportunities = db.query(Opportunity).filter(
        and_(
            Opportunity.deadline_at.isnot(None),
            Opportunity.deadline_at >= now,
            Opportunity.status.notin_([
                OpportunityStatus.WON,
                OpportunityStatus.LOST,
                OpportunityStatus.CANCELLED
            ])
        )
    ).order_by(Opportunity.deadline_at).limit(100).all()
    
    # Build iCal content
    ical_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Radar//Opportunities Calendar//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Radar Deadlines",
        "X-WR-TIMEZONE:Europe/Paris",
    ]
    
    for opp in opportunities:
        uid = f"opp-{opp.id}@radar.app"
        dtstart = opp.deadline_at.strftime("%Y%m%d")
        dtend = (opp.deadline_at + timedelta(days=1)).strftime("%Y%m%d")
        created = opp.created_at.strftime("%Y%m%dT%H%M%SZ") if opp.created_at else now.strftime("%Y%m%dT%H%M%SZ")
        
        summary = f"[Deadline] {opp.title[:50]}" if opp.title else "[Deadline] Opportunité"
        description = []
        if opp.organization:
            description.append(f"Organisation: {opp.organization}")
        if opp.budget_amount:
            description.append(f"Budget: {opp.budget_amount}€")
        if opp.score:
            description.append(f"Score: {opp.score}")
        description.append(f"\\nVoir: https://radarapp.fr/leads/{opp.id}")
        
        ical_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"DTSTAMP:{created}",
            f"CREATED:{created}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{' | '.join(description)}",
            "STATUS:CONFIRMED",
            "TRANSP:TRANSPARENT",
            # Add reminder 1 day before
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Deadline demain!",
            "TRIGGER:-P1D",
            "END:VALARM",
            # Add reminder 1 week before
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Deadline dans 7 jours",
            "TRIGGER:-P7D",
            "END:VALARM",
            "END:VEVENT",
        ])
    
    ical_lines.append("END:VCALENDAR")
    
    content = "\r\n".join(ical_lines)
    
    return Response(
        content=content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": "attachment; filename=radar-deadlines.ics"
        }
    )


@calendar_router.get("/events")
def get_calendar_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get events for calendar view (FullCalendar format)"""
    query = db.query(Opportunity).filter(
        Opportunity.deadline_at.isnot(None)
    )
    
    if start:
        try:
            start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
            query = query.filter(Opportunity.deadline_at >= start_date)
        except ValueError:
            pass
    
    if end:
        try:
            end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
            query = query.filter(Opportunity.deadline_at <= end_date)
        except ValueError:
            pass
    
    opportunities = query.order_by(Opportunity.deadline_at).all()
    
    events = []
    for opp in opportunities:
        # Color based on status
        color = "#3B82F6"  # blue default
        if opp.status == OpportunityStatus.WON:
            color = "#10B981"  # green
        elif opp.status == OpportunityStatus.LOST:
            color = "#EF4444"  # red
        elif opp.status == OpportunityStatus.IN_PROGRESS:
            color = "#F59E0B"  # amber
        elif opp.score and opp.score >= 70:
            color = "#8B5CF6"  # purple for high score
        
        events.append({
            "id": str(opp.id),
            "title": opp.title[:40] if opp.title else "Opportunité",
            "start": opp.deadline_at.isoformat(),
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {
                "opportunityId": opp.id,
                "score": opp.score,
                "status": opp.status.value if opp.status else None,
                "budget": float(opp.budget_amount) if opp.budget_amount else None,
                "organization": opp.organization
            }
        })
    
    return events


@calendar_router.get("/subscription-url")
def get_subscription_url(
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Get the iCal subscription URL for this user"""
    from app.core.security import create_access_token
    
    # Create a long-lived token for calendar subscription
    token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=timedelta(days=365)
    )
    
    return {
        "url": f"https://radarapp.fr/api/v1/calendar/ical?token={token}",
        "instructions": "Copiez cette URL et ajoutez-la comme calendrier externe dans Google Calendar ou Outlook"
    }
