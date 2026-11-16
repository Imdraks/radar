import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

// Use relative URL in production (empty string), localhost in development
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// Request deduplication cache
const pendingRequests = new Map<string, Promise<unknown>>();

function getRequestKey(config: InternalAxiosRequestConfig): string {
  return `${config.method}:${config.url}:${JSON.stringify(config.params || {})}`;
}

// Create axios instance for V1 API (legacy)
export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Create axios instance for V2 API (new architecture with UUIDs)
export const apiV2: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v2`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Helper to setup auth interceptor on an axios instance
function setupAuthInterceptor(instance: AxiosInstance) {
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      // Automatically add workspace_id to all requests (for multi-tenant isolation)
      if (typeof window !== "undefined") {
        const workspaceId = localStorage.getItem("current_workspace_id");
        if (workspaceId) {
          // Add to query params
          config.params = config.params || {};
          if (!config.params.workspace_id) {
            config.params.workspace_id = workspaceId;
          }
        }
      }
      
      return config;
    },
    (error) => Promise.reject(error)
  );
}

// Apply auth to both API instances
setupAuthInterceptor(api);
setupAuthInterceptor(apiV2);

// Response interceptor - handle 401 (only on V1 for now)
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    // A rejected step-up code is not an expired API session. Never replay an
    // MFA mutation automatically: it consumes attempts or a one-use proof.
    if (error.response?.status === 401 && originalRequest?.method?.toUpperCase() === 'POST'
      && /\/auth\/mfa\//.test(originalRequest.url || '')) {
      return Promise.reject(error);
    }

    // Handle NO_WORKSPACE_ACCESS - redirect to waiting page
    if (error.response?.status === 403) {
      const detail = (error.response?.data as { detail?: string })?.detail;
      if (detail === "NO_WORKSPACE_ACCESS") {
        if (typeof window !== "undefined" && !window.location.pathname.includes("/no-workspace")) {
          window.location.href = "/no-workspace";
        }
        return Promise.reject(error);
      }
    }

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
      
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: newRefreshToken } = response.data;
          
          localStorage.setItem("access_token", access_token);
          if (newRefreshToken) {
            localStorage.setItem("refresh_token", newRefreshToken);
          }

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      } else {
        // No refresh token, redirect to login
        localStorage.removeItem("access_token");
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  mfaOptions: async (challengeToken: string) => (await axios.post(`${API_URL}/api/v1/auth/mfa/options`, { challenge_token: challengeToken })).data,
  mfaSend: async (challengeToken: string, method: string) => (await axios.post(`${API_URL}/api/v1/auth/mfa/send`, { challenge_token: challengeToken, method })).data,
  mfaComplete: async (challengeToken: string, method: string, code: string) => (await axios.post(`${API_URL}/api/v1/auth/mfa/complete`, { challenge_token: challengeToken, method, code })).data,
  login: async (email: string, password: string, totpCode?: string) => {
    const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
      email,
      password,
      totp_code: totpCode,
    }, {
      headers: { "Content-Type": "application/json" },
    });
    return response.data;
  },
  
  getMe: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },
  
  refresh: async (refreshToken: string) => {
    const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};

// =============================================================================
// LEADS API (V2 - UUID based, uses /api/v2/leads)
// =============================================================================

export const leadsApi = {
  getAll: async (params?: Record<string, unknown>) => {
    const response = await apiV2.get("/leads", { params });
    return response.data;
  },
  
  getOne: async (id: string) => {
    const response = await apiV2.get(`/leads/${id}`);
    return response.data;
  },
  
  update: async (id: string, data: Record<string, unknown>) => {
    const response = await apiV2.patch(`/leads/${id}`, data);
    return response.data;
  },
  
  bulkUpdate: async (data: { ids: string[]; updates: Record<string, unknown> }) => {
    const response = await apiV2.post("/leads/bulk-update", data);
    return response.data;
  },
  
  createDossier: async (id: string, data?: Record<string, unknown>) => {
    const response = await apiV2.post(`/leads/${id}/create-dossier`, data || {});
    return response.data;
  },
  
  getStats: async () => {
    const response = await apiV2.get("/leads/stats");
    return response.data;
  },
};

// =============================================================================
// LEGACY OPPORTUNITIES API (V1 - Integer IDs, uses /api/v1/opportunities)
// @deprecated - Use leadsApi for new features
// =============================================================================

export const opportunitiesApi = {
  getAll: async (params?: Record<string, unknown>) => {
    const response = await api.get("/opportunities", { params });
    return response.data;
  },
  
  getOne: async (id: string | number) => {
    const response = await api.get(`/opportunities/${id}`);
    return response.data;
  },
  
  create: async (data: Record<string, unknown>) => {
    const response = await api.post("/opportunities", data);
    return response.data;
  },
  
  update: async (id: string | number, data: Record<string, unknown>) => {
    const response = await api.patch(`/opportunities/${id}`, data);
    return response.data;
  },
  
  delete: async (id: string | number) => {
    const response = await api.delete(`/opportunities/${id}`);
    return response.data;
  },
  
  getBudgetStats: async (params?: Record<string, unknown>) => {
    const response = await api.get("/opportunities/budget-stats", { params });
    return response.data;
  },
  
  // Notes
  getNotes: async (opportunityId: string | number) => {
    const response = await api.get(`/opportunities/${opportunityId}/notes`);
    return response.data;
  },
  
  addNote: async (opportunityId: string | number, data: { content: string; is_internal?: boolean }) => {
    const response = await api.post(`/opportunities/${opportunityId}/notes`, data);
    return response.data;
  },
  
  // Tasks
  getTasks: async (opportunityId: string | number) => {
    const response = await api.get(`/opportunities/${opportunityId}/tasks`);
    return response.data;
  },
  
  addTask: async (opportunityId: string | number, data: Record<string, unknown>) => {
    const response = await api.post(`/opportunities/${opportunityId}/tasks`, data);
    return response.data;
  },
  
  updateTask: async (opportunityId: string | number, taskId: string | number, data: Record<string, unknown>) => {
    const response = await api.patch(`/opportunities/${opportunityId}/tasks/${taskId}`, data);
    return response.data;
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: async () => {
    const response = await api.get("/dashboard/stats");
    return response.data;
  },
  
  getTopOpportunities: async (limit = 10) => {
    const response = await api.get("/dashboard/top-opportunities", { params: { limit } });
    return response.data;
  },
  
  getUpcomingDeadlines: async (days = 14, limit = 10) => {
    const response = await api.get("/dashboard/upcoming-deadlines", { params: { days, limit } });
    return response.data;
  },
  
  getRecentIngestions: async (limit = 10) => {
    const response = await api.get("/dashboard/recent-ingestions", { params: { limit } });
    return response.data;
  },
};

// Sources API
export const sourcesApi = {
  getAll: async (params?: Record<string, unknown>) => {
    const response = await api.get("/sources", { params });
    return response.data;
  },
  
  getOne: async (id: number) => {
    const response = await api.get(`/sources/${id}`);
    return response.data;
  },
  
  create: async (data: Record<string, unknown>) => {
    const response = await api.post("/sources", data);
    return response.data;
  },
  
  update: async (id: number, data: Record<string, unknown>) => {
    const response = await api.patch(`/sources/${id}`, data);
    return response.data;
  },
  
  delete: async (id: number) => {
    const response = await api.delete(`/sources/${id}`);
    return response.data;
  },
  
  test: async (id: number) => {
    const response = await api.post(`/sources/${id}/test`);
    return response.data;
  },
};

// Ingestion API
export interface IngestionSearchParams {
  keywords?: string;
  region?: string;
  city?: string;
  budget_min?: number;
  budget_max?: number;
}

export const ingestionApi = {
  trigger: async (sourceId?: number, searchParams?: IngestionSearchParams) => {
    const response = await api.post("/ingestion/run", {
      source_ids: sourceId ? [sourceId] : undefined,
      search_params: searchParams,
    });
    return response.data;
  },
  
  getRuns: async (params?: Record<string, unknown>) => {
    const response = await api.get("/ingestion/runs", { params });
    return response.data;
  },
};

// Scoring API
export const scoringApi = {
  getRules: async () => {
    const response = await api.get("/scoring/rules");
    return response.data;
  },
  
  getRule: async (id: number) => {
    const response = await api.get(`/scoring/rules/${id}`);
    return response.data;
  },
  
  createRule: async (data: Record<string, unknown>) => {
    const response = await api.post("/scoring/rules", data);
    return response.data;
  },
  
  updateRule: async (id: number, data: Record<string, unknown>) => {
    const response = await api.patch(`/scoring/rules/${id}`, data);
    return response.data;
  },
  
  deleteRule: async (id: number) => {
    const response = await api.delete(`/scoring/rules/${id}`);
    return response.data;
  },
  
  recalculateAll: async () => {
    const response = await api.post("/scoring/recalculate");
    return response.data;
  },
};

// Users API
export const usersApi = {
  getAll: async (params?: Record<string, unknown>) => {
    const response = await api.get("/users", { params });
    return response.data;
  },
  
  getOne: async (id: number) => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },
  
  create: async (data: Record<string, unknown>) => {
    const response = await api.post("/users", data);
    return response.data;
  },
  
  update: async (id: number, data: Record<string, unknown>) => {
    const response = await api.patch(`/users/${id}`, data);
    return response.data;
  },
  
  delete: async (id: number) => {
    const response = await api.delete(`/users/${id}`);
    return response.data;
  },
};

// Collection API (Entity-based collection system)
export interface EntityInput {
  name: string;
  type: "PERSON" | "ORGANIZATION" | "TOPIC";
}

export interface CollectRequest {
  objective: string;
  entities: EntityInput[];
  secondary_keywords?: string[];
  budget_min?: number;
  budget_max?: number;
  region?: string;
  city?: string;
  timeframe_days: number;
  require_contact: boolean;
}

export interface CollectResponse {
  run_id: string;
  source_count: number;
  task_ids: string[];
  entities_created: string[];
  message: string;
}

export interface Brief {
  id: string;
  entity_id: string;
  entity_name?: string;
  entity_type?: "PERSON" | "ORGANIZATION" | "TOPIC";
  objective: string;
  timeframe_days: number;
  overview?: string;
  contacts_ranked: Array<{
    type: string;
    value: string;
    label?: string;
    reliability_score: number;
    source?: string;
    is_verified?: boolean;
  }>;
  useful_facts: Array<{
    fact: string;
    source?: string;
    category?: string;
  }>;
  timeline: Array<{
    date?: string;
    event_type: string;
    description: string;
    source?: string;
  }>;
  sources_used: Array<{
    name: string;
    url?: string;
    document_count: number;
  }>;
  document_count: number;
  contact_count: number;
  completeness_score: number;
  generated_at: string;
}

export interface CollectionRun {
  id: string;
  status: string;
  objective: string;
  started_at: string;
  finished_at?: string;
  source_count: number;
  sources_success: number;
  sources_failed: number;
  documents_new: number;
  documents_updated: number;
  contacts_found: number;
  entities_requested: Array<{ name: string; type: string }>;
  source_runs: Array<{
    source_name: string;
    status: string;
    items_found: number;
    items_new: number;
    latency_ms?: number;
    error?: string;
  }>;
  error_summary?: string;
}

// =====================
// NEW: Unified Collection API
// =====================

export interface StandardCollectRequest {
  keywords?: string;
  source_ids?: string[];
  region?: string;
  city?: string;
  budget_min?: number;
  budget_max?: number;
}

export interface StandardCollectResponse {
  run_ids: string[];
  source_count: number;
  message: string;
}

export interface AdvancedCollectRequest {
  objective: string;
  entities: { name: string; type: string }[];
  secondary_keywords?: string[];
  timeframe_days?: number;
  require_contact?: boolean;
  region?: string;
  city?: string;
  budget_min?: number;
  budget_max?: number;
}

export interface AdvancedCollectResponse {
  run_id: string;
  entities_created: string[];
  message: string;
}

export interface CollectionStatus {
  id: string;
  type: "standard" | "advanced";
  status: string;
  started_at?: string;
  finished_at?: string;
  items_found: number;
  items_new: number;
  contacts_found: number;
  error_message?: string;
  brief_id?: string;
}

// Unified Collection API (NEW)
export const collectApi = {
  // Standard collection (Sources -> Opportunities)
  startStandard: async (request: StandardCollectRequest): Promise<StandardCollectResponse> => {
    const response = await api.post("/collect/standard", request);
    return response.data;
  },

  // Advanced collection (ChatGPT -> Briefs/Dossiers)
  startAdvanced: async (request: AdvancedCollectRequest): Promise<AdvancedCollectResponse> => {
    const response = await api.post("/collect/advanced", request);
    return response.data;
  },

  // Get standard collection status
  getStandardStatus: async (limit = 10): Promise<CollectionStatus[]> => {
    const response = await api.get("/collect/standard/status", { params: { limit } });
    return response.data;
  },

  // Get advanced collection status
  getAdvancedStatus: async (runId: string): Promise<CollectionStatus> => {
    const response = await api.get(`/collect/advanced/status/${runId}`);
    return response.data;
  },
};

// =============================================================================
// DOSSIERS API - GPT-enriched opportunity analysis
// =============================================================================

export interface DossierSummary {
  id: string;
  opportunity_id: string;
  opportunity_title: string;
  state: 'NOT_CREATED' | 'PROCESSING' | 'ENRICHING' | 'MERGING' | 'READY' | 'FAILED';
  summary_short: string | null;
  confidence_plus: number;
  score_final: number;
  quality_flags: string[];
  missing_fields: string[];
  created_at: string;
  updated_at: string;
}

export interface DossierDetail extends DossierSummary {
  summary_long: string | null;
  key_points: string[];
  action_checklist: string[];
  extracted_fields: {
    deadline_at?: string;
    budget_amount?: number;
    budget_hint?: string;
    location?: { city: string; region: string; country: string };
    contact_email?: string;
    contact_phone?: string;
    contact_url?: string;
    exigences?: string[];
    contraintes?: string[];
    doc_list?: string[];
  };
  sources_used: string[];
  gpt_model_used: string | null;
  tokens_used: number;
  processing_time_ms: number;
  processed_at: string | null;
  enriched_at: string | null;
  opportunity_url: string | null;
  opportunity_organization: string | null;
  opportunity_score_base: number;
}

export interface DossierEvidence {
  id: string;
  field_key: string;
  value: string | null;
  provenance: 'STANDARD_DOC' | 'WEB_ENRICHED';
  evidence_type: 'HTML' | 'EMAIL' | 'PDF' | 'WEB';
  evidence_ref: string | null;
  evidence_snippet: string | null;
  confidence: number;
  source_url: string | null;
  retrieved_at: string | null;
  retrieval_method: string | null;
  created_at: string;
}

export interface SourceDocumentItem {
  id: string;
  doc_type: string;
  source_url: string | null;
  fetched_at: string | null;
  created_at: string;
  raw_text_preview: string | null;
}

export interface EnrichmentRun {
  id: string;
  status: string;
  target_fields: string[];
  fields_found: string[];
  fields_not_found: string[];
  urls_consulted: string[];
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  errors: string[];
}

export interface DossierStats {
  total: number;
  ready: number;
  processing: number;
  failed: number;
  with_missing_fields: number;
  average_confidence: number;
}

export const dossiersApi = {
  // List dossiers with filters
  list: async (params?: {
    state?: string;
    q?: string;
    min_confidence?: number;
    has_missing_fields?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<DossierSummary[]> => {
    const response = await api.get("/dossiers", { params });
    return response.data;
  },

  // Get full dossier details
  get: async (dossierId: string): Promise<DossierDetail> => {
    const response = await api.get(`/dossiers/${dossierId}`);
    return response.data;
  },

  // Get dossier for opportunity
  getByOpportunity: async (opportunityId: string): Promise<DossierDetail> => {
    const response = await api.get(`/dossiers/opportunities/${opportunityId}/dossier`);
    return response.data;
  },

  // Get evidence for a dossier
  getEvidence: async (dossierId: string, fieldKey?: string): Promise<DossierEvidence[]> => {
    const response = await api.get(`/dossiers/${dossierId}/evidence`, {
      params: fieldKey ? { field_key: fieldKey } : undefined,
    });
    return response.data;
  },

  // Get source documents for a dossier
  getSources: async (dossierId: string): Promise<SourceDocumentItem[]> => {
    const response = await api.get(`/dossiers/${dossierId}/sources`);
    return response.data;
  },

  // Get enrichment history
  getEnrichments: async (dossierId: string): Promise<EnrichmentRun[]> => {
    const response = await api.get(`/dossiers/${dossierId}/enrichments`);
    return response.data;
  },

  // Delete a dossier
  delete: async (dossierId: string): Promise<void> => {
    await api.delete(`/dossiers/${dossierId}`);
  },

  // Build dossier for opportunity
  build: async (opportunityId: string, options?: {
    force_rebuild?: boolean;
    auto_enrich?: boolean;
  }): Promise<{ task_id: string; message: string }> => {
    const response = await api.post(
      `/dossiers/opportunities/${opportunityId}/dossier/build`,
      options || { force_rebuild: false, auto_enrich: true }
    );
    return response.data;
  },

  // Trigger web enrichment
  enrich: async (opportunityId: string, options?: {
    target_fields?: string[];
    auto_merge?: boolean;
  }): Promise<{ task_id: string; message: string }> => {
    const response = await api.post(
      `/dossiers/opportunities/${opportunityId}/dossier/enrich`,
      options || { auto_merge: true }
    );
    return response.data;
  },

  // Run full pipeline
  fullPipeline: async (opportunityId: string, forceRebuild = false): Promise<{ task_id: string; message: string }> => {
    const response = await api.post(
      `/dossiers/opportunities/${opportunityId}/dossier/full-pipeline`,
      null,
      { params: { force_rebuild: forceRebuild } }
    );
    return response.data;
  },

  // Batch build dossiers
  batchBuild: async (opportunityIds: string[], options?: {
    force_rebuild?: boolean;
    auto_enrich?: boolean;
  }): Promise<{ task_id: string; message: string }> => {
    const response = await api.post("/dossiers/batch/build", {
      opportunity_ids: opportunityIds,
      ...options,
    });
    return response.data;
  },

  // Get stats
  getStats: async (): Promise<DossierStats> => {
    const response = await api.get("/dossiers/stats/overview");
    return response.data;
  },
};

// Legacy Collection API (keep for backward compatibility)
export const collectionApi = {
  // Start a collection
  collect: async (request: CollectRequest): Promise<CollectResponse> => {
    const response = await api.post("/collection", request);
    return response.data;
  },
  
  // Get collection run status
  getRun: async (runId: string): Promise<CollectionRun> => {
    const response = await api.get(`/collection/runs/${runId}`);
    return response.data;
  },
  
  // List briefs
  getBriefs: async (params?: { entity_id?: string; objective?: string; limit?: number }): Promise<Brief[]> => {
    const response = await api.get("/collection/briefs", { params });
    return response.data;
  },
  
  // Get a specific brief
  getBrief: async (briefId: string): Promise<Brief> => {
    const response = await api.get(`/collection/briefs/${briefId}`);
    return response.data;
  },
  
  // List entities
  getEntities: async (params?: { entity_type?: string; search?: string; limit?: number }) => {
    const response = await api.get("/collection/entities", { params });
    return response.data;
  },
  
  // Get entity details
  getEntity: async (entityId: string) => {
    const response = await api.get(`/collection/entities/${entityId}`);
    return response.data;
  },
  
  // Get entity contacts
  getEntityContacts: async (entityId: string) => {
    const response = await api.get(`/collection/entities/${entityId}/contacts`);
    return response.data;
  },
  
  // Get entity documents
  getEntityDocuments: async (entityId: string, limit = 50) => {
    const response = await api.get(`/collection/entities/${entityId}/documents`, { params: { limit } });
    return response.data;
  },
};

// Admin API - Superadmin only
export const adminApi = {
  // Get activity logs
  getLogs: async (params?: Record<string, string>) => {
    const response = await api.get("/admin/logs", { params });
    return response.data;
  },
  
  // Get logs stream (for polling)
  getLogsStream: async (since?: string) => {
    const response = await api.get("/admin/logs/stream", { params: since ? { since } : {} });
    return response.data;
  },
  
  // Get users with tracking IDs
  getUsersTracking: async () => {
    const response = await api.get("/admin/users/tracking");
    return response.data;
  },
  
  // Get activity stats
  getStats: async (hours = 24) => {
    const response = await api.get("/admin/logs/stats", { params: { hours } });
    return response.data;
  },
};

// ============================================================================
// RADAR FEATURES API
// ============================================================================

// Profiles API (Fit Score)
export const profilesApi = {
  getAll: async () => {
    const response = await api.get("/profiles");
    // API returns {profiles: [...], total: N}, extract the array
    return response.data.profiles || response.data;
  },
  
  getOne: async (id: number) => {
    const response = await api.get(`/profiles/${id}`);
    return response.data;
  },
  
  create: async (data: {
    name: string;
    description?: string;
    objectives?: string[];
    weights?: Record<string, number>;
    criteria?: Record<string, unknown>;
  }) => {
    const response = await api.post("/profiles", data);
    return response.data;
  },
  
  update: async (id: number, data: Record<string, unknown>) => {
    const response = await api.patch(`/profiles/${id}`, data);
    return response.data;
  },
  
  delete: async (id: number) => {
    const response = await api.delete(`/profiles/${id}`);
    return response.data;
  },
  
  recompute: async (id: number) => {
    const response = await api.post(`/profiles/${id}/recompute`);
    return response.data;
  },
  
  getScores: async (id: number, limit = 50) => {
    const response = await api.get(`/profiles/${id}/scores`, { params: { limit } });
    return response.data;
  },
};

// Shortlists API (Daily Picks)
export const shortlistsApi = {
  getToday: async (profileId?: number) => {
    const response = await api.get("/shortlists/today", { 
      params: profileId ? { profile_id: profileId } : {} 
    });
    return response.data;
  },
  
  getAll: async (params?: { 
    profile_id?: number; 
    date_from?: string; 
    date_to?: string;
    limit?: number;
  }) => {
    const response = await api.get("/shortlists", { params });
    return response.data;
  },
  
  getOne: async (id: number) => {
    const response = await api.get(`/shortlists/${id}`);
    return response.data;
  },
  
  generate: async (profileId?: number) => {
    const response = await api.post("/shortlists/generate", null, { 
      params: profileId ? { profile_id: profileId } : {} 
    });
    return response.data;
  },
};

// Clusters API (Deduplication)
export const clustersApi = {
  getForOpportunity: async (opportunityId: number) => {
    const response = await api.get(`/clusters/opportunity/${opportunityId}`);
    return response.data;
  },
  
  rebuild: async () => {
    const response = await api.post("/clusters/rebuild");
    return response.data;
  },
  
  getStats: async () => {
    const response = await api.get("/clusters/stats");
    return response.data;
  },
};

// Deadlines API (Deadline Guard)
export const deadlinesApi = {
  getUpcoming: async (days = 14) => {
    const response = await api.get("/deadlines/upcoming", { params: { days_ahead: days } });
    return response.data;
  },
  
  getPast: async (days = 30) => {
    const response = await api.get("/deadlines/past", { params: { days_back: days } });
    return response.data;
  },
  
  scheduleAll: async () => {
    const response = await api.post("/deadlines/schedule-all");
    return response.data;
  },
  
  testNotification: async (opportunityId: number) => {
    const response = await api.post("/deadlines/test-notification", { opportunity_id: opportunityId });
    return response.data;
  },
  
  delete: async (id: number) => {
    const response = await api.delete(`/deadlines/${id}`);
    return response.data;
  },
};

// Source Health API
export const sourceHealthApi = {
  getAll: async (days = 30) => {
    const response = await api.get("/sources/health", { params: { days } });
    return response.data;
  },
  
  getOverview: async () => {
    const response = await api.get("/sources/health/overview");
    return response.data;
  },
  
  getOne: async (sourceId: number, days = 30) => {
    const response = await api.get(`/sources/health/${sourceId}`, { params: { days } });
    return response.data;
  },
  
  updateSource: async (sourceId: number, data: { is_active?: boolean }) => {
    const response = await api.patch(`/sources/${sourceId}`, data);
    return response.data;
  },
};

// Contact Finder API
export const contactFinderApi = {
  find: async (opportunityId: number, options?: { 
    search_web?: boolean;
    search_linkedin?: boolean;
    max_results?: number;
  }) => {
    const response = await api.post(`/contact-finder/opportunities/${opportunityId}/find`, options);
    return response.data;
  },
  
  getResult: async (opportunityId: number) => {
    const response = await api.get(`/contact-finder/opportunities/${opportunityId}/result`);
    return response.data;
  },
  
  getStats: async () => {
    const response = await api.get("/contact-finder/stats");
    return response.data;
  },
};

// Analytics Dashboard API
export const analyticsApi = {
  getTimeline: async (period: "7d" | "30d" | "90d" | "12m" = "30d") => {
    const response = await api.get("/analytics/timeline", { params: { period } });
    return response.data;
  },
  
  getConversion: async (period: "7d" | "30d" | "90d" | "all" = "30d") => {
    const response = await api.get("/analytics/conversion", { params: { period } });
    return response.data;
  },
  
  getDeadlineHeatmap: async () => {
    const response = await api.get("/analytics/deadline-heatmap");
    return response.data;
  },
  
  getComparison: async () => {
    const response = await api.get("/analytics/comparison");
    return response.data;
  },
  
  getKpis: async () => {
    const response = await api.get("/analytics/kpis");
    return response.data;
  },
  
  getTopPerformers: async (period: "30d" | "90d" | "all" = "30d") => {
    const response = await api.get("/analytics/top-performers", { params: { period } });
    return response.data;
  },

  getSignals: async () => {
    const response = await api.get("/analytics/signals");
    return response.data;
  },

  getInsights: async () => {
    const response = await api.get("/analytics/insights");
    return response.data;
  },

  getPredictionsSummary: async () => {
    const response = await api.get("/analytics/predictions-summary");
    return response.data;
  },
};

// Market Intelligence API
export const marketIntelligenceApi = {
  getFeed: async () => {
    const response = await api.get("/market-intelligence/feed");
    return response.data;
  },
  getFeeEstimate: async (artistId: string) => {
    const response = await api.get(`/market-intelligence/fee-estimate/${artistId}`);
    return response.data;
  },
};

// Analytics V2 API — Tour de contrôle
export const analyticsV2Api = {
  getCockpit: async () => {
    const response = await api.get("/analytics-v2/cockpit");
    return response.data;
  },
  getTerrain: async () => {
    const response = await api.get("/analytics-v2/terrain");
    return response.data;
  },
  getCompetitiveGaps: async () => {
    const response = await api.get("/analytics-v2/competitive-gaps");
    return response.data;
  },
};

// Competitive Intelligence API
export const competitiveApi = {
  // Competitors management
  getCompetitors: async () => {
    const response = await api.get("/competitive/competitors");
    return response.data;
  },
  
  addCompetitor: async (data: { name: string; keywords?: string[]; website?: string; notes?: string }) => {
    const response = await api.post("/competitive/competitors", data);
    return response.data;
  },
  
  updateCompetitor: async (id: number, data: { name?: string; keywords?: string[]; is_active?: boolean }) => {
    const response = await api.put(`/competitive/competitors/${id}`, data);
    return response.data;
  },
  
  deleteCompetitor: async (id: number) => {
    const response = await api.delete(`/competitive/competitors/${id}`);
    return response.data;
  },
  
  // Analysis
  getMentions: async (period: "7d" | "30d" | "90d" = "30d") => {
    const response = await api.get("/competitive/mentions", { params: { period } });
    return response.data;
  },
  
  getWinnersAnalysis: async (period: "30d" | "90d" | "12m" = "90d") => {
    const response = await api.get("/competitive/winners-analysis", { params: { period } });
    return response.data;
  },
  
  getPricingBenchmark: async (category?: string) => {
    const response = await api.get("/competitive/pricing-benchmark", { params: { category } });
    return response.data;
  },
  
  getAlerts: async () => {
    const response = await api.get("/competitive/alerts");
    return response.data;
  },
  
  getMarketShare: async (period: "30d" | "90d" | "12m" = "90d") => {
    const response = await api.get("/competitive/market-share", { params: { period } });
    return response.data;
  },
};

// ============================================================================
// PROJECT DETAIL API - Page projet détaillée
// ============================================================================

export interface ProjectDetail {
  id: number;
  name: string;
  client_id: number;
  client_name: string | null;
  status: "active" | "blocked" | "delivered" | "archived";
  deadline: string | null;
  owner_id: number | null;
  owner_name: string | null;
  description: string | null;
  budget: number | null;
  drive_folder_id: string | null;
  brief_doc_id: string | null;
  report_sheet_id: string | null;
  next_action_text: string | null;
  next_action_due_date: string | null;
  blocked_reason: string | null;
  progress_percent: number;
  deliverables_total: number;
  deliverables_approved: number;
  tasks_todo: number;
  tasks_doing: number;
  tasks_done: number;
  pending_validations: number;
  days_until_deadline: number | null;
  is_urgent: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectOverview {
  next_action_text: string | null;
  next_action_due_date: string | null;
  blocked_reason: string | null;
  today_tasks: Array<{
    id: number;
    title: string;
    status: string;
    priority: string;
    due_date: string | null;
  }>;
  pending_validations: Array<{
    id: number;
    deliverable_id: number;
    deliverable_name: string;
    requested_at: string | null;
  }>;
  recent_activity: Array<{
    id: number;
    message: string;
    activity_type: string | null;
    created_at: string;
    created_by_name: string | null;
  }>;
}

export interface ProjectDeliverable {
  id: number;
  name: string;
  type: string | null;
  status: string;
  due_date: string | null;
  link: string | null;
  drive_file_id: string | null;
  notes: string | null;
  has_pending_approval: boolean;
  days_until_due: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectTask {
  id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  due_date: string | null;
  assignee_id: number | null;
  assignee_name: string | null;
  created_at: string;
}

export interface ProjectAsset {
  id: number;
  kind: string;
  name: string;
  url: string;
  version: string | null;
  asset_type: string | null;
  created_at: string;
}

export interface ProjectActivityLog {
  id: number;
  message: string;
  activity_type: string | null;
  created_at: string;
  created_by: number | null;
  created_by_name: string | null;
}

export const projectDetailApi = {
  // Project detail
  getDetail: async (projectId: number): Promise<ProjectDetail> => {
    const response = await api.get(`/agency/projects/${projectId}/detail`);
    return response.data;
  },

  getOverview: async (projectId: number): Promise<ProjectOverview> => {
    const response = await api.get(`/agency/projects/${projectId}/overview`);
    return response.data;
  },

  updateProject: async (projectId: number, data: Partial<{
    name: string;
    status: string;
    deadline: string;
    description: string;
    next_action_text: string;
    next_action_due_date: string;
    blocked_reason: string;
    drive_folder_id: string;
    brief_doc_id: string;
    report_sheet_id: string;
  }>): Promise<ProjectDetail> => {
    const response = await api.patch(`/agency/projects/${projectId}`, data);
    return response.data;
  },

  // Deliverables
  getDeliverables: async (projectId: number): Promise<ProjectDeliverable[]> => {
    const response = await api.get(`/agency/projects/${projectId}/deliverables`);
    return response.data;
  },

  createDeliverable: async (projectId: number, data: {
    name: string;
    type?: string;
    status?: string;
    due_date?: string;
    link?: string;
    drive_file_id?: string;
    notes?: string;
  }): Promise<ProjectDeliverable> => {
    const response = await api.post(`/agency/projects/${projectId}/deliverables`, data);
    return response.data;
  },

  updateDeliverable: async (deliverableId: number, data: Partial<{
    name: string;
    type: string | null;
    status: string;
    due_date: string | null;
    link: string | null;
    drive_file_id: string | null;
    notes: string | null;
  }>): Promise<ProjectDeliverable> => {
    const response = await api.patch(`/agency/projects/deliverables/${deliverableId}`, data);
    return response.data;
  },

  requestValidation: async (deliverableId: number) => {
    const response = await api.post(`/agency/projects/deliverables/${deliverableId}/request-validation`);
    return response.data;
  },

  approveDeliverable: async (deliverableId: number) => {
    const response = await api.post(`/agency/projects/deliverables/${deliverableId}/approve`);
    return response.data;
  },

  deleteDeliverable: async (deliverableId: number) => {
    const response = await api.delete(`/agency/projects/deliverables/${deliverableId}`);
    return response.data;
  },

  // Tasks (Production Kanban)
  getTasks: async (projectId: number, status?: string): Promise<ProjectTask[]> => {
    const response = await api.get(`/agency/projects/${projectId}/tasks`, { params: status ? { status } : undefined });
    return response.data;
  },

  createTask: async (projectId: number, data: {
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    due_date?: string;
    assignee_id?: number;
  }): Promise<ProjectTask> => {
    const response = await api.post(`/agency/projects/${projectId}/tasks`, data);
    return response.data;
  },

  updateTask: async (taskId: number, data: Partial<{
    title: string;
    description: string | null;
    status: string;
    priority: string;
    due_date: string | null;
    assignee_id: number | null;
  }>): Promise<ProjectTask> => {
    const response = await api.patch(`/agency/projects/tasks/${taskId}`, data);
    return response.data;
  },

  deleteTask: async (taskId: number) => {
    const response = await api.delete(`/agency/projects/tasks/${taskId}`);
    return response.data;
  },

  // Assets
  getAssets: async (projectId: number): Promise<ProjectAsset[]> => {
    const response = await api.get(`/agency/projects/${projectId}/assets`);
    return response.data;
  },

  createAsset: async (projectId: number, data: {
    kind?: string;
    name: string;
    url: string;
    version?: string;
    asset_type?: string;
  }): Promise<ProjectAsset> => {
    const response = await api.post(`/agency/projects/${projectId}/assets`, data);
    return response.data;
  },

  deleteAsset: async (assetId: number) => {
    const response = await api.delete(`/agency/projects/assets/${assetId}`);
    return response.data;
  },

  // Activity
  getActivity: async (projectId: number, limit?: number): Promise<ProjectActivityLog[]> => {
    const response = await api.get(`/agency/projects/${projectId}/activity`, { params: limit ? { limit } : undefined });
    return response.data;
  },
};

// ============================================================================
// GOOGLE WORKSPACE API
// ============================================================================

export interface GoogleFolderResponse {
  id: string;
  url: string;
  name?: string;
}

export interface GoogleDocResponse {
  id: string;
  url: string;
  name?: string;
}

export const googleWorkspaceApi = {
  // Check if user has Google Workspace connected (Drive/Docs/Sheets)
  checkGoogleConnection: async (): Promise<{ connected: boolean; email?: string; scopes?: string[] }> => {
    try {
      const response = await api.get("/drive/auth/status");
      return response.data;
    } catch {
      return { connected: false };
    }
  },

  // Get Google auth URL to connect with Drive/Docs/Sheets scopes
  getGoogleAuthUrl: async (redirectPath?: string): Promise<string> => {
    const response = await api.get("/drive/auth/init", {
      params: { redirect: redirectPath || window.location.pathname }
    });
    return response.data.auth_url;
  },

  // Disconnect Google Workspace
  disconnectGoogle: async (): Promise<void> => {
    await api.delete("/drive/auth/disconnect");
  },

  // === CLIENT DRIVE ===
  createClientFolder: async (clientId: number, name?: string): Promise<GoogleFolderResponse> => {
    const response = await api.post(`/drive/clients/${clientId}/folder`, { name });
    return response.data;
  },

  getClientFolder: async (clientId: number): Promise<GoogleFolderResponse | null> => {
    const response = await api.get(`/drive/clients/${clientId}/folder`);
    return response.data;
  },

  // === PROJECT DRIVE ===
  createProjectFolder: async (projectId: number, name?: string): Promise<GoogleFolderResponse> => {
    const response = await api.post(`/drive/projects/${projectId}/folder`, { name });
    return response.data;
  },

  getProjectFolder: async (projectId: number): Promise<GoogleFolderResponse | null> => {
    const response = await api.get(`/drive/projects/${projectId}/folder`);
    return response.data;
  },

  // === PROJECT DOCS ===
  createProjectBrief: async (projectId: number, name?: string, templateId?: string): Promise<GoogleDocResponse> => {
    const response = await api.post(`/drive/projects/${projectId}/brief`, { name, template_id: templateId });
    return response.data;
  },

  createProjectReport: async (projectId: number, name?: string, templateId?: string): Promise<GoogleDocResponse> => {
    const response = await api.post(`/drive/projects/${projectId}/report`, { name, template_id: templateId });
    return response.data;
  },

  // === DELIVERABLE DRIVE ===
  createDeliverableFile: async (deliverableId: number, fileType: "doc" | "sheet", name?: string): Promise<GoogleDocResponse> => {
    const response = await api.post(`/drive/deliverables/${deliverableId}/file`, { file_type: fileType, name });
    return response.data;
  },

  // === UPLOAD TO DRIVE ===
  getUploadToken: async (): Promise<{ access_token: string; expires_in: number }> => {
    const response = await api.get("/drive/upload-token");
    return response.data;
  },

  uploadFileToDrive: async (
    file: File,
    folderId: string,
    fileName?: string,
    onProgress?: (progress: number) => void
  ): Promise<{ id: string; name: string; web_view_link: string; mime_type: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("folder_id", folderId);
    if (fileName) formData.append("file_name", fileName);

    const response = await api.post("/drive/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },
};

// Types for Drive folders
export interface DriveFolderInfo {
  key: string;
  label: string;
  folder_id: string | null;
}

export interface DriveFoldersResponse {
  project_id: number;
  drive_folder_id: string | null;
  folders: DriveFolderInfo[];
}

// Project detail API extension
export const projectDriveApi = {
  getDriveFolders: async (projectId: number): Promise<DriveFoldersResponse> => {
    const response = await api.get(`/agency/projects/${projectId}/drive-folders`);
    return response.data;
  },
};

// ============================================================================
// UNIFIED ASSETS API - Single source of truth
// ============================================================================

export type AssetType = 'DRIVE' | 'FIGMA' | 'DROPBOX' | 'YOUTUBE' | 'LINK' | 'DOC' | 'SHEET' | 'OTHER';
export type AssetStatus = 'DRAFT' | 'FINAL';

export interface Asset {
  id: number;
  project_id: number;
  name: string;
  url: string;
  type: AssetType;
  version: string | null;
  status: AssetStatus | null;
  drive_file_id: string | null;
  drive_folder_id: string | null;
  created_at: string;
  created_by: number | null;
  updated_at: string | null;
  // Computed from joins
  project_name: string | null;
  client_id: number | null;
  client_name: string | null;
}

export interface AssetListResponse {
  items: Asset[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface AssetCreateRequest {
  project_id: number;
  name: string;
  url: string;
  type?: AssetType;
  version?: string;
  status?: AssetStatus;
  drive_file_id?: string;
  drive_folder_id?: string;
}

export interface AssetUpdateRequest {
  name?: string;
  url?: string;
  type?: AssetType;
  version?: string;
  status?: AssetStatus;
  drive_file_id?: string;
  drive_folder_id?: string;
}

export interface AssetFilters {
  project_id?: number;
  client_id?: number;
  type?: AssetType;
  status?: AssetStatus;
  version?: string;
  q?: string;
  page?: number;
  limit?: number;
}

export const assetsApi = {
  /**
   * List all assets with optional filtering
   * Used by both /assets page and project assets tab
   */
  list: async (filters?: AssetFilters): Promise<AssetListResponse> => {
    const params = new URLSearchParams();
    if (filters?.project_id) params.append('project_id', filters.project_id.toString());
    if (filters?.client_id) params.append('client_id', filters.client_id.toString());
    if (filters?.type) params.append('type', filters.type);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.version) params.append('version', filters.version);
    if (filters?.q) params.append('q', filters.q);
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());
    
    const response = await api.get(`/assets?${params.toString()}`);
    return response.data;
  },

  /**
   * Get a single asset by ID
   */
  get: async (assetId: number): Promise<Asset> => {
    const response = await api.get(`/assets/${assetId}`);
    return response.data;
  },

  /**
   * Create a new asset
   */
  create: async (data: AssetCreateRequest): Promise<Asset> => {
    const response = await api.post('/assets', data);
    return response.data;
  },

  /**
   * Update an existing asset
   */
  update: async (assetId: number, data: AssetUpdateRequest): Promise<Asset> => {
    const response = await api.patch(`/assets/${assetId}`, data);
    return response.data;
  },

  /**
   * Delete an asset
   */
  delete: async (assetId: number): Promise<void> => {
    await api.delete(`/assets/${assetId}`);
  },
};

// Asset type configuration for UI
export const ASSET_TYPE_CONFIG: Record<AssetType, { label: string; icon: string; color: string }> = {
  DRIVE: { label: 'Google Drive', icon: 'folder', color: 'text-blue-500' },
  DOC: { label: 'Google Docs', icon: 'file-text', color: 'text-blue-600' },
  SHEET: { label: 'Google Sheets', icon: 'table', color: 'text-green-500' },
  FIGMA: { label: 'Figma', icon: 'image', color: 'text-purple-500' },
  DROPBOX: { label: 'Dropbox', icon: 'cloud', color: 'text-blue-400' },
  YOUTUBE: { label: 'YouTube', icon: 'video', color: 'text-red-500' },
  LINK: { label: 'Lien', icon: 'link', color: 'text-gray-500' },
  OTHER: { label: 'Autre', icon: 'file', color: 'text-gray-400' },
};

export const ASSET_STATUS_CONFIG: Record<AssetStatus, { label: string; color: string }> = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-100 text-gray-700' },
  FINAL: { label: 'Final', color: 'bg-green-100 text-green-700' },
};

// ============================================================================
// GOOGLE CALENDAR API
// ============================================================================

export interface GoogleCalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: string;
  end: string;
  all_day: boolean;
  html_link?: string;
  status?: string;
  location?: string;
}

export interface GoogleCalendarStatus {
  connected: boolean;
  email?: string;
  calendar_id?: string;
}

export const googleCalendarApi = {
  /**
   * Get connection status
   */
  getStatus: async (): Promise<GoogleCalendarStatus> => {
    const response = await api.get('/calendar/google/status');
    return response.data;
  },

  /**
   * Get auth URL to connect Google Calendar
   */
  getAuthUrl: async (): Promise<string> => {
    const response = await api.get('/calendar/google/init');
    return response.data.auth_url || response.request.responseURL;
  },

  /**
   * Disconnect Google Calendar
   */
  disconnect: async (): Promise<void> => {
    await api.delete('/calendar/google/disconnect');
  },

  /**
   * List calendar events
   */
  listEvents: async (startDate?: string, endDate?: string): Promise<GoogleCalendarEvent[]> => {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    
    const response = await api.get('/calendar/google/events', { params });
    return response.data;
  },

  /**
   * List user calendars
   */
  listCalendars: async (): Promise<{ id: string; summary: string; primary: boolean; background_color?: string }[]> => {
    const response = await api.get('/calendar/google/calendars');
    return response.data;
  },

  /**
   * Sync deadlines to Google Calendar
   */
  syncDeadlines: async (opportunityIds?: number[]): Promise<{ success: boolean; events_created: number; errors: string[] }> => {
    const response = await api.post('/calendar/google/sync', { opportunity_ids: opportunityIds });
    return response.data;
  },
};

export default api;
