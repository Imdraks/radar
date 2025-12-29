// Opportunity types
export interface Opportunity {
  id: number;
  uid: string;
  title: string;
  description?: string;
  raw_content?: string;
  source_type: SourceType;
  source_config_id?: number;
  source_name?: string;
  source_email?: string;
  url_primary?: string;
  url_secondary?: string[];
  category?: OpportunityCategory;
  status: OpportunityStatus;
  region?: string;
  organization_name?: string;
  budget_amount?: number;
  budget_currency: string;
  budget_text?: string;
  budget_hint?: string;
  deadline_at?: string;
  event_date_start?: string;
  event_date_end?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  score?: number;
  score_breakdown?: ScoreBreakdownItem[];
  assigned_to_id?: number;
  assigned_to?: User;
  duplicate_of_id?: number;
  is_duplicate: boolean;
  ingested_at: string;
  created_at: string;
  updated_at?: string;
  tags?: OpportunityTag[];
  notes?: OpportunityNote[];
  tasks?: OpportunityTask[];
}

export interface OpportunityTag {
  id: number;
  name: string;
  color?: string;
}

export interface OpportunityNote {
  id: number;
  opportunity_id: number;
  author_id: number;
  author?: User;
  content: string;
  is_internal: boolean;
  created_at: string;
  updated_at?: string;
}

export interface OpportunityTask {
  id: number;
  opportunity_id: number;
  title: string;
  description?: string;
  due_at?: string;
  is_completed: boolean;
  completed_at?: string;
  assigned_to_id?: number;
  assigned_to?: User;
  created_by_id: number;
  created_by?: User;
  created_at: string;
  updated_at?: string;
}

export interface ScoreBreakdownItem {
  rule: string;
  label: string;
  points: number;
}

export type SourceType = "rss" | "html" | "api" | "email";
export type OpportunityCategory = "appel_offres" | "partenariat" | "sponsoring" | "privatisation" | "production" | "prestation" | "autre";
export type OpportunityStatus = "new" | "to_qualify" | "qualified" | "in_progress" | "submitted" | "won" | "lost" | "archived";

// User types
export interface LinkedAccount {
  provider: string;
  email?: string;
  created_at?: string;
}

export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  auth_provider?: string;
  avatar_url?: string;
  linked_accounts?: LinkedAccount[];
  notification_preferences?: NotificationPreferences;
  created_at: string;
  updated_at?: string;
}

export type UserRole = "admin" | "bizdev" | "pm" | "viewer";

export interface NotificationPreferences {
  email?: boolean;
  discord?: boolean;
  slack?: boolean;
  min_score?: number;
}

