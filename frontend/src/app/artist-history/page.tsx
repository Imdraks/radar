"use client";

import { useState } from "react";
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
import { 
  Search, 
  Trash2, 
  Eye, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Music,
  Users,
  DollarSign,
  Calendar,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Youtube,
  Instagram,
  Brain,
  Zap,
  Target,
  Shield,
  AlertTriangle,
  Sparkles,
  LineChart,
  Lightbulb,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { format } from "date-fns";
import { fr } from "date-fns/locale";

// Spotify icon component
const SpotifyIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
  </svg>
);

// TikTok icon component  
const TiktokIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

interface ArtistAnalysis {
  id: number;
  artist_name: string;
  real_name?: string;
  genre?: string;
  image_url?: string;  // Photo de l'artiste
  spotify_monthly_listeners: number;
  youtube_subscribers: number;
  instagram_followers: number;
  tiktok_followers: number;
  total_followers: number;
  fee_min: number;
  fee_max: number;
  market_tier?: string;
  popularity_score: number;
  record_label?: string;
  management?: string;
  booking_agency?: string;
  booking_email?: string;
  market_trend: string;
  confidence_score: number;
  sources_scanned?: string;
  created_at: string;
  // AI Intelligence fields
  ai_score?: number;
  ai_tier?: string;
  growth_trend?: string;
  predicted_listeners_30d?: number;
  predicted_listeners_90d?: number;
  predicted_listeners_180d?: number;
  growth_rate_monthly?: number;
  strengths?: string[];
  weaknesses?: string[];
  opportunities?: string[];
  threats?: string[];
  optimal_fee?: number;
  negotiation_power?: string;
  best_booking_window?: string;
  event_type_fit?: Record<string, number>;
  territory_strength?: Record<string, number>;
  seasonal_demand?: Record<string, number>;
  risk_score?: number;
  risk_factors?: string[];
  opportunity_score?: number;
  key_opportunities?: string[];
  best_platforms?: string[];
  engagement_rate?: number;
  viral_potential?: number;
  content_recommendations?: string[];
  ai_summary?: string;
  ai_recommendations?: string[];
}

interface HistoryResponse {
  items: ArtistAnalysis[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

interface Statistics {
  total_analyses: number;
  unique_artists: number;
  avg_fee_min: number;
  avg_fee_max: number;
  total_fee_min: number;
  total_fee_max: number;
  most_searched_artist?: string;
  tier_distribution: Record<string, number>;
  avg_ai_score?: number;
  ai_tier_distribution?: Record<string, number>;
}

function ArtistHistoryContent() {
  const [search, setSearch] = useState("");
  const [genre, setGenre] = useState<string>("");
  const [marketTier, setMarketTier] = useState<string>("");
  const [page, setPage] = useState(1);
  const [selectedAnalysis, setSelectedAnalysis] = useState<ArtistAnalysis | null>(null);
  const queryClient = useQueryClient();

  const { data: history, isLoading } = useQuery<HistoryResponse>({
    queryKey: ["artist-history", page, search, genre, marketTier],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("per_page", "15");
      if (search) params.append("search", search);
      if (genre) params.append("genre", genre);
      if (marketTier) params.append("market_tier", marketTier);
      const response = await api.get(`/artist-history/?${params.toString()}`);
      return response.data;
    },
  });

  const { data: stats } = useQuery<Statistics>({
    queryKey: ["artist-stats"],
    queryFn: async () => {
      const response = await api.get("/artist-history/statistics");
      return response.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/artist-history/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artist-history"] });
      queryClient.invalidateQueries({ queryKey: ["artist-stats"] });
    },
  });

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
    return num.toString();
  };

