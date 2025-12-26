import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

// Use relative URL in production (empty string), localhost in development
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

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
  login: async (email: string, password: string) => {
    const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
      email,
      password,
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

// Opportunities API
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

export default api;
