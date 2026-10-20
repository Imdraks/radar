"use client";
import Link from "next/link";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Music2,
  Users,
  TrendingUp,
  TrendingDown,
  Clock,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Plus,
  Loader2,
  CheckCircle2,
  Target,
  Shield,
  Zap,
  Globe,
  BarChart3,
  Calendar,
  DollarSign,
  Star,
  Eye,
  Brain,
  Lightbulb,
  MapPin,
  Crown,
  Gem,
  Rocket,
  Sprout,
  Guitar,
  type LucideIcon,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import Image from "next/image";
import { toast } from "sonner";
import { api } from "@/lib/api";

// ============================================================================
// TYPES
// ============================================================================

interface ArtistReason {
  label: string;
  value?: string;
  impact?: number;
}

interface ArtistDetail {
  id: string;
  name: string;
  normalized_name: string;
  viberate_id?: string;
  spotify_id?: string;
  image_url?: string;
  country?: string;
  city?: string;
  genres: string[];
  score: number;
  timing_bucket?: string;
  recommendation?: string;
  monthly_listeners?: number;
  followers?: number;
  velocity?: number;
  acceleration?: number;
  data_quality?: string;
  drivers: ArtistReason[];
  risks: ArtistReason[];
  patterns: string[];
  signals: string[];
  summary?: string;
  evidence?: { source: string; collected_at: string; status: string; error_code?: string; source_url?: string; precision?: string; monthly_listeners_source?: string; contains_deezer_data?: boolean }[];
  missing_data?: string[];
  booking_range?: { min: number; max: number };
  last_enriched_at?: string;
  created_at: string;
  is_stale: boolean;
  has_spotify: boolean;
  has_viberate: boolean;
  // AI Intelligence
  ai_summary?: string;
  ai_tier?: string;
  ai_score?: number;
  growth_trend?: string;
  growth_rate_monthly?: number;
  predicted_listeners_30d?: number;
  predicted_listeners_90d?: number;
  predicted_listeners_180d?: number;
  confidence_score?: number;
  // SWOT
  strengths?: string[];
  weaknesses?: string[];
  opportunities?: string[];
  threats?: string[];
  // Booking Intelligence
  optimal_fee?: number;
  negotiation_power?: string;
  best_booking_window?: string;
  event_type_fit?: Record<string, number>;
  territory_strength?: Record<string, number>;
  seasonal_demand?: Record<string, number>;
  // Content & Viral
  viral_potential?: number;
  best_platforms?: string[];
  content_recommendations?: string[];
  ai_recommendations?: string[];
  // Social breakdown
  instagram_followers?: number;
  tiktok_followers?: number;
  youtube_subscribers?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

const formatNumber = (num?: number | null): string => {
  if (num === undefined || num === null) return "-";
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
};

const getScoreColor = (score: number): string => {
  if (score >= 80) return "text-green-600 dark:text-green-400";
  if (score >= 60) return "text-blue-600 dark:text-blue-400";
  if (score >= 40) return "text-yellow-600 dark:text-yellow-400";
  return "text-gray-600 dark:text-gray-400";
};

const getScoreBg = (score: number): string => {
  if (score >= 80) return "bg-green-100 dark:bg-green-900/30";
  if (score >= 60) return "bg-blue-100 dark:bg-blue-900/30";
  if (score >= 40) return "bg-yellow-100 dark:bg-yellow-900/30";
  return "bg-gray-100 dark:bg-gray-800";
};

const getRecommendationInfo = (rec?: string) => {
  const map: Record<string, { label: string; style: string }> = {
    SIGN: { label: "A signer", style: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" },
    BOOK: { label: "A booker", style: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" },
    WATCH: { label: "A suivre", style: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" },
    WATCHLIST: { label: "Watchlist", style: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" },
    PASS: { label: "Passer", style: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200" },
    IGNORE: { label: "Ignorer", style: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200" },
  };
  return map[rec || ""] || null;
};

const getTimingLabel = (bucket?: string): string => {
  const map: Record<string, string> = {
    IMMINENT: "Imminent",
    "1_3M": "1-3 mois",
    "3_6M": "3-6 mois",
    "6_12M": "6-12 mois",
    LONG: "Long terme",
  };
  return map[bucket || ""] || "-";
};

const getTimingStyle = (bucket?: string): string => {
  const map: Record<string, string> = {
    IMMINENT: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    "1_3M": "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    "3_6M": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    "6_12M": "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    LONG: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
  };
  return map[bucket || ""] || "";
};

const getTrendInfo = (trend?: string) => {
  const map: Record<string, { label: string; color: string; icon: "up" | "down" | "flat" }> = {
    strong_growth: { label: "Forte croissance", color: "text-green-600", icon: "up" },
    growing: { label: "En croissance", color: "text-green-500", icon: "up" },
    stable: { label: "Stable", color: "text-blue-500", icon: "flat" },
    declining: { label: "En baisse", color: "text-orange-500", icon: "down" },
    sharp_decline: { label: "Forte baisse", color: "text-red-500", icon: "down" },
  };
  return map[trend || ""] || { label: trend || "-", color: "text-gray-500", icon: "flat" as const };
};

const getTierInfo = (tier?: string) => {
  const map: Record<string, { label: string; icon: LucideIcon }> = {
    superstar: { label: "Superstar", icon: Crown },
    major: { label: "Major", icon: Star },
    established: { label: "Confirmé", icon: Gem },
    rising: { label: "En montée", icon: Rocket },
    emerging: { label: "Émergent", icon: Sprout },
    underground: { label: "Underground", icon: Guitar },
  };
  return map[tier || ""] || null;
};

const getNegoPowerInfo = (power?: string) => {
  const map: Record<string, { label: string; color: string }> = {
    high: { label: "Fort", color: "text-green-600" },
    medium: { label: "Moyen", color: "text-yellow-600" },
    low: { label: "Faible", color: "text-red-600" },
  };
  return map[power || ""] || { label: "-", color: "text-gray-500" };
};

// ============================================================================
// PAGE
// ============================================================================

export default function DiscoveryArtistDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const artistId = params.id as string;

  const [enrichJobId, setEnrichJobId] = useState<string | null>(null);
  const [enrichStatus, setEnrichStatus] = useState<string | null>(null);
  const [enrichStep, setEnrichStep] = useState<string | null>(null);
  const [enrichProgress, setEnrichProgress] = useState(0);

  const { data: artist, isLoading, error } = useQuery<ArtistDetail>({
    queryKey: ["discovery-artist", artistId],
    queryFn: async () => {
      const res = await api.get(`/discovery/artist/${artistId}`);
      return res.data;
    },
    enabled: !!artistId,
  });

  // Poll enrichment job status
  useEffect(() => {
    if (!enrichJobId) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/discovery/job/${enrichJobId}`);
        const job = res.data;
        setEnrichStatus(job.status);
        setEnrichStep(job.current_step);
        setEnrichProgress(job.progress);
        if (job.status === "COMPLETED" || job.status === "FAILED") {
          clearInterval(interval);
          if (job.status === "COMPLETED") {
            toast.success("Enrichissement terminé !");
            queryClient.invalidateQueries({ queryKey: ["discovery-artist", artistId] });
          } else {
            toast.error(job.error_message || "Erreur lors de l'enrichissement");
          }
          setTimeout(() => {
            setEnrichJobId(null);
            setEnrichStatus(null);
            setEnrichStep(null);
            setEnrichProgress(0);
          }, 3000);
        }
      } catch {
        // ignore polling errors
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [enrichJobId, artistId, queryClient]);

  const handleEnrich = useCallback(async () => {
    try {
      const res = await api.post(`/discovery/artist/${artistId}/refresh`);
      setEnrichJobId(res.data.id);
      setEnrichStatus("RUNNING");
      setEnrichStep("VIBERATE");
      setEnrichProgress(0);
      toast.info("Enrichissement lancé...");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur lors du lancement");
    }
  }, [artistId]);

  const handleAddToArtists = useCallback(async () => {
    try {
      const res = await api.post(`/discovery/artist/${artistId}/refresh`);
      setEnrichJobId(res.data.id);
      setEnrichStatus("RUNNING");
      setEnrichStep("VIBERATE");
      setEnrichProgress(0);
      toast.info("Analyse en cours...");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur lors du lancement");
    }
  }, [artistId]);

  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="container mx-auto p-6 max-w-5xl">
          {/* Back button */}
          <Button
            variant="ghost"
            className="mb-4"
            onClick={() => router.push("/discovery")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>

          {isLoading && (
            <div className="space-y-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          )}

          {error && (
            <Card>
              <CardContent className="p-8 text-center">
                <AlertCircle className="h-12 w-12 mx-auto text-red-400 mb-4" />
                <h2 className="text-xl font-semibold mb-2">Artiste introuvable</h2>
                <p className="text-muted-foreground mb-4">
                  Cet artiste n&apos;existe pas ou a été supprimé.
                </p>
                <Button onClick={() => router.push("/discovery")}>
                  Retour à la découverte
                </Button>
              </CardContent>
            </Card>
          )}

          {artist && (
            <div className="space-y-6">
              {/* ================================================================
                  HEADER CARD
                  ================================================================ */}
              <Card>
                <CardContent className="p-6">
                  {artist.is_stale && (
                    <div className="mb-4 bg-yellow-100 dark:bg-yellow-900/30 px-4 py-2 rounded-lg text-sm text-yellow-800 dark:text-yellow-200 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      Données datant de plus de 24h — pensez à enrichir
                    </div>
                  )}

                  <div className="flex items-start gap-6">
                    {/* Artist image */}
                    <div className="relative w-28 h-28 rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 flex-shrink-0">
                      {artist.image_url ? (
                        <Image
                          src={artist.image_url}
                          alt={artist.name}
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Sparkles className="h-8 w-8 text-gray-400" />
                        </div>
                      )}
                    </div>

                    {/* Artist info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold truncate">{artist.name}</h1>
                        {artist.ai_tier && getTierInfo(artist.ai_tier) && (
                          <Badge variant="outline" className="text-sm flex items-center gap-1">
                            {(() => { const Icon = getTierInfo(artist.ai_tier)!.icon; return <Icon className="h-3.5 w-3.5" />; })()}
                            {getTierInfo(artist.ai_tier)!.label}
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {artist.recommendation && getRecommendationInfo(artist.recommendation) && (
                          <Badge className={getRecommendationInfo(artist.recommendation)!.style}>
                            <Target className="h-3 w-3 mr-1" />
                            {getRecommendationInfo(artist.recommendation)!.label}
                          </Badge>
                        )}
                        {artist.timing_bucket && (
                          <Badge variant="outline" className={getTimingStyle(artist.timing_bucket)}>
                            <Clock className="h-3 w-3 mr-1" />
                            {getTimingLabel(artist.timing_bucket)}
                          </Badge>
                        )}
                        {artist.growth_trend && (
                          <Badge variant="outline" className={getTrendInfo(artist.growth_trend).color}>
                            {getTrendInfo(artist.growth_trend).icon === "up" ? (
                              <TrendingUp className="h-3 w-3 mr-1" />
                            ) : getTrendInfo(artist.growth_trend).icon === "down" ? (
                              <TrendingDown className="h-3 w-3 mr-1" />
                            ) : (
                              <BarChart3 className="h-3 w-3 mr-1" />
                            )}
                            {getTrendInfo(artist.growth_trend).label}
                          </Badge>
                        )}
                        {artist.country && (
                          <Badge variant="outline">
                            <MapPin className="h-3 w-3 mr-1" />
                            {artist.country}
                          </Badge>
                        )}
                        {artist.genres.map((g) => (
                          <Badge key={g} variant="secondary">{g}</Badge>
                        ))}
                      </div>

                      {/* External links */}
                      <div className="flex items-center gap-3 mt-3">
                        {artist.has_spotify && artist.spotify_id && (
                          <a
                            href={`https://open.spotify.com/artist/${artist.spotify_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-green-600 hover:underline flex items-center gap-1"
                          >
                            <Music2 className="h-3.5 w-3.5" />
                            Spotify
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                        {artist.has_viberate && artist.viberate_id && (
                          <a
                            href={artist.viberate_id}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-purple-600 hover:underline flex items-center gap-1"
                          >
                            Viberate
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Score */}
                    <div className={`text-center p-4 rounded-xl ${getScoreBg(artist.score)}`}>
                      <div className={`text-4xl font-bold ${getScoreColor(artist.score)}`}>
                        {artist.score}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">Score</div>
                      <Progress value={artist.score} className="w-20 mt-2" />
                      <div className="text-xs text-muted-foreground mt-1">Indicateur heuristique · confiance non calibrée</div>
                    </div>
                  </div>

                  <div className="mt-4 text-sm space-y-2">
                    <p>Sources et dates de collecte</p>
                    {artist.evidence?.length ? artist.evidence.map(e => <p key={e.source}>{e.source_url ? <a href={e.source_url} target="_blank" rel="noopener noreferrer" className="underline">{e.monthly_listeners_source === 'spotify_public' ? 'Page publique Spotify' : e.source}</a> : e.source}{e.contains_deezer_data ? ' / Deezer' : ''} · {new Date(e.collected_at).toLocaleString('fr-FR')} · {e.status}{e.error_code ? ` (${e.error_code})` : ''}</p>) : <p>Provenance de collecte indisponible.</p>}
                    {!!artist.missing_data?.length && <p>Données manquantes : {artist.missing_data.join(', ')}</p>}
                    <p>Les projections et fourchettes de cachet sont des estimations. Leur précision prédictive n’est pas encore validée.</p>
                    <Link href={`/events?artist=${artist.id}`} className="underline">Ajouter à un événement</Link>
                  </div>
                  {/* Action buttons */}
                  <div className="flex items-center gap-3 mt-5 pt-4 border-t">
                    <Button
                      onClick={handleEnrich}
                      disabled={!!enrichJobId}
                      variant="outline"
                      className="flex-1"
                    >
                      {enrichJobId ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          {enrichStep || "Enrichissement"} ({enrichProgress}%)
                        </>
                      ) : (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Enrichir les données
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={handleAddToArtists}
                      disabled={!!enrichJobId}
                      className="flex-1"
                    >
                      {enrichStatus === "COMPLETED" ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          Ajouté !
                        </>
                      ) : (
                        <>
                          <Plus className="h-4 w-4 mr-2" />
                          Ajouter à mes artistes
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Enrichment progress */}
                  {enrichJobId && (
                    <div className="mt-3">
                      <Progress value={enrichProgress} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1 text-center">
                        {enrichStep === "VIBERATE" && "Récupération des données sociales..."}
                        {enrichStep === "SPOTIFY" && "Scraping Spotify..."}
                        {enrichStep === "COMPUTE" && "Calcul du score et prédictions IA..."}
                        {enrichStatus === "COMPLETED" && "Terminé !"}
                        {enrichStatus === "FAILED" && "Erreur"}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* ================================================================
                  AI SUMMARY
                  ================================================================ */}
              {artist.ai_summary && (
                <Card className="border-purple-200 dark:border-purple-800">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Brain className="h-4 w-4 text-purple-500" />
                      Analyse IA
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed">{artist.ai_summary}</p>
                  </CardContent>
                </Card>
              )}

              {/* ================================================================
                  METRICS GRID
                  ================================================================ */}
              {(() => {
                const metrics = [
                  artist.monthly_listeners != null && {
                    icon: <Users className="h-5 w-5 text-blue-500" />,
                    value: formatNumber(artist.monthly_listeners),
                    label: "Auditeurs / mois",
                  },
                  artist.followers != null && {
                    icon: <Music2 className="h-5 w-5 text-green-500" />,
                    value: formatNumber(artist.followers),
                    label: "Followers Spotify",
                  },
                  artist.instagram_followers != null && artist.instagram_followers > 0 && {
                    icon: <Users className="h-5 w-5 text-pink-500" />,
                    value: formatNumber(artist.instagram_followers),
                    label: "Instagram",
                  },
                  artist.tiktok_followers != null && artist.tiktok_followers > 0 && {
                    icon: <Users className="h-5 w-5 text-gray-800 dark:text-gray-200" />,
                    value: formatNumber(artist.tiktok_followers),
                    label: "TikTok",
                  },
                  artist.youtube_subscribers != null && artist.youtube_subscribers > 0 && {
                    icon: <Users className="h-5 w-5 text-red-500" />,
                    value: formatNumber(artist.youtube_subscribers),
                    label: "YouTube",
                  },
                  artist.velocity != null && {
                    icon: <TrendingUp className="h-5 w-5 text-green-500" />,
                    value: (
                      <span className={artist.velocity >= 0 ? "text-green-600" : "text-red-600"}>
                        {artist.velocity >= 0 ? "+" : ""}{(artist.velocity * 100).toFixed(1)}%
                      </span>
                    ),
                    label: "Vélocité",
                  },
                ].filter(Boolean) as { icon: React.ReactNode; value: React.ReactNode; label: string }[];

                if (metrics.length === 0) {
                  return (
                    <Card>
                      <CardContent className="p-6 text-center text-muted-foreground">
                        <AlertCircle className="h-5 w-5 mx-auto mb-2" />
                        <p className="text-sm">Données limitées — cliquez sur &quot;Enrichir&quot; pour obtenir les métriques.</p>
                      </CardContent>
                    </Card>
                  );
                }

                return (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {metrics.map((m, i) => (
                      <Card key={i}>
                        <CardContent className="p-4 text-center">
                          <div className="flex justify-center mb-1">{m.icon}</div>
                          <div className="text-xl font-bold">{m.value}</div>
                          <div className="text-xs text-muted-foreground">{m.label}</div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                );
              })()}

              {/* ================================================================
                  PREDICTIONS
                  ================================================================ */}
              {artist.predicted_listeners_30d != null && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-500" />
                      Prédictions de croissance
                      {artist.growth_rate_monthly != null && (
                        <Badge variant="outline" className="ml-auto font-normal">
                          {artist.growth_rate_monthly >= 0 ? "+" : ""}{artist.growth_rate_monthly.toFixed(1)}% / mois
                        </Badge>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                        <div className="text-xs text-muted-foreground mb-1">30 jours</div>
                        <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                          {formatNumber(artist.predicted_listeners_30d)}
                        </div>
                        {artist.monthly_listeners && artist.predicted_listeners_30d > artist.monthly_listeners && (
                          <div className="text-xs text-green-600 mt-1">
                            +{formatNumber(artist.predicted_listeners_30d - artist.monthly_listeners)}
                          </div>
                        )}
                      </div>
                      <div className="text-center p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20">
                        <div className="text-xs text-muted-foreground mb-1">90 jours</div>
                        <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                          {formatNumber(artist.predicted_listeners_90d)}
                        </div>
                        {artist.monthly_listeners && artist.predicted_listeners_90d && artist.predicted_listeners_90d > artist.monthly_listeners && (
                          <div className="text-xs text-green-600 mt-1">
                            +{formatNumber(artist.predicted_listeners_90d - artist.monthly_listeners)}
                          </div>
                        )}
                      </div>
                      <div className="text-center p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20">
                        <div className="text-xs text-muted-foreground mb-1">180 jours</div>
                        <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400">
                          {formatNumber(artist.predicted_listeners_180d)}
                        </div>
                        {artist.monthly_listeners && artist.predicted_listeners_180d && artist.predicted_listeners_180d > artist.monthly_listeners && (
                          <div className="text-xs text-green-600 mt-1">
                            +{formatNumber(artist.predicted_listeners_180d - artist.monthly_listeners)}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* ================================================================
                  BOOKING INTELLIGENCE
                  ================================================================ */}
              {(artist.optimal_fee || artist.booking_range || artist.negotiation_power) && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-emerald-500" />
                      Booking Intelligence
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {artist.booking_range && (
                        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                          <div className="text-xs text-muted-foreground">Estimation indicative, à confirmer</div>
                          <div className="text-sm font-semibold">
                            {formatNumber(artist.booking_range.min)} – {formatNumber(artist.booking_range.max)} €
                          </div>
                        </div>
                      )}
                      {artist.negotiation_power && (
                        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                          <div className="text-xs text-muted-foreground">Pouvoir de négo</div>
                          <div className={`text-lg font-bold ${getNegoPowerInfo(artist.negotiation_power).color}`}>
                            {getNegoPowerInfo(artist.negotiation_power).label}
                          </div>
                        </div>
                      )}
                      {artist.best_booking_window && (
                        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                          <div className="text-xs text-muted-foreground">Meilleur timing</div>
                          <div className="text-sm font-semibold">{artist.best_booking_window}</div>
                        </div>
                      )}
                    </div>

                    {/* Event type fit */}
                    {artist.event_type_fit && Object.keys(artist.event_type_fit).length > 0 && (
                      <div className="mt-4">
                        <div className="text-xs text-muted-foreground mb-2">Compatibilité événements</div>
                        <div className="space-y-2">
                          {Object.entries(artist.event_type_fit).map(([type, score]) => (
                            <div key={type} className="flex items-center gap-3">
                              <div className="w-28 text-sm truncate">{type}</div>
                              <Progress value={score} className="flex-1 h-2" />
                              <div className="w-10 text-right text-xs text-muted-foreground">{score}%</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* ================================================================
                  TERRITORY & SEASONAL
                  ================================================================ */}
              {(artist.territory_strength || artist.seasonal_demand) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {artist.territory_strength && Object.keys(artist.territory_strength).length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Globe className="h-4 w-4 text-blue-500" />
                          Force territoriale
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {Object.entries(artist.territory_strength).map(([territory, score]) => (
                            <div key={territory} className="flex items-center gap-3">
                              <div className="w-24 text-sm">{territory}</div>
                              <Progress value={score} className="flex-1 h-2" />
                              <div className="w-10 text-right text-xs text-muted-foreground">{score}%</div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {artist.seasonal_demand && Object.keys(artist.seasonal_demand).length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-orange-500" />
                          Demande saisonnière
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-4 gap-2">
                          {Object.entries(artist.seasonal_demand).map(([quarter, demand]) => (
                            <div key={quarter} className="text-center p-2 rounded-lg bg-gray-50 dark:bg-gray-800">
                              <div className="text-xs text-muted-foreground">{quarter}</div>
                              <div className="text-lg font-bold mt-1">{Math.round(demand * 100)}%</div>
                              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
                                <div
                                  className="bg-orange-500 h-1.5 rounded-full"
                                  style={{ width: `${demand * 100}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* ================================================================
                  SWOT ANALYSIS
                  ================================================================ */}
              {(artist.strengths?.length || artist.weaknesses?.length || artist.opportunities?.length || artist.threats?.length) && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Shield className="h-4 w-4 text-indigo-500" />
                      Analyse SWOT
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {artist.strengths && artist.strengths.length > 0 && (
                        <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                          <div className="text-sm font-semibold text-green-700 dark:text-green-300 mb-2 flex items-center gap-1.5">
                            <CheckCircle2 className="h-4 w-4" />
                            Forces
                          </div>
                          <ul className="space-y-1">
                            {artist.strengths.map((s, i) => (
                              <li key={i} className="text-sm flex items-start gap-1.5">
                                <span className="text-green-500 mt-1">+</span>
                                {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {artist.weaknesses && artist.weaknesses.length > 0 && (
                        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                          <div className="text-sm font-semibold text-red-700 dark:text-red-300 mb-2 flex items-center gap-1.5">
                            <AlertCircle className="h-4 w-4" />
                            Faiblesses
                          </div>
                          <ul className="space-y-1">
                            {artist.weaknesses.map((w, i) => (
                              <li key={i} className="text-sm flex items-start gap-1.5">
                                <span className="text-red-500 mt-1">-</span>
                                {w}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {artist.opportunities && artist.opportunities.length > 0 && (
                        <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                          <div className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-2 flex items-center gap-1.5">
                            <Lightbulb className="h-4 w-4" />
                            Opportunités
                          </div>
                          <ul className="space-y-1">
                            {artist.opportunities.map((o, i) => (
                              <li key={i} className="text-sm flex items-start gap-1.5">
                                <span className="text-blue-500 mt-1">→</span>
                                {o}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {artist.threats && artist.threats.length > 0 && (
                        <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
                          <div className="text-sm font-semibold text-orange-700 dark:text-orange-300 mb-2 flex items-center gap-1.5">
                            <Zap className="h-4 w-4" />
                            Menaces
                          </div>
                          <ul className="space-y-1">
                            {artist.threats.map((t, i) => (
                              <li key={i} className="text-sm flex items-start gap-1.5">
                                <span className="text-orange-500 mt-1">!</span>
                                {t}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* ================================================================
                  DRIVERS & RISKS
                  ================================================================ */}
              {(artist.drivers.length > 0 || artist.risks.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {artist.drivers.length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-green-600 flex items-center gap-2">
                          <Star className="h-4 w-4" />
                          Points forts
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {artist.drivers.map((d, i) => (
                            <li key={i} className="flex items-center gap-2 text-sm">
                              <div className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
                              <span>{d.label}</span>
                              {d.value && (
                                <span className="ml-auto font-medium text-green-600">{d.value}</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                  {artist.risks.length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-red-600 flex items-center gap-2">
                          <AlertCircle className="h-4 w-4" />
                          Risques
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {artist.risks.map((r, i) => (
                            <li key={i} className="flex items-center gap-2 text-sm">
                              <div className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
                              <span>{r.label}</span>
                              {r.value && (
                                <span className="ml-auto font-medium text-red-600">{r.value}</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* ================================================================
                  AI RECOMMENDATIONS
                  ================================================================ */}
              {artist.ai_recommendations && artist.ai_recommendations.length > 0 && (
                <Card className="border-purple-200 dark:border-purple-800">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Lightbulb className="h-4 w-4 text-purple-500" />
                      Recommandations IA
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {artist.ai_recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <span className="text-purple-500 font-bold mt-0.5">{i + 1}.</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* ================================================================
                  CONTENT & PLATFORMS
                  ================================================================ */}
              {(artist.best_platforms?.length || artist.viral_potential != null || artist.content_recommendations?.length) && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Eye className="h-4 w-4 text-pink-500" />
                      Stratégie de contenu
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center gap-4 flex-wrap">
                        {artist.viral_potential != null && (
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4 text-yellow-500" />
                            <span className="text-sm text-muted-foreground">Potentiel viral :</span>
                            <span className="font-bold">{Math.round(artist.viral_potential * 100)}%</span>
                          </div>
                        )}
                        {artist.best_platforms && artist.best_platforms.length > 0 && (
                          <div className="flex items-center gap-2">
                            <Globe className="h-4 w-4 text-blue-500" />
                            <span className="text-sm text-muted-foreground">Plateformes :</span>
                            {artist.best_platforms.map((p, i) => (
                              <Badge key={i} variant="secondary">{p}</Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      {artist.content_recommendations && artist.content_recommendations.length > 0 && (
                        <ul className="space-y-1.5">
                          {artist.content_recommendations.map((c, i) => (
                            <li key={i} className="text-sm flex items-start gap-2">
                              <span className="text-pink-500 mt-0.5">•</span>
                              {c}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* ================================================================
                  SIGNALS & PATTERNS
                  ================================================================ */}
              {(artist.signals.length > 0 || artist.patterns.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {artist.signals.length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-yellow-500" />
                          Signaux
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {artist.signals.map((s, i) => (
                            <Badge key={i} variant="secondary">{typeof s === "object" ? (s as any).type || JSON.stringify(s) : s}</Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {artist.patterns.length > 0 && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                          <BarChart3 className="h-4 w-4 text-indigo-500" />
                          Patterns
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {artist.patterns.map((p, i) => (
                            <Badge key={i} variant="outline">{typeof p === "object" ? (p as any).type || JSON.stringify(p) : p}</Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* ================================================================
                  FOOTER
                  ================================================================ */}
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <div className="flex items-center gap-4">
                      <span>
                        Qualité : <strong>{artist.data_quality || "N/A"}</strong>
                      </span>
                      {artist.last_enriched_at && (
                        <span>
                          Mis à jour : {new Date(artist.last_enriched_at).toLocaleDateString("fr-FR")}
                        </span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