  const getTierBadge = (tier?: string) => {
    const tiers: Record<string, { label: string; color: string }> = {
      emerging: { label: "Émergent", color: "bg-blue-100 text-blue-800" },
      developing: { label: "En développement", color: "bg-cyan-100 text-cyan-800" },
      established: { label: "Établi", color: "bg-green-100 text-green-800" },
      star: { label: "Star", color: "bg-yellow-100 text-yellow-800" },
      superstar: { label: "Superstar", color: "bg-orange-100 text-orange-800" },
      mega_star: { label: "Méga Star", color: "bg-red-100 text-red-800" },
    };
    const t = tiers[tier || ""] || { label: tier || "N/A", color: "bg-gray-100 text-gray-800" };
    return <Badge className={t.color}>{t.label}</Badge>;
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "rising":
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case "declining":
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <Minus className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Music className="h-8 w-8 text-purple-500" />
            Historique des Analyses
          </h1>
          <p className="text-muted-foreground mt-1">
            Consultez l'historique de toutes les analyses d'artistes
          </p>
        </div>
      </div>

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
              <CardDescription>Budget Total Artistes</CardDescription>
              <CardTitle className="text-2xl flex items-center gap-2">
                <DollarSign className="h-6 w-6 text-green-500" />
                {(stats.total_fee_min || 0).toLocaleString()}€ - {(stats.total_fee_max || 0).toLocaleString()}€
              </CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                Moy: {(stats.avg_fee_min || 0).toLocaleString()}€ - {(stats.avg_fee_max || 0).toLocaleString()}€
              </p>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Plus Recherché</CardDescription>
              <CardTitle className="text-2xl flex items-center gap-2">
                <Music className="h-6 w-6 text-orange-500" />
                {stats.most_searched_artist || "N/A"}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher un artiste..."
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
            <Select value={marketTier} onValueChange={(v) => { setMarketTier(v === "all" ? "" : v); setPage(1); }}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Niveau" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les niveaux</SelectItem>
                <SelectItem value="emerging">Émergent</SelectItem>
                <SelectItem value="developing">En développement</SelectItem>
                <SelectItem value="established">Établi</SelectItem>
                <SelectItem value="star">Star</SelectItem>
                <SelectItem value="superstar">Superstar</SelectItem>
                <SelectItem value="mega_star">Méga Star</SelectItem>
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
                <TableHead>Niveau</TableHead>
                <TableHead>Score IA</TableHead>
                <TableHead>Spotify</TableHead>
                <TableHead>Tendance</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  </TableRow>
                ))
              ) : history?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    Aucune analyse trouvée. Analysez un artiste pour commencer.
                  </TableCell>
                </TableRow>
              ) : (
                history?.items.map((analysis) => (
                  <TableRow key={analysis.id} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelectedAnalysis(analysis)}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        {/* Mini photo de l'artiste */}
                        {analysis.image_url ? (
                          <img 
                            src={analysis.image_url} 
                            alt={analysis.artist_name}
                            className="w-10 h-10 rounded-full object-cover"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                            <Music className="h-5 w-5 text-white" />
                          </div>
                        )}
                        <div>
                          <div className="font-medium flex items-center gap-2">
                            {analysis.artist_name}
                            {analysis.ai_score && analysis.ai_score >= 70 && (
                              <Brain className="h-4 w-4 text-purple-500" />
                            )}
                          </div>
                          {analysis.real_name && (
                            <div className="text-sm text-muted-foreground">
                              ({analysis.real_name})
                            </div>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{analysis.genre || "N/A"}</Badge>
                    </TableCell>
                    <TableCell>
                      <span className="font-semibold text-green-600">
                        {analysis.fee_min.toLocaleString()}€ - {analysis.fee_max.toLocaleString()}€
                      </span>
                    </TableCell>
                    <TableCell>{getTierBadge(analysis.market_tier)}</TableCell>
                    <TableCell>
                      {analysis.ai_score ? (
                        <div className="flex items-center gap-2">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                            analysis.ai_score >= 80 ? "bg-green-100 text-green-700" :
                            analysis.ai_score >= 60 ? "bg-yellow-100 text-yellow-700" :
                            analysis.ai_score >= 40 ? "bg-orange-100 text-orange-700" :
                            "bg-red-100 text-red-700"
                          }`}>
                            {analysis.ai_score.toFixed(0)}
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <SpotifyIcon className="h-4 w-4 text-green-500" />
                        <span>{formatNumber(analysis.spotify_monthly_listeners)}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {analysis.growth_trend ? (
                          <>
                            {analysis.growth_trend === "explosive" || analysis.growth_trend === "rapid" || analysis.growth_trend === "strong" ? (
                              <TrendingUp className="h-4 w-4 text-green-500" />
                            ) : analysis.growth_trend === "declining" || analysis.growth_trend === "falling" ? (
                              <TrendingDown className="h-4 w-4 text-red-500" />
                            ) : (
                              <Minus className="h-4 w-4 text-gray-500" />
                            )}
                            <span className="text-xs capitalize">{analysis.growth_trend}</span>
                          </>
                        ) : (
                          getTrendIcon(analysis.market_trend)
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {format(new Date(analysis.created_at), "dd MMM yyyy HH:mm", { locale: fr })}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAnalysis(analysis);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-red-500 hover:text-red-700"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("Supprimer cette analyse ?")) {
                              deleteMutation.mutate(analysis.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
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
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm">
            Page {page} sur {history.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(history.total_pages, p + 1))}
            disabled={page === history.total_pages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Detail Dialog with AI Intelligence */}
      <Dialog open={!!selectedAnalysis} onOpenChange={() => setSelectedAnalysis(null)}>
        <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-start gap-4">
              {/* Photo de l'artiste */}
              {selectedAnalysis?.image_url ? (
                <img 
                  src={selectedAnalysis.image_url} 
                  alt={selectedAnalysis.artist_name}
                  className="w-20 h-20 rounded-full object-cover shadow-lg"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
                  <Music className="h-10 w-10 text-white" />
                </div>
              )}
              <div className="flex-1">
                <DialogTitle className="flex items-center gap-2">
                  {selectedAnalysis?.artist_name}
                  {selectedAnalysis?.ai_score && (
                    <Badge className={`ml-2 ${
                      selectedAnalysis.ai_score >= 80 ? "bg-green-500" :
                      selectedAnalysis.ai_score >= 60 ? "bg-yellow-500" :
                      selectedAnalysis.ai_score >= 40 ? "bg-orange-500" :
                      "bg-red-500"
                    }`}>
                      Score IA: {selectedAnalysis.ai_score.toFixed(0)}
                    </Badge>
                  )}
                </DialogTitle>
                <DialogDescription>
                  Analyse complète du{" "}
                  {selectedAnalysis && format(new Date(selectedAnalysis.created_at), "dd MMMM yyyy à HH:mm", { locale: fr })}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedAnalysis && (
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Aperçu</TabsTrigger>
                <TabsTrigger value="ai" className="flex items-center gap-1">
                  <Brain className="h-3 w-3" />
                  Intelligence IA
                </TabsTrigger>
                <TabsTrigger value="predictions">Prédictions</TabsTrigger>
                <TabsTrigger value="booking">Booking</TabsTrigger>
              </TabsList>

              {/* Tab: Overview */}
              <TabsContent value="overview" className="space-y-4 mt-4">
                {/* Info */}
                <div className="flex items-center gap-4 flex-wrap">
                  {selectedAnalysis.real_name && (
                    <span className="text-muted-foreground">({selectedAnalysis.real_name})</span>
                  )}
                  <Badge variant="secondary">{selectedAnalysis.genre}</Badge>
                  {getTierBadge(selectedAnalysis.market_tier)}
                  {selectedAnalysis.ai_tier && (
                    <Badge className="bg-purple-100 text-purple-800">
                      AI: {selectedAnalysis.ai_tier}
                    </Badge>
                  )}
                </div>

                {/* Fee */}
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    💰 Cachet estimé
                    {selectedAnalysis.optimal_fee && (
                      <Badge variant="outline" className="text-green-600">
                        Optimal: {selectedAnalysis.optimal_fee.toLocaleString()}€
                      </Badge>
                    )}
                  </h4>
                  <div className="text-3xl font-bold text-green-600">
                    {selectedAnalysis.fee_min.toLocaleString()}€ - {selectedAnalysis.fee_max.toLocaleString()}€
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Score popularité:</span>
                    <Progress value={selectedAnalysis.popularity_score} className="flex-1 h-2" />
                    <span className="text-sm font-medium">{selectedAnalysis.popularity_score.toFixed(0)}/100</span>
                  </div>
                </div>

                {/* Social Metrics */}
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <h4 className="font-medium mb-3">📊 Métriques Sociales</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                      <SpotifyIcon className="h-5 w-5 text-green-500" />
                      <div>
                        <div className="text-sm font-bold">{formatNumber(selectedAnalysis.spotify_monthly_listeners)}</div>
                        <div className="text-xs text-muted-foreground">auditeurs/mois</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                      <Youtube className="h-5 w-5 text-red-500" />
                      <div>
                        <div className="text-sm font-bold">
                          {selectedAnalysis.youtube_subscribers > 0 ? formatNumber(selectedAnalysis.youtube_subscribers) : "—"}
                        </div>
                        <div className="text-xs text-muted-foreground">abonnés</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                      <Instagram className="h-5 w-5 text-pink-500" />
                      <div>
                        <div className="text-sm font-bold">
                          {selectedAnalysis.instagram_followers > 0 ? formatNumber(selectedAnalysis.instagram_followers) : "—"}
                        </div>
                        <div className="text-xs text-muted-foreground">followers</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                      <TiktokIcon className="h-5 w-5" />
                      <div>
                        <div className="text-sm font-bold">
                          {selectedAnalysis.tiktok_followers > 0 ? formatNumber(selectedAnalysis.tiktok_followers) : "—"}
                        </div>
                        <div className="text-xs text-muted-foreground">followers</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Business */}
                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <h4 className="font-medium mb-3">🏢 Contacts Business</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {selectedAnalysis.record_label && (
                      <div><span className="text-muted-foreground">Label:</span> <span className="font-medium">{selectedAnalysis.record_label}</span></div>
                    )}
                    {selectedAnalysis.management && (
                      <div><span className="text-muted-foreground">Management:</span> <span className="font-medium">{selectedAnalysis.management}</span></div>
                    )}
                    {selectedAnalysis.booking_agency && (
                      <div><span className="text-muted-foreground">Booking:</span> <span className="font-medium">{selectedAnalysis.booking_agency}</span></div>
                    )}
                    {selectedAnalysis.booking_email && (
                      <div><span className="text-muted-foreground">Email:</span> <a href={`mailto:${selectedAnalysis.booking_email}`} className="font-medium text-blue-500">{selectedAnalysis.booking_email}</a></div>
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* Tab: AI Intelligence */}
              <TabsContent value="ai" className="space-y-4 mt-4">
                {selectedAnalysis.ai_summary ? (
                  <>
                    {/* AI Summary */}
                    <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg">
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Brain className="h-4 w-4 text-purple-500" />
                        Résumé IA
                      </h4>
                      <p className="text-sm">{selectedAnalysis.ai_summary}</p>
                    </div>

                    {/* SWOT Analysis */}
                    <div className="grid grid-cols-2 gap-3">
                      {selectedAnalysis.strengths && selectedAnalysis.strengths.length > 0 && (
                        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                          <h5 className="font-medium text-green-700 text-sm mb-2 flex items-center gap-1">
                            <Zap className="h-3 w-3" /> Forces
                          </h5>
                          <ul className="text-xs space-y-1">
                            {selectedAnalysis.strengths.slice(0, 3).map((s, i) => (
                              <li key={i} className="flex items-start gap-1">
                                <span className="text-green-500">✓</span> {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {selectedAnalysis.weaknesses && selectedAnalysis.weaknesses.length > 0 && (
                        <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                          <h5 className="font-medium text-red-700 text-sm mb-2 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> Faiblesses
                          </h5>
                          <ul className="text-xs space-y-1">
                            {selectedAnalysis.weaknesses.slice(0, 3).map((w, i) => (
                              <li key={i} className="flex items-start gap-1">
                                <span className="text-red-500">•</span> {w}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {selectedAnalysis.opportunities && selectedAnalysis.opportunities.length > 0 && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                          <h5 className="font-medium text-blue-700 text-sm mb-2 flex items-center gap-1">
                            <Lightbulb className="h-3 w-3" /> Opportunités
                          </h5>
                          <ul className="text-xs space-y-1">
                            {selectedAnalysis.opportunities.slice(0, 3).map((o, i) => (
                              <li key={i} className="flex items-start gap-1">
                                <span className="text-blue-500">→</span> {o}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {selectedAnalysis.threats && selectedAnalysis.threats.length > 0 && (
                        <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                          <h5 className="font-medium text-orange-700 text-sm mb-2 flex items-center gap-1">
                            <Shield className="h-3 w-3" /> Menaces
                          </h5>
                          <ul className="text-xs space-y-1">
                            {selectedAnalysis.threats.slice(0, 3).map((t, i) => (
                              <li key={i} className="flex items-start gap-1">
                                <span className="text-orange-500">!</span> {t}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Risk & Opportunity Scores */}
                    <div className="grid grid-cols-2 gap-4">
                      {selectedAnalysis.risk_score !== undefined && (
                        <div className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">Score de Risque</span>
                            <span className={`text-lg font-bold ${
                              selectedAnalysis.risk_score < 0.3 ? "text-green-600" :
                              selectedAnalysis.risk_score < 0.6 ? "text-yellow-600" : "text-red-600"
                            }`}>
                              {(selectedAnalysis.risk_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <Progress value={selectedAnalysis.risk_score * 100} className="h-2" />
                        </div>
                      )}
                      {selectedAnalysis.opportunity_score !== undefined && (
                        <div className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">Score Opportunité</span>
                            <span className={`text-lg font-bold ${
                              selectedAnalysis.opportunity_score > 0.6 ? "text-green-600" :
                              selectedAnalysis.opportunity_score > 0.3 ? "text-yellow-600" : "text-red-600"
                            }`}>
                              {(selectedAnalysis.opportunity_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <Progress value={selectedAnalysis.opportunity_score * 100} className="h-2" />
                        </div>
                      )}
                    </div>

                    {/* AI Recommendations */}
                    {selectedAnalysis.ai_recommendations && selectedAnalysis.ai_recommendations.length > 0 && (
                      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                        <h4 className="font-medium mb-2 flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-yellow-500" />
                          Recommandations IA
                        </h4>
                        <ul className="text-sm space-y-2">
                          {selectedAnalysis.ai_recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-yellow-500 font-bold">{i + 1}.</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Données IA non disponibles pour cette analyse.</p>
                    <p className="text-sm">Relancez une analyse pour obtenir les insights IA.</p>
                  </div>
                )}
              </TabsContent>

              {/* Tab: Predictions */}
              <TabsContent value="predictions" className="space-y-4 mt-4">
                {selectedAnalysis.predicted_listeners_30d ? (
                  <>
                    {/* Growth Trend */}
                    <div className="p-4 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="font-medium flex items-center gap-2">
                          <LineChart className="h-4 w-4" />
                          Tendance de Croissance
                        </h4>
                        <Badge className={`${
                          selectedAnalysis.growth_trend === "explosive" ? "bg-purple-500" :
                          selectedAnalysis.growth_trend === "rapid" ? "bg-green-500" :
                          selectedAnalysis.growth_trend === "strong" ? "bg-blue-500" :
                          selectedAnalysis.growth_trend === "moderate" ? "bg-yellow-500" :
                          selectedAnalysis.growth_trend === "stable" ? "bg-gray-500" :
                          "bg-red-500"
                        }`}>
                          {selectedAnalysis.growth_trend?.toUpperCase()}
                        </Badge>
                      </div>
                      {selectedAnalysis.growth_rate_monthly && (
                        <div className="text-3xl font-bold">
                          {selectedAnalysis.growth_rate_monthly > 0 ? "+" : ""}
                          {selectedAnalysis.growth_rate_monthly.toFixed(1)}%
                          <span className="text-sm font-normal text-muted-foreground ml-2">/ mois</span>
                        </div>
                      )}
                    </div>

                    {/* Predictions */}
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 border rounded-lg text-center">
                        <div className="text-xs text-muted-foreground mb-1">Dans 30 jours</div>
                        <div className="text-xl font-bold text-blue-600">
                          {formatNumber(selectedAnalysis.predicted_listeners_30d)}
                        </div>
                        <div className="text-xs text-muted-foreground">auditeurs prévus</div>
                      </div>
                      <div className="p-4 border rounded-lg text-center">
                        <div className="text-xs text-muted-foreground mb-1">Dans 90 jours</div>
                        <div className="text-xl font-bold text-green-600">
                          {formatNumber(selectedAnalysis.predicted_listeners_90d || 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">auditeurs prévus</div>
                      </div>
                      <div className="p-4 border rounded-lg text-center">
                        <div className="text-xs text-muted-foreground mb-1">Dans 180 jours</div>
                        <div className="text-xl font-bold text-purple-600">
                          {formatNumber(selectedAnalysis.predicted_listeners_180d || 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">auditeurs prévus</div>
                      </div>
                    </div>

                    {/* Content Strategy */}
                    {selectedAnalysis.best_platforms && selectedAnalysis.best_platforms.length > 0 && (
                      <div className="p-4 bg-pink-50 dark:bg-pink-900/20 rounded-lg">
                        <h4 className="font-medium mb-3">📱 Meilleures Plateformes</h4>
                        <div className="flex flex-wrap gap-2">
                          {selectedAnalysis.best_platforms.map((platform, i) => (
                            <Badge key={i} variant="secondary">{platform}</Badge>
                          ))}
                        </div>
                        {selectedAnalysis.viral_potential !== undefined && (
                          <div className="mt-3 flex items-center gap-2">
                            <span className="text-sm">Potentiel viral:</span>
                            <Progress value={selectedAnalysis.viral_potential * 100} className="flex-1 h-2" />
                            <span className="text-sm font-medium">{(selectedAnalysis.viral_potential * 100).toFixed(0)}%</span>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <LineChart className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Prédictions non disponibles pour cette analyse.</p>
                  </div>
                )}
              </TabsContent>

              {/* Tab: Booking */}
              <TabsContent value="booking" className="space-y-4 mt-4">
                {selectedAnalysis.optimal_fee ? (
                  <>
                    {/* Optimal Fee */}
                    <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg">
                      <h4 className="font-medium mb-2">💎 Cachet Optimal Recommandé</h4>
                      <div className="text-4xl font-bold text-green-600">
                        {selectedAnalysis.optimal_fee.toLocaleString()}€
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        Fourchette: {selectedAnalysis.fee_min.toLocaleString()}€ - {selectedAnalysis.fee_max.toLocaleString()}€
                      </div>
                    </div>

                    {/* Negotiation Info */}
                    <div className="grid grid-cols-2 gap-4">
                      {selectedAnalysis.negotiation_power && (
                        <div className="p-4 border rounded-lg">
                          <div className="text-sm text-muted-foreground mb-1">Pouvoir de négociation</div>
                          <div className={`text-xl font-bold capitalize ${
                            selectedAnalysis.negotiation_power === "high" ? "text-red-600" :
                            selectedAnalysis.negotiation_power === "medium" ? "text-yellow-600" :
                            "text-green-600"
                          }`}>
                            {selectedAnalysis.negotiation_power === "high" ? "🔴 Élevé (Artiste)" :
                             selectedAnalysis.negotiation_power === "medium" ? "🟡 Moyen" :
                             "🟢 Faible (Acheteur)"}
                          </div>
                        </div>
                      )}
                      {selectedAnalysis.best_booking_window && (
                        <div className="p-4 border rounded-lg">
                          <div className="text-sm text-muted-foreground mb-1">Fenêtre de réservation idéale</div>
                          <div className="text-xl font-bold">
                            {selectedAnalysis.best_booking_window}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Event Type Fit */}
                    {selectedAnalysis.event_type_fit && Object.keys(selectedAnalysis.event_type_fit).length > 0 && (
                      <div className="p-4 border rounded-lg">
                        <h4 className="font-medium mb-3">🎪 Compatibilité par Type d'Événement</h4>
                        <div className="space-y-2">
                          {Object.entries(selectedAnalysis.event_type_fit)
                            .sort(([, a], [, b]) => b - a)
                            .map(([type, score]) => (
                              <div key={type} className="flex items-center gap-2">
                                <span className="w-24 text-sm capitalize">{type}</span>
                                <Progress value={score * 100} className="flex-1 h-2" />
                                <span className="text-sm w-12 text-right">{(score * 100).toFixed(0)}%</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Seasonal Demand */}
                    {selectedAnalysis.seasonal_demand && Object.keys(selectedAnalysis.seasonal_demand).length > 0 && (
                      <div className="p-4 border rounded-lg">
                        <h4 className="font-medium mb-3">📅 Demande Saisonnière</h4>
                        <div className="grid grid-cols-4 gap-2">
                          {Object.entries(selectedAnalysis.seasonal_demand).map(([season, score]) => (
                            <div key={season} className="text-center p-2 rounded bg-muted/50">
                              <div className="text-xs text-muted-foreground capitalize">{season}</div>
                              <div className={`text-lg font-bold ${
                                score > 0.7 ? "text-green-600" :
                                score > 0.4 ? "text-yellow-600" :
                                "text-red-600"
                              }`}>
                                {(score * 100).toFixed(0)}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Intelligence Booking non disponible pour cette analyse.</p>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ArtistHistoryPage() {
  return (
    <AppLayout>
      <ArtistHistoryContent />
    </AppLayout>
  );
}
