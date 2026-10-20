"""
Database Models
"""
from .account import Account  # Must be imported before User for relationship resolution
from .user import User, Role
from .opportunity import (
    Opportunity,
    OpportunityNote,
    OpportunityTask,
    OpportunityTag,
    SourceType,
    OpportunityCategory,
    OpportunityStatus,
    TaskStatus,
)
from .source import SourceConfig
from .ingestion import IngestionRun
from .scoring import ScoringRule
from .artist_analysis import ArtistAnalysis
from .entity import (
    Entity,
    EntityType,
    Document,
    Extract,
    Contact,
    ContactType,
    Brief,
    CollectionRun,
    ObjectiveType,
)
from .dossier import (
    SourceDocument,
    DocType,
    Dossier,
    DossierState,
    DossierEvidence,
    EvidenceProvenance,
    EvidenceType,
    WebEnrichmentRun,
)
# Activity Log
from .activity_log import ActivityLog

# Radar Features (nouvelles fonctionnalités)
from .radar_features import (
    Profile,
    ProfileObjective,
    OpportunityProfileScore,
    DailyShortlist,
    ShortlistReason,
    OpportunityCluster,
    OpportunityClusterMember,
    DeadlineAlert,
    AlertType,
    AlertStatus,
    SourceHealth,
    ContactFinderResult,
)

# Nouveaux modèles refonte v2
from .collections import (
    CollectionType,
    CollectionStatus,
    LogLevel,
    LeadItemKind,
    LeadItemStatus,
    DossierObjective,
    DossierState as DossierStateV2,
    EvidenceProvenance as EvidenceProvenanceV2,
    CollectionV2,
    CollectionLog,
    LeadItem,
    CollectionResult,
    SourceDocumentV2,
    DossierV2,
    Evidence,
)

# Agency Cockpit V2 - New models
from .agency import (
    Client,
    Deal,
    Project,
    Deliverable,
    Approval,
    Asset,
    AgencyTask,
    CalendarEvent,
    ProjectActivityLog,
    DealStatus,
    ProjectStatus,
    DeliverableStatus,
    ApprovalStatus,
    AssetKind,
    TaskStatus as AgencyTaskStatus,
    TaskPriority,
    CalendarEventType,
    ActivityType,
)

# Workspace & Multi-tenant
from .workspace import (
    Workspace,
    WorkspaceMember,
    WorkspaceInvite,
    WorkspaceRole,
)

# Billing - Radar Business (Quotes & Invoices)
from .billing import (
    BillingClient,
    Quote,
    QuoteItem,
    Invoice,
    InvoiceItem,
    QuoteStatus,
    InvoiceStatus,
    PaymentMethod,
)

# Drive Folder Map - Google Drive structure tracking
from .drive_folder_map import (
    DriveFolderMap,
    DriveFolderType,
)

# Discovery V3 - Artist discovery and enrichment
from .discovery import (
    DiscoveryArtist,
    DiscoverySnapshot,
    DiscoveryComputedMetrics,
    DiscoveryCandidate,
    DiscoveryComparisonList,
    DiscoveryComparisonItem,
    DiscoveryEnrichmentJob,
    DataQuality,
    TimingBucket,
    Recommendation,
    CandidateType,
    SnapshotSource,
    SnapshotStatus,
    JobStatus,
    JobStep,
    InputType,
)

# Spotify Search - Dedicated Spotify search engine
from .spotify_search import (
    SpotifySearchJob,
    SpotifySearchResult,
    SpotifyJobStatus,
    SpotifyJobStep,
)

# Banking Connections - Radar Business
from .banking import (
    BankConnection,
    BankAccount,
    BankConsent,
    BankSyncLog,
    BankConnectionStatus,
    BankAccountType,
    ConsentType,
    ConsentStatus,
    SyncStatus,
    SyncTrigger,
)


from .subscription_request import SubscriptionRequest

from .production_event import ProductionEvent, EventArtist, EventExpense
