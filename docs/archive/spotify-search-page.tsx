"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Search,
  Music,
  Users,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  Disc3,
  RefreshCw,
  ChevronRight,
  Brain,
  Sparkles,
  User,
  Mail,
  Building2,
  Youtube,
  Instagram,
  Zap,
  AlertTriangle,
  Lightbulb,
  Shield,
  Calendar,
  Globe,
  Target,
  LineChart,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { api } from "@/lib/api";

// ============================================================================
// ICONS
// ============================================================================

const SpotifyIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
  </svg>
);

const TiktokIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

// ============================================================================
// TYPES
// ============================================================================

interface WebArtistProfile {
  name: string;
  real_name?: string;
  genre: string;
  sub_genres: string[];
  nationality: string;
  birth_year?: number;
  image_url?: string;
  social_metrics: {
    total_followers: number;
    spotify_monthly_listeners: number;
    youtube_subscribers: number;
    youtube_total_views: number;
    instagram_followers: number;
    tiktok_followers: number;
    platforms: Array<{
      platform: string;
      followers: number;
      monthly_listeners: number;
      url?: string;
    }>;
  };
  concerts: {
    upcoming: Array<{
      name: string;
      date?: string;
      venue: string;
      city: string;
      ticket_price_range?: { min?: number; max?: number };
      is_sold_out: boolean;
      source: string;
    }>;
    past: Array<{
      name: string;
      date?: string;
      venue: string;
      city: string;
    }>;
    festivals_played: string[];
  };
  business: {
    record_label?: string;
    management?: string;
    booking_email?: string;
    official_website?: string;
    distributor?: string;
  };
  financials: {
    estimated_fee_min: number;
    estimated_fee_max: number;
    popularity_score: number;
    market_tier: string;
  };
  ai_intelligence?: {
    ai_summary?: string;
    overall_trend?: string;
    risk_score: number;
    opportunity_score: number;
    market_analysis: {
      strengths: string[];
      weaknesses: string[];
      opportunities: string[];
      threats: string[];
    };
    recommendations: string[];
    predictions?: {
      short_term?: { days: number; prediction: string; confidence: number };
      medium_term?: { days: number; prediction: string; confidence: number };
      long_term?: { days: number; prediction: string; confidence: number };
    };
    booking_intelligence?: {
      optimal_fee?: number;
      negotiation_tips?: string[];
      best_booking_window?: string;
      venue_recommendations?: string[];
    };
  };
}

interface TaskResult {
  ready: boolean;
  status: string;
  result?: {
    artist: string;
    status: string;
    result: WebArtistProfile;
    ai_score?: number;
    ai_tier?: string;
  };
  error?: string;
}

