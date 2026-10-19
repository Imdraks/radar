"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Rocket,
  TrendingUp,
  RefreshCw,
  Sparkles,
  LayoutGrid,
  List,
  ChevronLeft,
  ChevronRight,
  Search,
  Zap,
  Target,
  DollarSign,
  ArrowRight,
  Music2,
  Star,
  Users,
  Plus,
  Filter,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  ArtistCard,
  ArtistCardData,
  JobQueuePanel,
  JobData,
  SearchBar,
  InputType,
  FeedFiltersBar,
  FeedFilters,
} from "@/components/discovery";

// ============================================================================
// TYPES
// ============================================================================

interface FeedResponse {
  artists: ArtistCardData[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

interface QueueResponse {
  jobs: JobData[];
  running: number;
  pending: number;
  completed_24h: number;
}

interface JobResponse {
  id: string;
  artist_name?: string;
  input_type: string;
  input_value: string;
  status: string;
  current_step: string;
  progress: number;
  started_at: string;
}

// ============================================================================
// DEFAULT VALUES
// ============================================================================

const DEFAULT_FILTERS: FeedFilters = {
  timing: [],
  scoreRange: [0, 100],
  listenersRange: [0, 10000000],
  recommendation: [],
};

// ============================================================================
// API FUNCTIONS
// ============================================================================

const fetchFeed = async (
  feedType: string,
  page: number,
  filters: FeedFilters
): Promise<FeedResponse> => {
  const params = new URLSearchParams();
  params.set("page", page.toString());
  params.set("limit", "20");

  if (filters.timing.length > 0) {
    params.set("timing", filters.timing.join(","));
  }
  if (filters.scoreRange[0] > 0) {
    params.set("score_min", filters.scoreRange[0].toString());
  }
  if (filters.scoreRange[1] < 100) {
    params.set("score_max", filters.scoreRange[1].toString());
  }
  if (filters.listenersRange[0] > 0) {
    params.set("listeners_min", filters.listenersRange[0].toString());
  }
  if (filters.listenersRange[1] < 10000000) {
    params.set("listeners_max", filters.listenersRange[1].toString());
  }
  if (filters.recommendation.length > 0) {
    params.set("recommendation", filters.recommendation.join(","));
  }

  const response = await api.get(`/discovery/feed/${feedType}?${params.toString()}`);
  return response.data;
};

const fetchQueue = async (): Promise<QueueResponse> => {
  const response = await api.get("/discovery/queue");
  return response.data;
};

const searchArtist = async (query: string, inputType: InputType): Promise<JobResponse> => {
  const response = await api.post("/discovery/search", {
    query,
    input_type: inputType,
  });
  return response.data;
};

const refreshArtist = async (artistId: number): Promise<JobResponse> => {
  const response = await api.post(`/discovery/artist/${artistId}/refresh`);
  return response.data;
};

// ============================================================================
// COMPONENTS
// ============================================================================

function FeedSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="flex items-start gap-3 mb-3">
              <Skeleton className="w-16 h-16 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-5 w-32 mb-2" />
                <Skeleton className="h-4 w-24" />
              </div>
              <Skeleton className="h-10 w-10 rounded" />
            </div>
            <div className="grid grid-cols-3 gap-2 mb-3">
              <Skeleton className="h-12 rounded" />
              <Skeleton className="h-12 rounded" />
              <Skeleton className="h-12 rounded" />
            </div>
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function EmptyFeed({ feedType }: { feedType: string }) {
  return (
    <div className="text-center py-16 px-6">
      <div className="w-20 h-20 bg-gradient-to-br from-purple-100 to-violet-100 dark:from-purple-900/30 dark:to-violet-900/30 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
        {feedType === "RECOMMENDED" ? (
          <Rocket className="h-10 w-10 text-purple-500" />
        ) : (
          <TrendingUp className="h-10 w-10 text-violet-500" />
        )}
      </div>
      <h3 className="text-xl font-semibold mb-3">
        {feedType === "RECOMMENDED" ? "Aucune recommandation" : "Pas d'artistes trending"}
      </h3>
      <p className="text-muted-foreground max-w-md mx-auto mb-6">
        {feedType === "RECOMMENDED"
          ? "Analysez des artistes pour construire votre feed personnalisé de recommandations basées sur vos recherches."
          : "Le feed trending se remplit automatiquement avec les artistes en forte croissance de votre historique."}
      </p>
      <Link href="#artist-search">
        <Button className="bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-700 hover:to-violet-700 text-white shadow-md">
          <Search className="h-4 w-4 mr-2" />
          Analyser un artiste
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </Link>
    </div>
  );
}

function Pagination({
  page,
  total,
  limit,
  hasMore,
  onPageChange,
}: {
  page: number;
  total: number;
  limit: number;
  hasMore: boolean;
  onPageChange: (page: number) => void;
}) {
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="flex items-center justify-between py-4">
      <div className="text-sm text-muted-foreground">
        Affichage de {(page - 1) * limit + 1}-{Math.min(page * limit, total)} sur {total}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm">
          Page {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={!hasMore}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// QUICK FILTER CHIPS
// ============================================================================

interface QuickFilter {
  id: string;
  label: string;
  icon: React.ReactNode;
  filter: Partial<FeedFilters>;
}

const QUICK_FILTERS: QuickFilter[] = [
  {
    id: "emerging",
    label: "Émergents",
    icon: <Zap className="h-3.5 w-3.5" />,
    filter: { listenersRange: [0, 50000] as [number, number] },
  },
  {
    id: "rising",
    label: "En hausse",
    icon: <TrendingUp className="h-3.5 w-3.5" />,
    filter: { recommendation: ["SIGN", "WATCH"] },
  },
  {
    id: "budget",
    label: "Petit budget",
    icon: <DollarSign className="h-3.5 w-3.5" />,
    filter: { scoreRange: [40, 70] as [number, number] },
  },
  {
    id: "top-picks",
    label: "Top Picks",
    icon: <Star className="h-3.5 w-3.5" />,
    filter: { scoreRange: [80, 100] as [number, number], recommendation: ["SIGN"] },
  },
];

// ============================================================================
// MAIN PAGE
// ============================================================================

function DiscoveryV3Page() {
  const queryClient = useQueryClient();

  // State
  const [feedType, setFeedType] = useState<"RECOMMENDED" | "TRENDING">("RECOMMENDED");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FeedFilters>(DEFAULT_FILTERS);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [activeQuickFilter, setActiveQuickFilter] = useState<string | null>(null);
  const [lastJobCreated, setLastJobCreated] = useState<{ id: string; input: string } | null>(null);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [feedType, filters]);

  // Queries
  const feedQuery = useQuery({
    queryKey: ["discovery-feed", feedType, page, filters],
    queryFn: () => fetchFeed(feedType, page, filters),
    staleTime: 60 * 1000, // 60 seconds
    refetchInterval: false,
  });

  const queueQuery = useQuery({
    queryKey: ["discovery-queue"],
    queryFn: fetchQueue,
    staleTime: 3 * 1000, // 3 seconds for active jobs
    refetchInterval: (data) => {
      // Refetch every 3s if there are running jobs
      if (data?.state.data?.running && data.state.data.running > 0) {
        return 3000;
      }
      return false;
    },
  });

  // Mutations
  const searchMutation = useMutation({
    mutationFn: ({ query, inputType }: { query: string; inputType: InputType }) =>
      searchArtist(query, inputType),
    onSuccess: (data) => {
      toast.success("Analyse lancée !", {
        description: `L'artiste "${data.input_value}" est en cours d'analyse`,
        duration: 5000,
      });
      // Track last job for visual indicator
      setLastJobCreated({ id: data.id, input: data.input_value });
      // Refetch queue to show new job
      queryClient.invalidateQueries({ queryKey: ["discovery-queue"] });
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail;
      if (detail?.code === "ALREADY_EXISTS") {
        toast.error("Artiste existant", {
          description: detail.message,
        });
      } else {
        toast.error("Erreur", {
          description: error?.response?.data?.detail || "Une erreur est survenue lors de la recherche",
        });
      }
    },
  });

  const refreshMutation = useMutation({
    mutationFn: refreshArtist,
    onSuccess: (data) => {
      toast.success("Rafraîchissement lancé", {
        description: `Job #${data.id} créé`,
      });
      queryClient.invalidateQueries({ queryKey: ["discovery-queue"] });
    },
  });

  // Handlers
  const handleSearch = (query: string, inputType: InputType) => {
    searchMutation.mutate({ query, inputType });
  };

  const handleRefresh = (artistId: number) => {
    refreshMutation.mutate(artistId);
  };

  const handleAddToComparison = (artistId: number) => {
    window.open(`/comparison?add=${artistId}`, "_blank");
    toast.success("Ouverture de la comparaison", {
      description: "Choisissez une sélection pour enregistrer cet artiste",
    });
  };

  const handleViewDetail = (artistId: number) => {
    window.open(`/discovery/${artistId}`, "_blank");
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setActiveQuickFilter(null);
  };

  const applyQuickFilter = (quickFilter: QuickFilter) => {
    if (activeQuickFilter === quickFilter.id) {
      resetFilters();
    } else {
      setFilters({ ...DEFAULT_FILTERS, ...quickFilter.filter });
      setActiveQuickFilter(quickFilter.id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Discovery</h1>
            <p className="text-muted-foreground text-sm">Feed intelligent d'artistes analysés</p>
          </div>
        </div>
        
        {/* Quick Filter Chips */}
        <div className="flex flex-wrap gap-2">
          {QUICK_FILTERS.map((qf) => (
            <button
              key={qf.id}
              onClick={() => applyQuickFilter(qf)}
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                activeQuickFilter === qf.id
                  ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700"
                  : "bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-700"
              }`}
            >
              {qf.icon}
              {qf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search bar */}
      <SearchBar
        onSearch={handleSearch}
        isLoading={searchMutation.isPending}
        placeholder="Rechercher un artiste par nom, URL Spotify ou Viberate..."
      />

      {/* Active analysis indicator */}
      {(queueQuery.data?.running ?? 0) > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0">
              <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Analyse en cours...
              </h4>
              <p className="text-sm text-blue-600 dark:text-blue-300">
                {queueQuery.data?.running} artiste(s) en cours d'enrichissement. 
                Les résultats apparaîtront automatiquement dans le feed.
              </p>
            </div>
            <div className="flex-shrink-0">
              <div className="flex items-center gap-2 text-xs text-blue-600">
                <span className="px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded">
                  Identification
                </span>
                <span>→</span>
                <span className="px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded">
                  Viberate
                </span>
                <span>→</span>
                <span className="px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded">
                  Spotify
                </span>
                <span>→</span>
                <span className="px-2 py-1 bg-blue-100 dark:bg-blue-800 rounded">
                  Calcul
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pending jobs indicator */}
      {(queueQuery.data?.pending ?? 0) > 0 && (queueQuery.data?.running ?? 0) === 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                {queueQuery.data?.pending} analyse(s) en attente
              </h4>
              <p className="text-sm text-yellow-600 dark:text-yellow-300">
                Le worker va bientôt traiter ces demandes.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Layout: Feed + Queue sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main feed area */}
        <div className="lg:col-span-3 space-y-4">
          {/* Tabs + Filters */}
          <Card className="p-4">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <Tabs
                value={feedType}
                onValueChange={(v) => setFeedType(v as "RECOMMENDED" | "TRENDING")}
              >
                <TabsList className="bg-gray-100 dark:bg-gray-800">
                  <TabsTrigger value="RECOMMENDED" className="gap-2 data-[state=active]:bg-white dark:data-[state=active]:bg-gray-700">
                    <Rocket className="h-4 w-4" />
                    Recommandés
                    {feedQuery.data && feedType === "RECOMMENDED" && (
                      <Badge variant="secondary" className="ml-1 text-xs">
                        {feedQuery.data.total}
                      </Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="TRENDING" className="gap-2 data-[state=active]:bg-white dark:data-[state=active]:bg-gray-700">
                    <TrendingUp className="h-4 w-4" />
                    Trending
                    {feedQuery.data && feedType === "TRENDING" && (
                      <Badge variant="secondary" className="ml-1 text-xs">
                        {feedQuery.data.total}
                      </Badge>
                    )}
                  </TabsTrigger>
                </TabsList>
              </Tabs>

              <div className="flex items-center gap-2">
                <FeedFiltersBar
                  filters={filters}
                  onFiltersChange={(f) => {
                    setFilters(f);
                    setActiveQuickFilter(null);
                  }}
                  onReset={resetFilters}
                />

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => feedQuery.refetch()}
                  disabled={feedQuery.isRefetching}
                  className="gap-1"
                >
                  <RefreshCw
                    className={`h-4 w-4 ${feedQuery.isRefetching ? "animate-spin" : ""}`}
                  />
                  <span className="hidden sm:inline">Actualiser</span>
                </Button>

                {/* View mode toggle */}
                <div className="border rounded-lg p-1 flex items-center gap-1 bg-gray-50 dark:bg-gray-800">
                  <Button
                    variant={viewMode === "grid" ? "secondary" : "ghost"}
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => setViewMode("grid")}
                  >
                    <LayoutGrid className="h-4 w-4" />
                  </Button>
                  <Button
                    variant={viewMode === "list" ? "secondary" : "ghost"}
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => setViewMode("list")}
                  >
                    <List className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Active filters indicator */}
            {activeQuickFilter && (
              <div className="mt-3 pt-3 border-t flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Filtre actif:</span>
                <Badge variant="secondary" className="gap-1">
                  {QUICK_FILTERS.find(f => f.id === activeQuickFilter)?.icon}
                  {QUICK_FILTERS.find(f => f.id === activeQuickFilter)?.label}
                  <button
                    onClick={resetFilters}
                    className="ml-1 hover:text-red-500 transition-colors"
                  >
                    ×
                  </button>
                </Badge>
              </div>
            )}
          </Card>

          {/* Feed content */}
          {feedQuery.isLoading ? (
            <FeedSkeleton />
          ) : feedQuery.isError ? (
            <Card className="p-8 text-center border-red-200 dark:border-red-800">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Sparkles className="h-8 w-8 text-red-500" />
              </div>
              <p className="text-red-600 dark:text-red-400 font-medium mb-4">
                Erreur lors du chargement du feed
              </p>
              <Button variant="outline" onClick={() => feedQuery.refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Réessayer
              </Button>
            </Card>
          ) : !feedQuery.data || feedQuery.data.artists.length === 0 ? (
            <Card>
              <EmptyFeed feedType={feedType} />
            </Card>
          ) : (
            <>
              <div
                className={
                  viewMode === "grid"
                    ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
                    : "space-y-3"
                }
              >
                {feedQuery.data.artists.map((artist) => (
                  <ArtistCard
                    key={artist.id}
                    artist={artist}
                    onRefresh={handleRefresh}
                    onAddToComparison={handleAddToComparison}
                    onViewDetail={handleViewDetail}
                    isRefreshing={refreshMutation.isPending}
                  />
                ))}
              </div>

              {/* Pagination */}
              <Card className="p-4">
                <Pagination
                  page={feedQuery.data.page}
                  total={feedQuery.data.total}
                  limit={feedQuery.data.limit}
                  hasMore={feedQuery.data.has_more}
                  onPageChange={setPage}
                />
              </Card>
            </>
          )}
        </div>

        {/* Queue sidebar */}
        <div className="lg:col-span-1">
          <div className="sticky top-4 space-y-4">
            <JobQueuePanel
              jobs={queueQuery.data?.jobs || []}
              runningCount={queueQuery.data?.running || 0}
              pendingCount={queueQuery.data?.pending || 0}
              completedCount={queueQuery.data?.completed_24h || 0}
              isLoading={queueQuery.isLoading}
              onRetry={async (jobId) => {
                try {
                  await api.post(`/discovery/artist/${jobId}/refresh`);
                  toast.success("Relance effectuée", {
                    description: "Le job a été relancé",
                  });
                  queryClient.invalidateQueries({ queryKey: ["discovery-queue"] });
                } catch {
                  toast.error("Erreur lors de la relance");
                }
              }}
            />
            
            {/* Quick Links */}
            <Card className="p-4">
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <Target className="h-4 w-4 text-purple-500" />
                Accès rapide
              </h4>
              <div className="space-y-2">
                <Link href="#artist-search" className="block">
                  <Button variant="outline" size="sm" className="w-full justify-start gap-2">
                    <Search className="h-4 w-4" />
                    Historique des analyses
                  </Button>
                </Link>
                <Link href="/comparison" className="block">
                  <Button variant="outline" size="sm" className="w-full justify-start gap-2">
                    <Users className="h-4 w-4" />
                    Comparer des artistes
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXPORT WITH LAYOUT
// ============================================================================

export default function DiscoveryPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <DiscoveryV3Page />
      </AppLayout>
    </ProtectedRoute>
  );
}
