"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { 
  Search, 
  Trash2, 
  Eye, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Music,
  Music2,
  Users,
  DollarSign,
  Calendar,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Brain,
  Sparkles,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";
import { ArtistSearchBar, JobQueuePanel, EmptyState } from "@/components/artists";
import { toast } from "sonner";

// Spotify icon
const SpotifyIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
  </svg>
);

interface HistoryItem {
  id: string;
  artist_name: string;
  image_url: string | null;
  genre: string | null;
  score: number | null;
  ai_tier: string | null;
  growth_trend: string | null;
  monthly_listeners: number | null;
  fee_min: number | null;
  fee_max: number | null;
  data_quality: string | null;
  last_enriched_at: string | null;
  created_at: string;
}

interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

interface Statistics {
  total_analyses: number;
  unique_artists: number;
  total_budget_min: number;
  total_budget_max: number;
  avg_budget_min: number;
  avg_budget_max: number;
  most_searched_artist: string | null;
  avg_score: number | null;
}

function formatNumber(n: number | null | undefined): string {
  if (!n) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

function getTierBadge(tier: string | null) {
  const tiers: Record<string, { label: string; className: string }> = {
    "S": { label: "S-Tier", className: "bg-gradient-to-r from-amber-400 to-orange-500 text-white" },
    "A": { label: "A-Tier", className: "bg-green-100 text-green-800" },
    "B": { label: "B-Tier", className: "bg-blue-100 text-blue-800" },
    "C": { label: "C-Tier", className: "bg-gray-100 text-gray-800" },
    "RECOMMENDED": { label: "Recommandé", className: "bg-green-100 text-green-800" },
    "TIMING": { label: "À surveiller", className: "bg-amber-100 text-amber-800" },
    "AVOID": { label: "Éviter", className: "bg-red-100 text-red-800" },
  };
  const t = tiers[tier?.toUpperCase() || ""] || { label: tier || "—", className: "bg-gray-100 text-gray-800" };
  return <Badge className={t.className}>{t.label}</Badge>;
}

function getGrowthIcon(trend: string | null) {
  if (!trend) return <Minus className="h-4 w-4 text-gray-400" />;
  const lower = trend.toLowerCase();
  if (["explosive", "rapid", "strong", "rising", "hot"].includes(lower)) {
    return <TrendingUp className="h-4 w-4 text-green-500" />;
  }
  if (["declining", "falling", "cold"].includes(lower)) {
    return <TrendingDown className="h-4 w-4 text-red-500" />;
  }
  return <Minus className="h-4 w-4 text-gray-400" />;
}

function ArtistsPageContent() {
  const [search, setSearch] = useState("");
  const [genre, setGenre] = useState("");
  const [level, setLevel] = useState("");
  const [page, setPage] = useState(1);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const queryClient = useQueryClient();

  // History query
  const { data: history, isLoading: historyLoading } = useQuery<HistoryResponse>({
    queryKey: ["artists-history", page, search, genre, level],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("per_page", "15");
      if (search) params.append("search", search);
      if (genre) params.append("genre", genre);
      if (level) params.append("level", level);
      const response = await api.get(`/api/v1/artists/history?${params.toString()}`);
      return response.data;
    },
  });

  // Statistics query
  const { data: stats, isLoading: statsLoading } = useQuery<Statistics>({
    queryKey: ["artists-stats"],
    queryFn: async () => {
      const response = await api.get("/api/v1/artists/statistics");
      return response.data;
    },
  });

  // Analyze mutation
  const analyzeMutation = useMutation({
    mutationFn: async (resolved: Record<string, any>) => {
      const response = await api.post("/api/v1/artists/analyze", { resolved });
      return response.data;
    },
    onSuccess: (data) => {
      if (data.status === "JOB_CREATED") {
        toast.success("Analyse lancée !", {
          description: "Suivez la progression dans le panneau de droite",
        });
        queryClient.invalidateQueries({ queryKey: ["artist-jobs"] });
      } else if (data.status === "ALREADY_RUNNING") {
        toast.info("Analyse déjà en cours", {
          description: data.message,
        });
      }
      setIsAnalyzing(false);
    },
    onError: (error: any) => {
      toast.error("Erreur", {
        description: error.response?.data?.detail || "Impossible de lancer l'analyse",
      });
      setIsAnalyzing(false);
    },
  });

  // Handle analyze
  const handleAnalyze = useCallback((resolved: Record<string, any>) => {
    setIsAnalyzing(true);
    analyzeMutation.mutate(resolved);
  }, [analyzeMutation]);

  // Handle quick start
  const handleQuickStart = useCallback((example: { name: string; type: string; value: string }) => {
    handleAnalyze({
      display_name: example.value,
      input_type: example.type,
    });
  }, [handleAnalyze]);

  // Refresh artist
  const refreshMutation = useMutation({
    mutationFn: async (artistId: string) => {
      const response = await api.post(`/api/v1/artists/${artistId}/refresh`);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Rafraîchissement lancé");
      queryClient.invalidateQueries({ queryKey: ["artist-jobs"] });
    },
  });

  const hasData = history && history.items.length > 0;
  const isFirstLoad = historyLoading && !history;

  return (
    <div className="container mx-auto py-6 space-y-8">
      {/* ========================================= */}
      {/* HERO SECTION - Search First */}
      {/* ========================================= */}
      <div className="text-center space-y-6 py-8">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight flex items-center justify-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Music2 className="h-6 w-6 text-white" />
            </div>
            Google des Artistes
          </h1>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Analysez n'importe quel artiste en quelques secondes. Score, métriques sociales, 
            estimation de cachet et recommandations personnalisées.
          </p>
        </div>

        {/* Main Search Bar */}
        <ArtistSearchBar
          onAnalyze={handleAnalyze}
          isAnalyzing={isAnalyzing}
        />
      </div>

      {/* ========================================= */}
      {/* MAIN CONTENT */}
      {/* ========================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column - Stats + History */}
        <div className="lg:col-span-3 space-y-6">
          {/* Statistics Cards */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Total Analyses</CardDescription>
                  <CardTitle className="text-3xl flex items-center gap-2">
                    <BarChart3 className="h-6 w-6 text-blue-500" />
                    {stats.total_analyses}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Artistes Uniques</CardDescription>
                  <CardTitle className="text-3xl flex items-center gap-2">
                    <Users className="h-6 w-6 text-purple-500" />
                    {stats.unique_artists}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Budget Total</CardDescription>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <DollarSign className="h-6 w-6 text-green-500" />
                    {formatNumber(stats.total_budget_min)}€ - {formatNumber(stats.total_budget_max)}€
                  </CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    Moy: {formatNumber(stats.avg_budget_min)}€ - {formatNumber(stats.avg_budget_max)}€
                  </p>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Plus Recherché</CardDescription>
                  <CardTitle className="text-xl flex items-center gap-2 truncate">
                    <Sparkles className="h-6 w-6 text-amber-500 flex-shrink-0" />
                    {stats.most_searched_artist || "—"}
                  </CardTitle>
                  {stats.avg_score && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Score moyen: {stats.avg_score.toFixed(0)}/100
                    </p>
                  )}
                </CardHeader>
              </Card>
            </div>
          )}

          {/* Show empty state if no data */}
          {!historyLoading && !hasData && (
            <EmptyState onQuickStart={handleQuickStart} />
          )}

          {/* History Table */}
          {(hasData || historyLoading) && (
            <>
              {/* Filters */}
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col md:flex-row gap-4">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Filtrer les résultats..."
                        value={search}
                        onChange={(e) => {
                          setSearch(e.target.value);
                          setPage(1);
                        }}
                        className="pl-9"
                      />
                    </div>
                    <Select value={genre} onValueChange={(v) => { setGenre(v === "all" ? "" : v); setPage(1); }}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Genre" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tous les genres</SelectItem>
                        <SelectItem value="RAP">Rap</SelectItem>
                        <SelectItem value="POP">Pop</SelectItem>
                        <SelectItem value="ELECTRO">Electro</SelectItem>
                        <SelectItem value="RNB">RnB</SelectItem>
                        <SelectItem value="ROCK">Rock</SelectItem>
                        <SelectItem value="VARIETE">Variété</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select value={level} onValueChange={(v) => { setLevel(v === "all" ? "" : v); setPage(1); }}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Qualité data" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tous</SelectItem>
                        <SelectItem value="HIGH">Haute</SelectItem>
                        <SelectItem value="MEDIUM">Moyenne</SelectItem>
                        <SelectItem value="LOW">Basse</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {/* Table */}
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Artiste</TableHead>
                        <TableHead>Genre</TableHead>
                        <TableHead>Cachet Estimé</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Spotify</TableHead>
                        <TableHead>Tendance</TableHead>
                        <TableHead>Dernière MAJ</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {historyLoading ? (
                        Array.from({ length: 5 }).map((_, i) => (
                          <TableRow key={i}>
                            {Array.from({ length: 8 }).map((_, j) => (
                              <TableCell key={j}>
                                <Skeleton className="h-4 w-full" />
                              </TableCell>
                            ))}
                          </TableRow>
                        ))
                      ) : history?.items.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                            Aucun résultat pour ces filtres.
                          </TableCell>
                        </TableRow>
                      ) : (
                        history?.items.map((item) => (
                          <TableRow key={item.id} className="hover:bg-muted/50">
                            <TableCell>
                              <div className="flex items-center gap-3">
                                <Avatar className="h-10 w-10">
                                  <AvatarImage src={item.image_url || undefined} alt={item.artist_name} />
                                  <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500">
                                    <Music2 className="h-5 w-5 text-white" />
                                  </AvatarFallback>
                                </Avatar>
                                <div>
                                  <div className="font-medium flex items-center gap-2">
                                    {item.artist_name}
                                    {item.score && item.score >= 70 && (
                                      <Brain className="h-4 w-4 text-purple-500" />
                                    )}
                                  </div>
                                  {item.data_quality && (
                                    <Badge variant="outline" className="text-xs">
                                      {item.data_quality}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{item.genre || "—"}</Badge>
                            </TableCell>
                            <TableCell>
                              {item.fee_min && item.fee_max ? (
                                <span className="font-semibold text-green-600">
                                  {item.fee_min.toLocaleString()}€ - {item.fee_max.toLocaleString()}€
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {item.score ? (
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                                  item.score >= 80 ? "bg-green-100 text-green-700" :
                                  item.score >= 60 ? "bg-yellow-100 text-yellow-700" :
                                  item.score >= 40 ? "bg-orange-100 text-orange-700" :
                                  "bg-red-100 text-red-700"
                                }`}>
                                  {item.score}
                                </div>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <SpotifyIcon className="h-4 w-4 text-green-500" />
                                <span>{formatNumber(item.monthly_listeners)}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                {getGrowthIcon(item.growth_trend)}
                                <span className="text-xs capitalize">{item.growth_trend || "—"}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              {item.last_enriched_at ? (
                                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                  <Calendar className="h-3 w-3" />
                                  {formatDistanceToNow(new Date(item.last_enriched_at), {
                                    addSuffix: true,
                                    locale: fr,
                                  })}
                                </div>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => refreshMutation.mutate(item.id)}
                                  disabled={refreshMutation.isPending}
                                  title="Rafraîchir"
                                >
                                  <RefreshCw className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  title="Voir détails"
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Pagination */}
              {history && history.total_pages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Précédent
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} sur {history.total_pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(history.total_pages, p + 1))}
                    disabled={page === history.total_pages}
                  >
                    Suivant
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Right Column - Job Queue */}
        <div className="lg:col-span-1">
          <div className="sticky top-6">
            <JobQueuePanel 
              onViewDetail={(artistId) => {
                window.open(`/discovery/${artistId}`, "_blank");
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ArtistsPage() {
  return (
    <AppLayout>
      <ArtistsPageContent />
    </AppLayout>
  );
}
