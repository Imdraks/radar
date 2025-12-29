"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  User, 
  Music, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Mail, 
  Building2,
  Calendar,
  Globe,
  CheckCircle2,
  Youtube,
  Instagram,
  Brain,
  Zap,
  AlertTriangle,
  Lightbulb,
  Shield,
  Sparkles,
  LineChart,
  Target,
} from "lucide-react";

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

interface WebArtistProfile {
  name: string;
  real_name?: string;
  genre: string;
  sub_genres: string[];
  nationality: string;
  birth_year?: number;
  image_url?: string;  // Photo de l'artiste Spotify
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
      ticket_price_range?: {
        min?: number;
        max?: number;
      };
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
  financials: {
    estimated_fee_min: number;
    estimated_fee_max: number;
    market_tier: string;
    popularity_score: number;
  };
  business: {
    record_label?: string;
    management?: string;
    booking_agency?: string;
    booking_email?: string;
  };
  analysis: {
    market_trend: "rising" | "stable" | "declining";
    career_stage: string;
    last_album?: string;
    last_album_year?: number;
    confidence_score: number;
  };
  meta: {
    sources_scanned: string[];
    scan_timestamp: string;
  };
  // AI Intelligence data
  ai_intelligence?: {
    artist_name: string;
    overall_score: number;
    confidence_score: number;
    tier: string;
    overall_trend: string;
    market_analysis: {
      tier: string;
      position: string;
      genre_rank_estimate: number;
      similar_artists: string[];
      strengths: string[];
      weaknesses: string[];
      opportunities: string[];
      threats: string[];
    };
    listener_prediction: {
      current_value: number;
      predicted_30d: number;
      predicted_90d: number;
      predicted_180d: number;
      growth_rate_monthly: number;
      trend: string;
      confidence?: number;
    };
    booking_intelligence: {
      estimated_fee_min: number;
      estimated_fee_max: number;
      optimal_fee: number;
      negotiation_power: string;
      best_booking_window: string;
      event_type_fit: Record<string, number>;
      territory_strength: Record<string, number>;
      seasonal_demand: Record<string, number>;
    };
    content_strategy: {
      best_platforms: string[];
      engagement_rate: number;
      viral_potential: number;
      content_recommendations: string[];
    };
    risk_score: number;
    risk_factors: string[];
    opportunity_score: number;
    key_opportunities: string[];
    ai_summary: string;
    recommendations: string[];
  };
}

interface TaskResult {
  task_id: string;
  status: string;
  ready: boolean;
  result?: {
    artist: string;
    status: string;
    result: WebArtistProfile;
    ai_score?: number;
    ai_tier?: string;
    ai_summary?: string;
  };
  error?: string;
}