interface SearchHistoryItem {
  id: string;
  artist_name: string;
  status: "pending" | "running" | "done" | "error";
  timestamp: Date;
  result?: TaskResult;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatNumber(num: number | undefined): string {
  if (!num) return "N/A";
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(0)}K`;
  return num.toString();
}

function getTrendIcon(trend: string) {
  switch (trend) {
    case "rising":
    case "explosive":
    case "rapid":
    case "strong":
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    case "declining":
    case "falling":
      return <TrendingDown className="h-4 w-4 text-red-500" />;
    default:
      return <Minus className="h-4 w-4 text-gray-500" />;
  }
}

function getTrendLabel(trend: string) {
  const labels: Record<string, string> = {
    rising: "En hausse",
    explosive: "Explosive",
    rapid: "Rapide",
    strong: "Fort",
    moderate: "Modéré",
    stable: "Stable",
    declining: "En baisse",
    falling: "Chute",
  };
  return labels[trend] || trend;
}

function getTierLabel(tier: string) {
  const tiers: Record<string, { label: string; color: string }> = {
    emerging: { label: "Émergent", color: "bg-blue-100 text-blue-800" },
    underground: { label: "Underground", color: "bg-gray-100 text-gray-800" },
    developing: { label: "En développement", color: "bg-cyan-100 text-cyan-800" },
    rising: { label: "Rising", color: "bg-teal-100 text-teal-800" },
    established: { label: "Établi", color: "bg-green-100 text-green-800" },
    major: { label: "Major", color: "bg-purple-100 text-purple-800" },
    star: { label: "Star", color: "bg-yellow-100 text-yellow-800" },
    superstar: { label: "Superstar", color: "bg-orange-100 text-orange-800" },
    mega_star: { label: "Méga Star", color: "bg-red-100 text-red-800" },
  };
  return tiers[tier] || { label: tier, color: "bg-gray-100 text-gray-800" };
}

// ============================================================================
// MAIN PAGE
// ============================================================================

function SpotifySearchPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([]);

  // Mutation pour lancer l'analyse
  const analyzeMutation = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post("/ingestion/analyze-artist", {
        artist_name: name,
        force_refresh: true,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
      setPolling(true);
      toast.success("Analyse lancée !");
      
      // Ajouter à l'historique
      setSearchHistory(prev => [{
        id: data.task_id,
        artist_name: searchQuery,
        status: "running",
        timestamp: new Date(),
      }, ...prev.slice(0, 9)]);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Erreur lors de l'analyse");
    },
  });

  // Query pour le polling du résultat
  const { data: taskStatus } = useQuery<TaskResult>({
    queryKey: ["artist-task", taskId],
    queryFn: async () => {
      const response = await api.get(`/ingestion/task/${taskId}`);
      return response.data;
    },
    enabled: !!taskId && polling,
    refetchInterval: polling ? 2000 : false,
  });

  // Arrêter le polling quand ready
  if (taskStatus?.ready && polling) {
    setPolling(false);
    // Mettre à jour l'historique
    setSearchHistory(prev => prev.map(item => 
      item.id === taskId 
        ? { ...item, status: taskStatus.error ? "error" : "done", result: taskStatus }
        : item
    ));
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length >= 2) {
      analyzeMutation.mutate(searchQuery.trim());
    }
  };

  const handleReset = () => {
    setTaskId(null);
    setPolling(false);
    setSearchQuery("");
    analyzeMutation.reset();
  };

  const handleSelectHistory = (item: SearchHistoryItem) => {
    if (item.result) {
      setTaskId(item.id);
      setSearchQuery(item.artist_name);
    }
  };

  const profile = taskStatus?.result?.result;
  const aiData = profile?.ai_intelligence;
  const aiScore = taskStatus?.result?.ai_score;

  return (
    <AppLayout>
      <ProtectedRoute>
        <div className="container mx-auto py-6 px-4">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 rounded-lg">
                <Brain className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Recherche Artiste</h1>
                <p className="text-muted-foreground">
                  Scan web complet : données, prédictions, SWOT, stratégie booking
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Main content */}
            <div className="lg:col-span-3 space-y-6">
              {/* Search bar */}
              <Card className="border-2 border-purple-200 dark:border-purple-800">
                <CardContent className="p-4">
                  <form onSubmit={handleSearch} className="flex gap-3">
                    <div className="relative flex-1">
                      <Brain className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-purple-500" />
                      <Input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Entrez le nom d'un artiste (ex: PNL, Nekfeu, Aya Nakamura...)"
                        className="pl-11 text-lg h-12"
                        disabled={analyzeMutation.isPending || polling}
                      />
                    </div>
                    <Button
                      type="submit"
                      disabled={analyzeMutation.isPending || polling || searchQuery.trim().length < 2}
                      className="h-12 px-6 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                    >
                      {analyzeMutation.isPending || polling ? (
                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                      ) : (
                        <Brain className="h-5 w-5 mr-2" />
                      )}
                      Analyser
                    </Button>
                  </form>

                  {/* Sources scannées */}
                  <div className="mt-3 flex flex-wrap gap-1">
                    <span className="text-xs text-muted-foreground mr-2">Sources :</span>
                    {["Spotify", "YouTube", "Wikipedia", "Discogs", "Songkick", "Bandsintown", "Ticketmaster", "Google"].map(source => (
                      <Badge key={source} variant="outline" className="text-xs">{source}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Loading state */}
              {polling && (
                <Card className="border-purple-200 dark:border-purple-800">
                  <CardContent className="py-12">
                    <div className="flex flex-col items-center justify-center space-y-4">
                      <div className="relative">
                        <Brain className="h-20 w-20 text-purple-500 animate-pulse" />
                        <Loader2 className="h-10 w-10 animate-spin text-pink-500 absolute -bottom-2 -right-2" />
                      </div>
                      <p className="text-xl font-medium">
                        Analyse en cours pour <strong className="text-purple-600">{searchQuery}</strong>
                      </p>
                      <div className="text-sm text-muted-foreground text-center space-y-1">
                        <p className="flex items-center justify-center gap-1.5"><Search className="h-3.5 w-3.5" /> Scan des sources web (Spotify, YouTube, Viberate...)</p>
                        <p className="flex items-center justify-center gap-1.5"><Brain className="h-3.5 w-3.5" /> Génération des prédictions...</p>
                        <p className="flex items-center justify-center gap-1.5"><LineChart className="h-3.5 w-3.5" /> Calcul du score et analyse SWOT...</p>
                      </div>
                      <div className="w-64">
                        <Progress value={undefined} className="h-2" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Results */}
              {taskStatus?.ready && profile && (
                <Card>
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="text-lg font-semibold">Résultats pour "{profile.name}"</h3>
                      <Button variant="outline" size="sm" onClick={handleReset}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Nouvelle recherche
                      </Button>
                    </div>

                    <Tabs defaultValue="overview" className="w-full">
                      <TabsList className="grid w-full grid-cols-4 mb-4">
                        <TabsTrigger value="overview">Aperçu</TabsTrigger>
                        <TabsTrigger value="ai" className="flex items-center gap-1">
                          <Brain className="h-3 w-3" />
                          IA
                        </TabsTrigger>
                        <TabsTrigger value="predictions">Prédictions</TabsTrigger>
                        <TabsTrigger value="booking">Booking</TabsTrigger>
                      </TabsList>

                      {/* Tab: Overview */}
                      <TabsContent value="overview" className="space-y-4">
                        {/* Artist Header with AI Score */}
                        <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg">
                          <div className="relative">
                            <div className="h-20 w-20 rounded-full overflow-hidden flex items-center justify-center bg-purple-200 dark:bg-purple-800">
                              {profile.image_url ? (
                                <img 
                                  src={profile.image_url} 
                                  alt={profile.name}
                                  className="h-full w-full object-cover"
                                />
                              ) : (
                                <User className="h-10 w-10 text-purple-600 dark:text-purple-300" />
                              )}
                            </div>
                            {aiScore && (
                              <div className={`absolute -bottom-2 -right-2 w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white ${
                                aiScore >= 80 ? "bg-green-500" :
                                aiScore >= 60 ? "bg-yellow-500" :
                                aiScore >= 40 ? "bg-orange-500" :
                                "bg-red-500"
                              }`}>
                                {aiScore.toFixed(0)}
                              </div>
                            )}
                          </div>
                          <div className="flex-1">
                            <h3 className="text-2xl font-bold">{profile.name}</h3>
                            {profile.real_name && (
                              <p className="text-sm text-muted-foreground">({profile.real_name})</p>
                            )}
                            <div className="flex flex-wrap gap-1 mt-2">
                              {profile.genre !== "Unknown" && (
                                <Badge variant="secondary">{profile.genre}</Badge>
                              )}
                              <Badge className={getTierLabel(profile.financials.market_tier).color}>
                                {getTierLabel(profile.financials.market_tier).label}
                              </Badge>
                              {aiData?.overall_trend && (
                                <Badge variant="outline" className="gap-1">
                                  {getTrendIcon(aiData.overall_trend)}
                                  {getTrendLabel(aiData.overall_trend)}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Fee Estimation */}
                        <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium flex items-center gap-2"><Zap className="h-4 w-4 text-green-600" /> Cachet estimé</h4>
                            {aiData?.booking_intelligence?.optimal_fee && (
                              <Badge className="bg-green-600">
                                Optimal: {aiData.booking_intelligence.optimal_fee.toLocaleString()}€
                              </Badge>
                            )}
                          </div>
                          <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                            {profile.financials.estimated_fee_min.toLocaleString()}€ - {profile.financials.estimated_fee_max.toLocaleString()}€
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Score popularité:</span>
                            <Progress value={profile.financials.popularity_score} className="flex-1 h-2" />
                            <span className="text-sm font-medium">{profile.financials.popularity_score.toFixed(0)}/100</span>
                          </div>
                        </div>

                        {/* Social Metrics */}
                        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                          <h4 className="font-medium mb-3 flex items-center gap-2"><LineChart className="h-4 w-4 text-blue-600" /> Métriques Sociales</h4>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {profile.social_metrics.spotify_monthly_listeners > 0 && (
                              <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                                <SpotifyIcon className="h-5 w-5 text-green-500" />
                                <div>
                                  <div className="text-sm font-bold">{formatNumber(profile.social_metrics.spotify_monthly_listeners)}</div>
                                  <div className="text-xs text-muted-foreground">auditeurs/mois</div>
                                </div>
                              </div>
                            )}
                            {profile.social_metrics.youtube_subscribers > 0 && (
                              <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                                <Youtube className="h-5 w-5 text-red-500" />
                                <div>
                                  <div className="text-sm font-bold">{formatNumber(profile.social_metrics.youtube_subscribers)}</div>
                                  <div className="text-xs text-muted-foreground">abonnés</div>
                                </div>
                              </div>
                            )}
                            {profile.social_metrics.instagram_followers > 0 && (
                              <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                                <Instagram className="h-5 w-5 text-pink-500" />
                                <div>
                                  <div className="text-sm font-bold">{formatNumber(profile.social_metrics.instagram_followers)}</div>
                                  <div className="text-xs text-muted-foreground">followers</div>
                                </div>
                              </div>
                            )}
                            {profile.social_metrics.tiktok_followers > 0 && (
                              <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded">
                                <TiktokIcon className="h-5 w-5" />
                                <div>
                                  <div className="text-sm font-bold">{formatNumber(profile.social_metrics.tiktok_followers)}</div>
                                  <div className="text-xs text-muted-foreground">followers</div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Business Info */}
                        {(profile.business.record_label || profile.business.management || profile.business.booking_email) && (
                          <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                            <h4 className="font-medium mb-3 flex items-center gap-2"><Building2 className="h-4 w-4 text-gray-600" /> Contacts Business</h4>
                            <div className="space-y-2 text-sm">
                              {profile.business.record_label && (
                                <div className="flex items-center gap-2">
                                  <Building2 className="h-4 w-4 text-muted-foreground" />
                                  <span>Label: <strong>{profile.business.record_label}</strong></span>
                                </div>
                              )}
                              {profile.business.management && (
                                <div className="flex items-center gap-2">
                                  <User className="h-4 w-4 text-muted-foreground" />
                                  <span>Management: <strong>{profile.business.management}</strong></span>
                                </div>
                              )}
                              {profile.business.booking_email && (
                                <div className="flex items-center gap-2">
                                  <Mail className="h-4 w-4 text-muted-foreground" />
                                  <a href={`mailto:${profile.business.booking_email}`} className="text-blue-600 hover:underline">
                                    {profile.business.booking_email}
                                  </a>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Upcoming Concerts */}
                        {profile.concerts.upcoming.length > 0 && (
                          <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                            <h4 className="font-medium mb-3 flex items-center gap-2"><Music className="h-4 w-4 text-orange-600" /> Prochains concerts</h4>
                            <div className="space-y-2">
                              {profile.concerts.upcoming.slice(0, 5).map((concert, i) => (
                                <div key={i} className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded text-sm">
                                  <div>
                                    <span className="font-medium">{concert.name}</span>
                                    <span className="text-muted-foreground"> - {concert.venue}, {concert.city}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {concert.date && <span className="text-xs">{new Date(concert.date).toLocaleDateString('fr-FR')}</span>}
                                    {concert.is_sold_out && <Badge variant="destructive" className="text-xs">Sold Out</Badge>}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </TabsContent>

                      {/* Tab: AI Intelligence */}
                      <TabsContent value="ai" className="space-y-4">
                        {aiData ? (
                          <>
                            {/* AI Summary */}
                            {aiData.ai_summary && (
                              <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg">
                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                  <Brain className="h-4 w-4 text-purple-500" />
                                  Résumé IA
                                </h4>
                                <p className="text-sm">{aiData.ai_summary}</p>
                              </div>
                            )}

                            {/* SWOT Analysis */}
                            <div className="grid grid-cols-2 gap-3">
                              {aiData.market_analysis.strengths?.length > 0 && (
                                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                  <h5 className="font-medium text-green-700 text-sm mb-2 flex items-center gap-1">
                                    <Zap className="h-3 w-3" /> Forces
                                  </h5>
                                  <ul className="text-xs space-y-1">
                                    {aiData.market_analysis.strengths.slice(0, 4).map((s, i) => (
                                      <li key={i} className="flex items-start gap-1">
                                        <span className="text-green-500">✓</span> {s}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {aiData.market_analysis.weaknesses?.length > 0 && (
                                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                  <h5 className="font-medium text-red-700 text-sm mb-2 flex items-center gap-1">
                                    <AlertTriangle className="h-3 w-3" /> Faiblesses
                                  </h5>
                                  <ul className="text-xs space-y-1">
                                    {aiData.market_analysis.weaknesses.slice(0, 4).map((w, i) => (
                                      <li key={i} className="flex items-start gap-1">
                                        <span className="text-red-500">•</span> {w}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {aiData.market_analysis.opportunities?.length > 0 && (
                                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                  <h5 className="font-medium text-blue-700 text-sm mb-2 flex items-center gap-1">
                                    <Lightbulb className="h-3 w-3" /> Opportunités
                                  </h5>
                                  <ul className="text-xs space-y-1">
                                    {aiData.market_analysis.opportunities.slice(0, 4).map((o, i) => (
                                      <li key={i} className="flex items-start gap-1">
                                        <span className="text-blue-500">→</span> {o}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {aiData.market_analysis.threats?.length > 0 && (
                                <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                                  <h5 className="font-medium text-orange-700 text-sm mb-2 flex items-center gap-1">
                                    <Shield className="h-3 w-3" /> Menaces
                                  </h5>
                                  <ul className="text-xs space-y-1">
                                    {aiData.market_analysis.threats.slice(0, 4).map((t, i) => (
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
                              <div className="p-3 border rounded-lg">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-sm font-medium">Score de Risque</span>
                                  <span className={`text-lg font-bold ${
                                    aiData.risk_score < 0.3 ? "text-green-600" :
                                    aiData.risk_score < 0.6 ? "text-yellow-600" : "text-red-600"
                                  }`}>
                                    {(aiData.risk_score * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <Progress value={aiData.risk_score * 100} className="h-2" />
                              </div>
                              <div className="p-3 border rounded-lg">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-sm font-medium">Score Opportunité</span>
                                  <span className={`text-lg font-bold ${
                                    aiData.opportunity_score > 0.6 ? "text-green-600" :
                                    aiData.opportunity_score > 0.3 ? "text-yellow-600" : "text-red-600"
                                  }`}>
                                    {(aiData.opportunity_score * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <Progress value={aiData.opportunity_score * 100} className="h-2" />
                              </div>
                            </div>

                            {/* AI Recommendations */}
                            {aiData.recommendations?.length > 0 && (
                              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                  <Sparkles className="h-4 w-4 text-yellow-500" />
                                  Recommandations IA
                                </h4>
                                <ul className="text-sm space-y-2">
                                  {aiData.recommendations.slice(0, 5).map((rec, i) => (
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
                            <p>Données IA non disponibles pour cet artiste</p>
                          </div>
                        )}
                      </TabsContent>

                      {/* Tab: Predictions */}
                      <TabsContent value="predictions" className="space-y-4">
                        {aiData?.predictions ? (
                          <div className="space-y-4">
                            <h4 className="font-medium flex items-center gap-2">
                              <LineChart className="h-4 w-4 text-purple-500" />
                              Prédictions de croissance
                            </h4>
                            <div className="grid grid-cols-3 gap-4">
                              {aiData.predictions.short_term && (
                                <div className="p-4 border rounded-lg">
                                  <div className="text-sm text-muted-foreground mb-1">30 jours</div>
                                  <div className="text-lg font-bold">{aiData.predictions.short_term.prediction}</div>
                                  <div className="text-xs text-muted-foreground">
                                    Confiance: {(aiData.predictions.short_term.confidence * 100).toFixed(0)}%
                                  </div>
                                </div>
                              )}
                              {aiData.predictions.medium_term && (
                                <div className="p-4 border rounded-lg">
                                  <div className="text-sm text-muted-foreground mb-1">90 jours</div>
                                  <div className="text-lg font-bold">{aiData.predictions.medium_term.prediction}</div>
                                  <div className="text-xs text-muted-foreground">
                                    Confiance: {(aiData.predictions.medium_term.confidence * 100).toFixed(0)}%
                                  </div>
                                </div>
                              )}
                              {aiData.predictions.long_term && (
                                <div className="p-4 border rounded-lg">
                                  <div className="text-sm text-muted-foreground mb-1">180 jours</div>
                                  <div className="text-lg font-bold">{aiData.predictions.long_term.prediction}</div>
                                  <div className="text-xs text-muted-foreground">
                                    Confiance: {(aiData.predictions.long_term.confidence * 100).toFixed(0)}%
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-8 text-muted-foreground">
                            <LineChart className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>Prédictions non disponibles</p>
                          </div>
                        )}
                      </TabsContent>

                      {/* Tab: Booking */}
                      <TabsContent value="booking" className="space-y-4">
                        {aiData?.booking_intelligence ? (
                          <>
                            {aiData.booking_intelligence.optimal_fee && (
                              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                <h4 className="font-medium mb-2 flex items-center gap-2"><Zap className="h-4 w-4 text-green-600" /> Cachet optimal recommandé</h4>
                                <div className="text-3xl font-bold text-green-600">
                                  {aiData.booking_intelligence.optimal_fee.toLocaleString()}€
                                </div>
                              </div>
                            )}

                            {aiData.booking_intelligence.best_booking_window && (
                              <div className="p-4 border rounded-lg">
                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                  <Calendar className="h-4 w-4" />
                                  Meilleure période de booking
                                </h4>
                                <p>{aiData.booking_intelligence.best_booking_window}</p>
                              </div>
                            )}

                            {(aiData.booking_intelligence.negotiation_tips?.length ?? 0) > 0 && (
                              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                  <Target className="h-4 w-4 text-blue-500" />
                                  Tips de négociation
                                </h4>
                                <ul className="text-sm space-y-1">
                                  {aiData.booking_intelligence.negotiation_tips?.map((tip, i) => (
                                    <li key={i} className="flex items-start gap-2">
                                      <span className="text-blue-500">•</span> {tip}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {(aiData.booking_intelligence.venue_recommendations?.length ?? 0) > 0 && (
                              <div className="p-4 border rounded-lg">
                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                  <Globe className="h-4 w-4" />
                                  Salles recommandées
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                  {aiData.booking_intelligence.venue_recommendations?.map((venue, i) => (
                                    <Badge key={i} variant="secondary">{venue}</Badge>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="text-center py-8 text-muted-foreground">
                            <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>Données booking non disponibles</p>
                          </div>
                        )}
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              )}

              {/* Empty state */}
              {!taskId && !polling && (
                <div className="text-center py-16">
                  <div className="w-24 h-24 bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Brain className="h-12 w-12 text-purple-500" />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">Analyse d'artiste</h3>
                  <p className="text-muted-foreground max-w-md mx-auto mb-6">
                    Entrez le nom d'un artiste pour lancer un scan web complet : 
                    données sociales, prédictions, SWOT, stratégie de booking.
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-w-lg mx-auto text-sm">
                    <div className="flex items-center gap-2 p-2 bg-muted rounded">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Score global
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-muted rounded">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Analyse SWOT
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-muted rounded">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Prédictions 30/90/180j
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-muted rounded">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Cachet estimé
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-muted rounded">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Contacts business
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-muted rounded">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Intelligence booking
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar - History */}
            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Historique</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {searchHistory.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      Aucune recherche récente
                    </p>
                  ) : (
                    searchHistory.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => handleSelectHistory(item)}
                        disabled={item.status === "running"}
                        className="w-full text-left p-3 rounded-lg border hover:bg-muted/50 transition-colors disabled:opacity-50"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {item.status === "running" ? (
                              <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
                            ) : item.status === "done" ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : item.status === "error" ? (
                              <AlertCircle className="h-4 w-4 text-red-500" />
                            ) : (
                              <Clock className="h-4 w-4 text-yellow-500" />
                            )}
                            <span className="font-medium truncate max-w-[150px]">{item.artist_name}</span>
                          </div>
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {item.timestamp.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </button>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Features */}
              <Card className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Brain className="h-4 w-4 text-purple-500" />
                    Fonctionnalités IA
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <SpotifyIcon className="h-4 w-4 text-green-500" />
                    Données Spotify réelles
                  </div>
                  <div className="flex items-center gap-2">
                    <Youtube className="h-4 w-4 text-red-500" />
                    Stats YouTube
                  </div>
                  <div className="flex items-center gap-2">
                    <Instagram className="h-4 w-4 text-pink-500" />
                    Réseaux sociaux
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-orange-500" />
                    Concerts & festivals
                  </div>
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-blue-500" />
                    Intelligence booking
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    </AppLayout>
  );
}

export default SpotifySearchPage;
