"""Official product catalog and entitlements. Legacy packs are read-only compatibility identifiers."""
from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field


# ============================================================================
# PLANS
# ============================================================================

class Plan(str, Enum):
    CORE = "core"
    PREMIUM = "premium"
    BUSINESS = "business"


# ============================================================================
# PACKS
# ============================================================================

class Pack(str, Enum):
    CORE = "core"           # Pipeline, Projets, Production, Assets, Calendrier, Cockpit
    CLIENTS = "clients"     # Clients, Dossiers, Daily Picks
    LEADS = "leads"         # Leads, Kanban Leads, Scoring
    TALENTS = "talents"     # Artistes, Profils, Découverte, Comparaison, Carte
    INTELLIGENCE = "intelligence"  # Analytics, Veille Concur., Prédictions IA


class Addon(str, Enum):
    RADAR_BUSINESS = "radar_business"  # CRM étendu, Devis, Factures


# ============================================================================
# FEATURES (mapped to packs)
# ============================================================================

class Feature(str, Enum):
    # Core
    COCKPIT = "cockpit"
    PIPELINE = "pipeline"
    PROJECTS = "projects"
    PRODUCTION = "production"
    ASSETS = "assets"
    CALENDAR = "calendar"
    
    # Clients
    CLIENTS = "clients"
    DOSSIERS = "dossiers"
    DAILY_PICKS = "daily_picks"
    
    # Leads
    LEADS = "leads"
    KANBAN_LEADS = "kanban_leads"
    SCORING = "scoring"
    
    # Talents
    ARTISTS = "artists"
    PROFILES = "profiles"
    DISCOVERY = "discovery"
    COMPARISON = "comparison"
    MAP = "map"
    EVENTS = "events"
    SPOTIFY_SEARCH = "spotify_search"
    
    # Intelligence
    ANALYTICS = "analytics"
    COMPETITOR_WATCH = "competitor_watch"
    AI_PREDICTIONS = "ai_predictions"
    
    # Radar Business (addon)
    CRM_EXTENDED = "crm_extended"
    QUOTES = "quotes"
    INVOICES = "invoices"
    BANKING = "banking"
    
    # Admin only (always available to admins)
    SOURCES = "sources"
    SOURCE_HEALTH = "source_health"


# ============================================================================
# PACK → FEATURES MAPPING
# ============================================================================

PACK_FEATURES: Dict[Pack, Set[Feature]] = {
    Pack.CORE: {
        Feature.COCKPIT,
        Feature.PIPELINE,
        Feature.PROJECTS,
        Feature.PRODUCTION,
        Feature.ASSETS,
        Feature.CALENDAR,
    },
    Pack.CLIENTS: {
        Feature.CLIENTS,
        Feature.DOSSIERS,
        Feature.DAILY_PICKS,
    },
    Pack.LEADS: {
        Feature.LEADS,
        Feature.KANBAN_LEADS,
        Feature.SCORING,
    },
    Pack.TALENTS: {
        Feature.ARTISTS,
        Feature.PROFILES,
        Feature.DISCOVERY,
        Feature.COMPARISON,
        Feature.MAP,
    },
    Pack.INTELLIGENCE: {
        Feature.ANALYTICS,
        Feature.COMPETITOR_WATCH,
        Feature.AI_PREDICTIONS,
    },
}

ADDON_FEATURES: Dict[Addon, Set[Feature]] = {
    Addon.RADAR_BUSINESS: {
        Feature.CRM_EXTENDED,
        Feature.QUOTES,
        Feature.INVOICES,
        Feature.BANKING,
    },
}

# Admin-only features (not gated by packs)
ADMIN_ONLY_FEATURES: Set[Feature] = {
    Feature.SOURCES,
    Feature.SOURCE_HEALTH,
}


# ============================================================================
# PLAN CONFIGURATION
# ============================================================================

@dataclass
class PlanConfig:
    """Configuration for a subscription plan"""
    name: str
    display_name: str
    description: str
    price_monthly: Optional[int]  # Unpublished until commercial validation
    included_packs: List[Pack]
    included_addons: List[Addon]
    max_seats: int
    features_bullets: List[str]