// Source types
export interface SourceConfig {
  id: number;
  name: string;
  source_type: SourceType;
  description?: string;
  url?: string;
  api_key?: string;
  css_selector_list?: string;
  css_selector_item?: string;
  css_selector_title?: string;
  css_selector_description?: string;
  css_selector_link?: string;
  css_selector_date?: string;
  email_folder: string;
  poll_interval_minutes: number;
  is_active: boolean;
  last_polled_at?: string;
  extra_config?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

// Ingestion types
export interface IngestionRun {
  id: number;
  source_config_id?: number;
  source_config?: SourceConfig;
  source_type: SourceType;
  started_at: string;
  finished_at?: string;
  status: IngestionStatus;
  items_found: number;
  items_new: number;
  items_duplicate: number;
  items_error: number;
  error_message?: string;
  details?: Record<string, unknown>;
}

export type IngestionStatus = "running" | "completed" | "failed";

// Scoring types
export interface ScoringRule {
  id: number;
  name: string;
  rule_type: RuleType;
  description?: string;
  condition_type: string;
  condition_value: Record<string, unknown>;
  points: number;
  label?: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export type RuleType = "urgency" | "event_fit" | "quality" | "value" | "penalty";

// Dashboard types
export interface DashboardStats {
  total_opportunities: number;
  new_today: number;
  new_this_week: number;
  avg_score: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_source_type: Record<string, number>;
}

export interface BudgetStats {
  min: number;
  max: number;
  avg: number;
  median: number;
  histogram: BudgetBucket[];
}

export interface BudgetBucket {
  min: number;
  max: number;
  count: number;
}

// Pagination types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Auth types
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ============================================================================
// RADAR FEATURES TYPES
// ============================================================================

// Profiles (Fit Score)
export interface Profile {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  keywords_include: string[];
  keywords_exclude: string[];
  regions: string[];
  cities: string[];
  budget_min?: number;
  budget_max?: number;
  objectives: string[];
  weights: ProfileWeights;
  created_at: string;
  updated_at: string;
}

export type ProfileObjective = 
  | "visibility" 
  | "revenue" 
  | "networking" 
  | "artist_development"
  | "brand_building";

export interface ProfileWeights {
  score_base: number;
  budget_match: number;
  deadline_proximity: number;
  contact_present: number;
  location_match: number;
}

export interface OpportunityProfileScore {
  opportunity_id: number;
  profile_id: number;
  fit_score: number;
  computed_at: string;
  opportunity?: Opportunity;
}

// Shortlists (Daily Picks)
export interface ShortlistItem {
  opportunity_id: string;
  title: string;
  organization?: string;
  score: number;
  fit_score: number;
  reasons: string[];
  deadline_at?: string;
  url?: string;
  category?: string;
}

export interface DailyShortlist {
  id: string;
  date: string;
  profile_id: string;
  profile_name: string;
  items: ShortlistItem[];
  total_candidates: number;
  items_count: number;
  created_at: string;
}

// Clusters (Deduplication)
export type ClusterMatchType = "url" | "hash" | "text" | "ai";

export interface ClusterMember {
  opportunity_id: string;
  title: string;
  source_name: string;
  url?: string;
  similarity_score: number;
  match_type: string;
}

export interface OpportunityCluster {
  cluster_id: string;
  canonical_opportunity_id: string;
  canonical_title: string;
  member_count: number;
  cluster_score: number;
  members: ClusterMember[];
}

export interface ClusterRebuildResponse {
  clusters_created: number;
  clusters_updated: number;
  opportunities_clustered: number;
  duration_seconds: number;
}

// Deadline Alerts
export type AlertType = "J_7" | "J_3" | "J_1";
export type AlertStatus = "pending" | "sent" | "acknowledged" | "dismissed";

export interface DeadlineAlert {
  id: number;
  opportunity_id: number;
  opportunity?: Opportunity;
  deadline: string;
  alert_type: AlertType;
  status: AlertStatus;
  scheduled_at: string;
  sent_at?: string;
  acknowledged_at?: string;
}

export interface UpcomingDeadline {
  opportunity: Opportunity;
  days_remaining: number;
  alerts: DeadlineAlert[];
}

// Source Health
export interface SourceHealthMetrics {
  source_id: number;
  source?: SourceConfig;
  date: string;
  opportunities_found: number;
  duplicates_found: number;
  avg_score: number;
  error_rate: number;
  freshness_hours: number;
  health_score: number;
}

export interface SourceHealthSummary {
  source_id: string;
  source_name: string;
  is_active: boolean;
  avg_health_score: number;
  total_items_last_7_days: number;
  error_rate_last_7_days: number;
  recommendation?: "disable" | "repair" | "prioritize" | null;
}

export interface SourceHealthOverview {
  sources: SourceHealthSummary[];
  total_active: number;
  total_inactive: number;
  avg_health_score: number;
  sources_needing_attention: number;
}

// Contact Finder
export interface ContactInfo {
  type: "email" | "phone" | "website" | "linkedin" | "twitter";
  value: string;
  confidence: number;
  source: string;
}

export interface ContactFinderResult {
  id: number;
  opportunity_id: number;
  contacts: ContactInfo[];
  evidence: string[];
  status: "pending" | "searching" | "completed" | "failed";
  requested_at: string;
  completed_at?: string;
}

export interface ContactFinderStats {
  total_searches: number;
  successful_searches: number;
  emails_found: number;
  phones_found: number;
}