export function ArtistAnalysisDialog() {
  const [open, setOpen] = useState(false);
  const [artistName, setArtistName] = useState("");
  const [forceRefresh, setForceRefresh] = useState(true);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const analyzeMutation = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post("/ingestion/analyze-artist", {
        artist_name: name,
        force_refresh: forceRefresh,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
      setPolling(true);
    },
  });

  const { data: taskStatus } = useQuery<TaskResult>({
    queryKey: ["artist-task", taskId],
    queryFn: async () => {
      const response = await api.get(`/ingestion/task/${taskId}`);
      return response.data;
    },
    enabled: !!taskId && polling,
    refetchInterval: polling ? 2000 : false,
  });

  if (taskStatus?.ready && polling) {
    setPolling(false);
  }

  const handleAnalyze = () => {
    if (artistName.trim()) {
      analyzeMutation.mutate(artistName.trim());
    }
  };

  const handleReset = () => {
    setTaskId(null);
    setPolling(false);
    setArtistName("");
    analyzeMutation.reset();
  };

  const getTrendIcon = (trend: string) => {
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
  };

  const getTrendLabel = (trend: string) => {
    const labels: Record<string, string> = {
      rising: "En hausse 🚀",
      explosive: "Explosive 🔥",
      rapid: "Rapide ⚡",
      strong: "Fort 📈",
      moderate: "Modéré",
      stable: "Stable",
      declining: "En baisse",
      falling: "Chute 📉",
    };
    return labels[trend] || trend;
  };

  const getTierLabel = (tier: string) => {
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
  };

  const getEventTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      concert_hall: "Concert",
      concert: "Concert",
      private_event: "Événement",
      event: "Événement",
      festival: "Festival",
      club: "Showcase",
      showcase: "Showcase",
      corporate: "Collaboration",
      collaboration: "Collaboration",
    };
    return labels[type.toLowerCase()] || type;
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
    return num.toString();
  };

  const profile = taskStatus?.result?.result;
  const aiData = profile?.ai_intelligence;
  const aiScore = taskStatus?.result?.ai_score;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <User className="h-4 w-4" />
          Analyser un Artiste
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            Analyse IA d'Artiste
          </DialogTitle>
          <DialogDescription>
            Scan web + Intelligence Artificielle : prédictions, SWOT, stratégie de booking
          </DialogDescription>
        </DialogHeader>

        {!taskId ? (
          <>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Nom de l'artiste</label>
                <Input
                  placeholder="Ex: PNL, Nekfeu, Aya Nakamura, DJ Snake..."
                  value={artistName}
                  onChange={(e) => setArtistName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                  className="text-lg"
                />
              </div>
              
              <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Brain className="h-4 w-4 text-purple-500" />
                  Fonctionnalités IA incluses
                </h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Score IA global (0-100)
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Analyse SWOT
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Prédictions 30/90/180j
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Intelligence Booking
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Risques & Opportunités
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Recommandations IA
                  </div>
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                <p className="font-medium mb-1">Sources scannées :</p>
                <div className="flex flex-wrap gap-1">
                  {["Spotify", "YouTube", "Wikipedia", "Discogs", "Songkick", "Bandsintown", "Ticketmaster", "Fnac", "Google"].map(source => (
                    <Badge key={source} variant="outline" className="text-xs">{source}</Badge>
                  ))}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                onClick={handleAnalyze}
                disabled={!artistName.trim() || analyzeMutation.isPending}
                className="gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              >
                {analyzeMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Brain className="h-4 w-4" />
                )}
                Lancer l'Analyse IA
              </Button>
            </DialogFooter>
          </>
        ) : (
          <ScrollArea className="max-h-[70vh]">
            <div className="py-4 pr-4">
              {polling ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <div className="relative">
                    <Brain className="h-16 w-16 text-purple-500 animate-pulse" />
                    <Loader2 className="h-8 w-8 animate-spin text-blue-500 absolute -bottom-2 -right-2" />
                  </div>
                  <p className="text-lg font-medium">
                    Analyse IA en cours pour <strong>{artistName}</strong>
                  </p>
                  <div className="text-sm text-muted-foreground text-center max-w-md space-y-1">
                    <p>🔍 Scan des sources web...</p>
                    <p>🧠 Génération des prédictions...</p>
                    <p>📊 Calcul du score IA...</p>
                  </div>
                </div>
              ) : taskStatus?.ready && profile ? (
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
                        <h4 className="font-medium flex items-center gap-2">💰 Cachet estimé</h4>
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
                      <h4 className="font-medium mb-3">📊 Métriques Sociales</h4>
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
                        <h4 className="font-medium mb-3">🏢 Contacts Business</h4>
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
                        <p>Données IA en cours de génération...</p>
                      </div>
                    )}
                  </TabsContent>

                  {/* Tab: Predictions */}
                  <TabsContent value="predictions" className="space-y-4">
                    {aiData?.listener_prediction ? (
                      <>
                        {/* Growth Trend - Enhanced Design */}
                        <div className={`p-5 rounded-xl border-2 ${
                          aiData.listener_prediction.trend === "explosive" ? "bg-gradient-to-br from-purple-500/10 via-pink-500/10 to-red-500/10 border-purple-400/50" :
                          aiData.listener_prediction.trend === "rapid" ? "bg-gradient-to-br from-green-500/10 via-emerald-500/10 to-teal-500/10 border-green-400/50" :
                          aiData.listener_prediction.trend === "strong" ? "bg-gradient-to-br from-blue-500/10 via-cyan-500/10 to-sky-500/10 border-blue-400/50" :
                          aiData.listener_prediction.trend === "moderate" ? "bg-gradient-to-br from-yellow-500/10 via-amber-500/10 to-orange-500/10 border-yellow-400/50" :
                          aiData.listener_prediction.trend === "stable" ? "bg-gradient-to-br from-gray-500/10 via-slate-500/10 to-zinc-500/10 border-gray-400/50" :
                          "bg-gradient-to-br from-red-500/10 via-orange-500/10 to-yellow-500/10 border-red-400/50"
                        }`}>
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="font-semibold flex items-center gap-2 text-lg">
                              <LineChart className="h-5 w-5" />
                              Tendance de Croissance
                            </h4>
                            <Badge className={`px-3 py-1 text-sm font-bold ${
                              aiData.listener_prediction.trend === "explosive" ? "bg-purple-500 animate-pulse" :
                              aiData.listener_prediction.trend === "rapid" ? "bg-green-500" :
                              aiData.listener_prediction.trend === "strong" ? "bg-blue-500" :
                              aiData.listener_prediction.trend === "moderate" ? "bg-yellow-500 text-yellow-900" :
                              aiData.listener_prediction.trend === "stable" ? "bg-gray-500" :
                              "bg-red-500"
                            }`}>
                              {aiData.listener_prediction.trend === "explosive" ? "🚀 EXPLOSIVE" :
                               aiData.listener_prediction.trend === "rapid" ? "📈 RAPIDE" :
                               aiData.listener_prediction.trend === "strong" ? "💪 FORTE" :
                               aiData.listener_prediction.trend === "moderate" ? "📊 MODÉRÉE" :
                               aiData.listener_prediction.trend === "stable" ? "➡️ STABLE" :
                               aiData.listener_prediction.trend === "declining" ? "📉 DÉCLIN" :
                               "⬇️ CHUTE"}
                            </Badge>
                          </div>
                          <div className="flex items-baseline gap-2">
                            <span className={`text-4xl font-bold ${
                              aiData.listener_prediction.growth_rate_monthly > 15 ? "text-purple-600 dark:text-purple-400" :
                              aiData.listener_prediction.growth_rate_monthly > 8 ? "text-green-600 dark:text-green-400" :
                              aiData.listener_prediction.growth_rate_monthly > 4 ? "text-blue-600 dark:text-blue-400" :
                              aiData.listener_prediction.growth_rate_monthly > 0 ? "text-yellow-600 dark:text-yellow-400" :
                              "text-red-600 dark:text-red-400"
                            }`}>
                              {aiData.listener_prediction.growth_rate_monthly > 0 ? "+" : ""}
                              {aiData.listener_prediction.growth_rate_monthly?.toFixed(1)}%
                            </span>
                            <span className="text-sm text-muted-foreground">/ mois</span>
                          </div>
                          {/* Growth context message */}
                          <p className="text-sm text-muted-foreground mt-3 italic">
                            {aiData.listener_prediction.growth_rate_monthly > 20 
                              ? "🔥 Croissance exceptionnelle ! Artiste en phase virale."
                              : aiData.listener_prediction.growth_rate_monthly > 10
                              ? "📈 Excellente dynamique. Momentum à capitaliser rapidement."
                              : aiData.listener_prediction.growth_rate_monthly > 5
                              ? "✨ Bonne progression. L'artiste gagne en traction."
                              : aiData.listener_prediction.growth_rate_monthly > 2
                              ? "📊 Croissance stable. Base de fans qui se consolide."
                              : aiData.listener_prediction.growth_rate_monthly > 0
                              ? "🌱 Croissance lente mais régulière."
                              : "⚠️ Attention: audience en régression."}
                          </p>
                        </div>

                        {/* Predictions Cards - Enhanced with Deltas */}
                        <div className="grid grid-cols-3 gap-4">
                          <div className="p-4 border rounded-xl bg-gradient-to-b from-blue-50 to-white dark:from-blue-900/20 dark:to-transparent text-center relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-16 h-16 bg-blue-500/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                            <div className="text-xs text-muted-foreground mb-2 font-medium">Dans 30 jours</div>
                            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                              {formatNumber(aiData.listener_prediction.predicted_30d)}
                            </div>
                            <div className="text-xs text-muted-foreground">auditeurs prévus</div>
                            {aiData.listener_prediction.current_value && (
                              <div className="mt-2 text-xs font-medium text-blue-500">
                                +{formatNumber(aiData.listener_prediction.predicted_30d - aiData.listener_prediction.current_value)} nouveaux
                              </div>
                            )}
                          </div>
                          <div className="p-4 border rounded-xl bg-gradient-to-b from-green-50 to-white dark:from-green-900/20 dark:to-transparent text-center relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-16 h-16 bg-green-500/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                            <div className="text-xs text-muted-foreground mb-2 font-medium">Dans 90 jours</div>
                            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                              {formatNumber(aiData.listener_prediction.predicted_90d)}
                            </div>
                            <div className="text-xs text-muted-foreground">auditeurs prévus</div>
                            {aiData.listener_prediction.current_value && (
                              <div className="mt-2 text-xs font-medium text-green-500">
                                +{formatNumber(aiData.listener_prediction.predicted_90d - aiData.listener_prediction.current_value)} nouveaux
                              </div>
                            )}
                          </div>
                          <div className="p-4 border rounded-xl bg-gradient-to-b from-purple-50 to-white dark:from-purple-900/20 dark:to-transparent text-center relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-16 h-16 bg-purple-500/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                            <div className="text-xs text-muted-foreground mb-2 font-medium">Dans 180 jours</div>
                            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                              {formatNumber(aiData.listener_prediction.predicted_180d)}
                            </div>
                            <div className="text-xs text-muted-foreground">auditeurs prévus</div>
                            {aiData.listener_prediction.current_value && (
                              <div className="mt-2 text-xs font-medium text-purple-500">
                                +{formatNumber(aiData.listener_prediction.predicted_180d - aiData.listener_prediction.current_value)} nouveaux
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Confidence Indicator */}
                        {aiData.listener_prediction.confidence !== undefined && (
                          <div className="p-4 border rounded-lg bg-slate-50 dark:bg-slate-900/50">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium">Confiance de la prédiction</span>
                              <span className={`text-sm font-bold ${
                                aiData.listener_prediction.confidence > 0.7 ? "text-green-600" :
                                aiData.listener_prediction.confidence > 0.4 ? "text-yellow-600" :
                                "text-red-600"
                              }`}>
                                {(aiData.listener_prediction.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <Progress 
                              value={aiData.listener_prediction.confidence * 100} 
                              className="h-2"
                            />
                            <p className="text-xs text-muted-foreground mt-2">
                              {aiData.listener_prediction.confidence > 0.7 
                                ? "Haute fiabilité - basé sur données historiques" 
                                : aiData.listener_prediction.confidence > 0.4
                                ? "Fiabilité moyenne - estimation algorithmique"
                                : "Estimation préliminaire - données limitées"}
                            </p>
                          </div>
                        )}

                        {/* Content Strategy */}
                        {aiData.content_strategy?.best_platforms?.length > 0 && (
                          <div className="p-4 bg-gradient-to-r from-pink-50 to-rose-50 dark:from-pink-900/20 dark:to-rose-900/20 rounded-xl border border-pink-200 dark:border-pink-800">
                            <h4 className="font-semibold mb-3 flex items-center gap-2">
                              📱 Meilleures Plateformes
                            </h4>
                            <div className="flex flex-wrap gap-2 mb-4">
                              {aiData.content_strategy.best_platforms.map((platform, i) => (
                                <Badge key={i} variant="secondary" className="px-3 py-1">
                                  {platform === "TikTok" ? "🎵 " : 
                                   platform === "Instagram" ? "📸 " :
                                   platform === "YouTube" ? "🎬 " :
                                   platform === "Spotify" ? "🎧 " : ""}
                                  {platform}
                                </Badge>
                              ))}
                            </div>
                            {aiData.content_strategy.viral_potential !== undefined && (
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-sm font-medium">Potentiel viral</span>
                                  <span className={`text-sm font-bold ${
                                    aiData.content_strategy.viral_potential > 0.7 ? "text-purple-600" :
                                    aiData.content_strategy.viral_potential > 0.4 ? "text-blue-600" :
                                    "text-gray-600"
                                  }`}>
                                    {(aiData.content_strategy.viral_potential * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <div className="relative">
                                  <Progress value={aiData.content_strategy.viral_potential * 100} className="h-3" />
                                  {aiData.content_strategy.viral_potential > 0.7 && (
                                    <span className="absolute right-0 -top-1 text-xs">🔥</span>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <LineChart className="h-12 w-12 mx-auto mb-4 opacity-50 animate-pulse" />
                        <p>Prédictions en cours de calcul...</p>
                      </div>
                    )}
                  </TabsContent>

                  {/* Tab: Booking */}
                  <TabsContent value="booking" className="space-y-4">
                    {aiData?.booking_intelligence ? (
                      <>
                        {/* Optimal Fee */}
                        <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg">
                          <h4 className="font-medium mb-2">💎 Cachet Optimal Recommandé</h4>
                          <div className="text-4xl font-bold text-green-600">
                            {aiData.booking_intelligence.optimal_fee?.toLocaleString()}€
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Fourchette: {aiData.booking_intelligence.estimated_fee_min?.toLocaleString()}€ - {aiData.booking_intelligence.estimated_fee_max?.toLocaleString()}€
                          </div>
                        </div>

                        {/* Negotiation Info */}
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-4 border rounded-lg">
                            <div className="text-sm text-muted-foreground mb-1">Pouvoir de négociation</div>
                            <div className={`text-xl font-bold ${
                              aiData.booking_intelligence.negotiation_power === "high" ? "text-red-600" :
                              aiData.booking_intelligence.negotiation_power === "medium" ? "text-yellow-600" :
                              "text-green-600"
                            }`}>
                              {aiData.booking_intelligence.negotiation_power === "high" ? "🔴 Élevé (Artiste)" :
                               aiData.booking_intelligence.negotiation_power === "medium" ? "🟡 Moyen" :
                               "🟢 Faible (Acheteur)"}
                            </div>
                          </div>
                          <div className="p-4 border rounded-lg">
                            <div className="text-sm text-muted-foreground mb-1">Fenêtre de réservation</div>
                            <div className="text-xl font-bold">
                              {aiData.booking_intelligence.best_booking_window}
                            </div>
                          </div>
                        </div>

                        {/* Event Type Fit */}
                        {aiData.booking_intelligence.event_type_fit && Object.keys(aiData.booking_intelligence.event_type_fit).length > 0 && (
                          <div className="p-4 border rounded-lg">
                            <h4 className="font-medium mb-3">🎪 Compatibilité par Type</h4>
                            <div className="space-y-2">
                              {Object.entries(aiData.booking_intelligence.event_type_fit)
                                .sort(([, a], [, b]) => b - a)
                                .slice(0, 5)
                                .map(([type, score]) => (
                                  <div key={type} className="flex items-center gap-2">
                                    <span className="w-24 text-sm">{getEventTypeLabel(type)}</span>
                                    <Progress value={score * 100} className="flex-1 h-2" />
                                    <span className="text-sm w-12 text-right">{(score * 100).toFixed(0)}%</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}

                        {/* Seasonal Demand */}
                        {aiData.booking_intelligence.seasonal_demand && Object.keys(aiData.booking_intelligence.seasonal_demand).length > 0 && (
                          <div className="p-4 border rounded-lg">
                            <h4 className="font-medium mb-3">📅 Demande Saisonnière</h4>
                            <div className="grid grid-cols-4 gap-2">
                              {Object.entries(aiData.booking_intelligence.seasonal_demand).map(([season, score]) => (
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
                        <p>Intelligence Booking en cours...</p>
                      </div>
                    )}
                  </TabsContent>

                  {/* Footer Actions */}
                  <div className="flex gap-2 mt-4 pt-4 border-t">
                    <Button onClick={handleReset} variant="outline" className="flex-1">
                      Nouvelle analyse
                    </Button>
                    <Button onClick={() => setOpen(false)} className="flex-1">
                      Fermer
                    </Button>
                  </div>
                </Tabs>
              ) : taskStatus?.error ? (
                <div className="text-center py-8">
                  <p className="text-red-500 mb-4">Erreur: {taskStatus.error}</p>
                  <Button onClick={handleReset} variant="outline">
                    Réessayer
                  </Button>
                </div>
              ) : null}
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  );
}