# Prices are deliberately unpublished until commercial validation.
PLAN_CONFIGS: Dict[Plan, PlanConfig] = {
    Plan.CORE: PlanConfig("core", "Radar Core", "Organisation et production", None,
                          [Pack.CORE], [], 3,
                          ["Projets et tâches", "Planning et calendrier", "Fichiers et livrables"]),
    Plan.PREMIUM: PlanConfig("premium", "Radar Premium", "Production, événements et intelligence artistique", None,
                             [Pack.CORE, Pack.TALENTS, Pack.INTELLIGENCE], [], 10,
                             ["Toutes les fonctions Core", "Discovery et sélections artistiques", "Gestion événementielle"]),
    Plan.BUSINESS: PlanConfig("business", "Radar Business", "Gestion commerciale avancée", None,
                              list(Pack), [], 999,
                              ["Toutes les fonctions Premium", "Clients et prospects", "Devis, factures et suivi des paiements"]),
}
# Keep legacy identifiers readable; they are no longer purchasable offers.
ADDON_CONFIGS = {}  # defined below for backwards imports
EXTRA_SEAT_PRICE = None
DISABLED_FEATURES = {Feature.BANKING, Feature.COMPETITOR_WATCH, Feature.AI_PREDICTIONS}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_plan_packs(plan: Plan) -> List[Pack]:
    """Get packs included in a plan"""
    return PLAN_CONFIGS[plan].included_packs


def get_plan_addons(plan: Plan) -> List[Addon]:
    """Get addons included for free in a plan"""
    return PLAN_CONFIGS[plan].included_addons


def resolve_plan(value: str, enabled_packs=None, addons=None) -> Plan:
    """Read legacy records without dropping their contracted business access."""
    if value in {"mini", "standard"}:
        if set(enabled_packs or []) & {"clients", "leads"} or "radar_business" in (addons or []):
            return Plan.BUSINESS
        return Plan.CORE if value == "mini" else Plan.PREMIUM
    try:
        return Plan(value)
    except (ValueError, TypeError):
        return Plan.CORE  # Unknown plans never grant paid access.


def get_plan_features(plan: Plan, addons=None) -> Set[Feature]:
    """Authoritative entitlements. Packs/addons cannot bypass a plan."""
    features = set()
    for pack in PLAN_CONFIGS[plan].included_packs:
        features.update(PACK_FEATURES.get(pack, set()))
    if plan in {Plan.PREMIUM, Plan.BUSINESS}:
        features.update({Feature.EVENTS, Feature.SPOTIFY_SEARCH})
    if plan == Plan.BUSINESS:
        features.update(ADDON_FEATURES[Addon.RADAR_BUSINESS])
    return features - DISABLED_FEATURES


def effective_features(workspace) -> Set[Feature]:
    from datetime import datetime
    if workspace.plan_expires_at and workspace.plan_expires_at <= datetime.utcnow():
        return get_plan_features(Plan.CORE)
    return get_plan_features(resolve_plan(workspace.plan, workspace.enabled_packs, workspace.addons))


def get_pack_from_feature(feature: Feature) -> Optional[Pack]:
    """Find which pack contains a feature"""
    for pack, pack_features in PACK_FEATURES.items():
        if feature in pack_features:
            return pack
    return None


def get_addon_from_feature(feature: Feature) -> Optional[Addon]:
    """Find which addon contains a feature"""
    for addon, addon_features in ADDON_FEATURES.items():
        if feature in addon_features:
            return addon
    return None


def is_feature_available(
    feature: Feature,
    plan: Plan,
    addons: List[Addon] = None,
    is_admin: bool = False
) -> bool:
    """Check if a feature is available for a given plan/addons combination"""
    # Admin-only features
    if feature in ADMIN_ONLY_FEATURES:
        return is_admin
    
    available_features = get_plan_features(plan, addons)
    return feature in available_features


def get_upgrade_message(feature: Feature, current_plan: Plan) -> str:
    if feature in DISABLED_FEATURES:
        return "Fonctionnalité suspendue en attente de validation"
    for plan in Plan:
        if feature in get_plan_features(plan):
            return f"Disponible avec {PLAN_CONFIGS[plan].display_name}"
    return "Contactez votre administrateur"


# ============================================================================
# FEATURE TO ROUTE MAPPING (for navigation gating)
# ============================================================================

FEATURE_ROUTES: Dict[str, Feature] = {
    # Core
    "/cockpit": Feature.COCKPIT,
    "/pipeline": Feature.PIPELINE,
    "/projects": Feature.PROJECTS,
    "/production": Feature.PRODUCTION,
    "/assets": Feature.ASSETS,
    "/calendar": Feature.CALENDAR,
    "/today": Feature.COCKPIT,  # Today is part of Cockpit
    
    # Clients
    "/clients": Feature.CLIENTS,
    "/dossiers": Feature.DOSSIERS,
    
    # Leads
    "/leads": Feature.LEADS,
    "/opportunities": Feature.LEADS,
    
    # Talents
    "/artists": Feature.ARTISTS,
    "/profiles": Feature.PROFILES,
    "/discovery": Feature.DISCOVERY,
    "/comparison": Feature.COMPARISON,
    "/map": Feature.MAP,
    
    # Intelligence
    "/analytics": Feature.ANALYTICS,
    "/competitor-watch": Feature.COMPETITOR_WATCH,
    "/predictions": Feature.AI_PREDICTIONS,
    
    # Radar Business
    "/quotes": Feature.QUOTES,
    "/invoices": Feature.INVOICES,
    "/banking": Feature.BANKING,
    
    # Admin
    "/sources": Feature.SOURCES,
    "/source-health": Feature.SOURCE_HEALTH,
}


# ============================================================================
# NAVIGATION ITEMS CONFIG (for sidebar rendering)
# ============================================================================

@dataclass
class NavItem:
    """Navigation item configuration"""
    label: str
    path: str
    icon: str
    feature: Optional[Feature] = None
    admin_only: bool = False
    badge: Optional[str] = None


NAV_SECTIONS = {
    "Accueil": [NavItem("Vue d'ensemble", "/today", "Home", Feature.COCKPIT),
                NavItem("Activités et notifications", "/inbox", "Inbox", Feature.COCKPIT)],
    "Organisation": [NavItem("Projets", "/projects", "FolderOpen", Feature.PROJECTS),
                     NavItem("Tâches et production", "/production", "Clapperboard", Feature.PRODUCTION),
                     NavItem("Calendrier", "/agency-calendar", "Calendar", Feature.CALENDAR),
                     NavItem("Fichiers", "/assets", "Image", Feature.ASSETS)],
    "Événementiel": [NavItem("Événements", "/events", "CalendarDays", Feature.EVENTS),
                      NavItem("Discovery", "/discovery", "Search", Feature.DISCOVERY),
                      NavItem("Sélections artistiques", "/comparison", "GitCompare", Feature.COMPARISON)],
    "Business": [NavItem("Clients et prospects", "/clients", "Users", Feature.CLIENTS),
                 NavItem("Pipeline commercial", "/pipeline", "TrendingUp", Feature.PIPELINE),
                 NavItem("Devis", "/devis", "Receipt", Feature.QUOTES),
                 NavItem("Factures et paiements", "/factures", "FileCheck", Feature.INVOICES)],
    "Administration": [NavItem("Équipe et intégrations", "/workspace/settings", "Users", admin_only=True),
                        NavItem("Abonnement", "/settings/subscription", "CreditCard"),
                        NavItem("Paramètres", "/settings", "Settings")],
}
# The commercial pipeline belongs to Business; Core remains production focused.
PACK_FEATURES[Pack.CORE].discard(Feature.PIPELINE)
PACK_FEATURES[Pack.LEADS].add(Feature.PIPELINE)
