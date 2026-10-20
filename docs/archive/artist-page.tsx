"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
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
  Loader2,
  AtSign,
  CheckCircle2,
  Clock,
  XCircle,
  RefreshCw,
  Play,
  Sprout,
  Star,
  Crown,
  Building2,
  Smartphone,
  Gem,
  Tent,
  type LucideIcon,
} from "lucide-react";

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

const ViberateIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none"/>
    <path d="M8 12 L11 15 L16 9" stroke="currentColor" strokeWidth="2" fill="none"/>
  </svg>
);

// ============================================================================
// TYPES
// ============================================================================

type InputType = "NAME" | "SPOTIFY_URL" | "VIBERATE_URL";

interface ArtistAnalysis {
  id: number;
  artist_name: string;
  real_name?: string;
  genre?: string;
  image_url?: string;
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

interface JobItem {
  id: number;
  artist_name?: string;
  input_type: string;
  input_value: string;
  status: "QUEUED" | "RUNNING" | "DONE" | "FAILED" | "PARTIAL";
  current_step: string;
  progress: number;
  error_message?: string;
  started_at: string;
  completed_at?: string;
}

interface QueueResponse {
  jobs: JobItem[];
  running: number;
  pending: number;
  completed_24h: number;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const formatNumber = (num: number) => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
  return num.toString();
};

const detectInputType = (value: string): InputType => {
  if (value.includes("open.spotify.com")) return "SPOTIFY_URL";
  if (value.includes("viberate.com")) return "VIBERATE_URL";
  return "NAME";
};

const getTierConfig = (tier?: string) => {
  const tiers: Record<string, { label: string; className: string; icon: LucideIcon }> = {
    emerging: { label: "Émergent", className: "bg-blue-50 text-blue-700 border-blue-200", icon: Sprout },
    developing: { label: "En développement", className: "bg-cyan-50 text-cyan-700 border-cyan-200", icon: TrendingUp },
    established: { label: "Établi", className: "bg-green-50 text-green-700 border-green-200", icon: CheckCircle2 },
    star: { label: "Star", className: "bg-yellow-50 text-yellow-700 border-yellow-200", icon: Star },
    superstar: { label: "Superstar", className: "bg-orange-50 text-orange-700 border-orange-200", icon: Sparkles },
    mega_star: { label: "Méga Star", className: "bg-red-50 text-red-700 border-red-200", icon: Crown },
  };
  return tiers[tier || ""] || { label: tier || "N/A", className: "bg-gray-50 text-gray-700 border-gray-200", icon: Minus };
};

// ============================================================================
// GOOGLE-LIKE SEARCH BAR
// ============================================================================

function GoogleSearchBar({ 
  onSearch, 
  isLoading 
}: { 
  onSearch: (query: string, inputType: InputType) => void;
  isLoading: boolean;
}) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const detectedType = useMemo(() => detectInputType(query), [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 2 && !isLoading) {
      onSearch(query.trim(), detectedType);
    }
  };

  const getTypeIndicator = () => {
    if (!query) return null;
    
    const configs: Record<InputType, { icon: React.ReactNode; label: string; color: string }> = {
      NAME: { icon: <AtSign className="h-3.5 w-3.5" />, label: "Nom", color: "text-gray-500" },
      SPOTIFY_URL: { icon: <SpotifyIcon className="h-3.5 w-3.5" />, label: "Spotify", color: "text-green-500" },
      VIBERATE_URL: { icon: <ViberateIcon className="h-3.5 w-3.5" />, label: "Viberate", color: "text-purple-500" },
    };
    
    const config = configs[detectedType];
    return (
      <div className={`flex items-center gap-1.5 text-xs ${config.color}`}>
        {config.icon}
        <span>{config.label}</span>
      </div>
    );
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className={`
        relative bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 transition-all duration-300 overflow-hidden
        ${isFocused ? "ring-2 ring-purple-500/20" : ""}
      `}>
        <div className="flex items-center px-5 py-4">
          {isLoading ? (
            <Loader2 className="h-5 w-5 text-purple-500 animate-spin mr-4" />
          ) : (
            <Search className="h-5 w-5 text-gray-400 mr-4" />
          )}
          
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Rechercher un artiste (nom, URL Spotify ou Viberate)..."
            disabled={isLoading}
            className="flex-1 bg-transparent border-none outline-none text-lg placeholder:text-gray-400"
          />
          
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full mr-2"
            >
              <XCircle className="h-4 w-4 text-gray-400" />
            </button>
          )}
          
          <Button 
            type="submit" 
            disabled={query.trim().length < 2 || isLoading}
            className="bg-purple-600 hover:bg-purple-700 text-white rounded-xl px-6"
          >
            {isLoading ? "Analyse..." : "Analyser"}
          </Button>
        </div>
        
        {query && (
          <div className="px-5 pb-3 flex items-center justify-between border-t border-gray-100 dark:border-gray-800">
            {getTypeIndicator()}
            <span className="text-xs text-gray-400">
              Appuyez sur Entrée pour lancer l'analyse
            </span>
          </div>
        )}

        {isLoading && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-100 dark:bg-gray-800 overflow-hidden">
            <div className="h-full bg-purple-500 animate-loading rounded-full" 
                 style={{ width: '40%' }} />
          </div>
        )}
      </div>
    </form>
  );
}

// ============================================================================
// ACTIVE JOBS PANEL
// ============================================================================

function ActiveJobsPanel({ jobs }: { jobs: JobItem[] }) {
  const activeJobs = jobs.filter(j => j.status === "QUEUED" || j.status === "RUNNING");
  const recentJobs = jobs.filter(j => j.status !== "QUEUED" && j.status !== "RUNNING").slice(0, 3);
  
  if (activeJobs.length === 0 && recentJobs.length === 0) return null;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "DONE": return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "COMPLETED": return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "PARTIAL": return <CheckCircle2 className="h-4 w-4 text-yellow-500" />;
      case "FAILED": return <XCircle className="h-4 w-4 text-red-500" />;
      case "RUNNING": return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default: return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStepLabel = (step: string) => {
    const labels: Record<string, string> = {
      MATCH: "Recherche...",
      VIBERATE: "Viberate",
      SPOTIFY: "Spotify",
      COMPUTE: "Calcul IA",
      DONE: "Terminé",
    };
    return labels[step] || step;
  };

  return (
    <Card className="border-purple-200/50 bg-gradient-to-br from-purple-50/50 to-white dark:from-purple-900/10 dark:to-gray-900">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Play className="h-4 w-4 text-purple-500" />
          Analyses en cours
          {activeJobs.length > 0 && (
            <Badge variant="secondary" className="ml-auto bg-purple-100 text-purple-700">
              {activeJobs.length} active{activeJobs.length > 1 ? "s" : ""}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {activeJobs.map((job) => (
          <div key={job.id} className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border">
            {getStatusIcon(job.status)}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate">{job.artist_name || job.input_value}</span>
                <Badge variant="outline" className="text-xs shrink-0">
                  {getStepLabel(job.current_step)}
                </Badge>
              </div>
              <Progress value={job.progress} className="h-1.5 mt-1.5" />
            </div>
            <span className="text-xs text-muted-foreground">{job.progress}%</span>
          </div>
        ))}
        
        {recentJobs.length > 0 && (
          <div className="pt-2 border-t space-y-1.5">
            <span className="text-xs text-muted-foreground">Récentes</span>
            {recentJobs.map((job) => (
              <div key={job.id} className="flex items-center gap-2 text-sm">
                {getStatusIcon(job.status)}
                <span className="truncate">{job.artist_name || job.input_value}</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {format(new Date(job.started_at), "HH:mm")}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// STAT CARD
// ============================================================================

function StatCard({ 
  title, 
  value, 
  subtitle,
  icon: Icon, 
  iconColor,
}: { 
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  iconColor: string;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <span className="text-2xl font-bold tracking-tight">{value}</span>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className={`p-2.5 rounded-xl ${iconColor}`}>
            <Icon className="h-5 w-5 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// ARTIST TABLE ROW
// ============================================================================

function ArtistTableRow({ 
  analysis, 
  onView, 
  onDelete 
}: { 
  analysis: ArtistAnalysis;
  onView: () => void;
  onDelete: () => void;
}) {
  const tierConfig = getTierConfig(analysis.market_tier);
  
  return (
    <TableRow className="group cursor-pointer hover:bg-gray-50/50 dark:hover:bg-gray-800/50" onClick={onView}>
      <TableCell>
        <div className="flex items-center gap-3">
          {analysis.image_url ? (
            <img 
              src={analysis.image_url} 
              alt={analysis.artist_name}
              className="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center ring-2 ring-gray-100">
              <Music className="h-5 w-5 text-white" />
            </div>
          )}
          <div>
            <div className="font-medium flex items-center gap-2">
              {analysis.artist_name}
              {(analysis.ai_score ?? 0) > 0 && analysis.ai_score! >= 70 && (
                <Brain className="h-3.5 w-3.5 text-purple-500" />
              )}
            </div>
            {analysis.real_name && (
              <div className="text-xs text-muted-foreground">{analysis.real_name}</div>
            )}
          </div>
        </div>
      </TableCell>
      
      <TableCell>
        <Badge variant="outline" className="font-normal">{analysis.genre || "—"}</Badge>
      </TableCell>
      
      <TableCell>
        <div className="flex items-center gap-1.5">
          <DollarSign className="h-3.5 w-3.5 text-green-500" />
          <span className="font-semibold text-green-700 dark:text-green-400">
            {analysis.fee_min.toLocaleString()}€ - {analysis.fee_max.toLocaleString()}€
          </span>
        </div>
      </TableCell>
      
      <TableCell>
        <Badge variant="outline" className={`${tierConfig.className} border flex items-center gap-1`}>
          {(() => { const Icon = tierConfig.icon; return <Icon className="h-3 w-3" />; })()}
          {tierConfig.label}
        </Badge>
      </TableCell>
      
      <TableCell>
        {analysis.ai_score ? (
          <div className={`
            inline-flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold
            ${analysis.ai_score >= 80 ? "bg-green-100 text-green-700" :
              analysis.ai_score >= 60 ? "bg-yellow-100 text-yellow-700" :
              analysis.ai_score >= 40 ? "bg-orange-100 text-orange-700" :
              "bg-red-100 text-red-700"}
          `}>
            {analysis.ai_score.toFixed(0)}
          </div>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </TableCell>
      
      <TableCell>
        <div className="flex items-center gap-1.5">
          <SpotifyIcon className="h-4 w-4 text-green-500" />
          <span className="font-medium">{formatNumber(analysis.spotify_monthly_listeners)}</span>
        </div>
      </TableCell>
      
      <TableCell>
        <div className="flex items-center gap-1.5">
          {analysis.growth_trend === "explosive" || analysis.growth_trend === "rapid" || analysis.growth_trend === "strong" ? (
            <>
              <TrendingUp className="h-4 w-4 text-green-500" />
              <span className="text-xs text-green-600 capitalize">{analysis.growth_trend}</span>
            </>
          ) : analysis.growth_trend === "declining" || analysis.growth_trend === "falling" ? (
            <>
              <TrendingDown className="h-4 w-4 text-red-500" />
              <span className="text-xs text-red-600 capitalize">{analysis.growth_trend}</span>
            </>
          ) : analysis.market_trend === "rising" ? (
            <TrendingUp className="h-4 w-4 text-green-500" />
          ) : analysis.market_trend === "declining" ? (
            <TrendingDown className="h-4 w-4 text-red-500" />
          ) : (
            <Minus className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </TableCell>
      
      <TableCell>
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          {format(new Date(analysis.created_at), "dd MMM yyyy", { locale: fr })}
        </div>
      </TableCell>
      
      <TableCell>
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={(e) => { e.stopPropagation(); onView(); }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
            onClick={(e) => {
              e.stopPropagation();
              if (confirm("Supprimer cette analyse ?")) onDelete();
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ============================================================================
// ARTIST DETAIL DIALOG
// ============================================================================

function ArtistDetailDialog({ 
  analysis, 
  open, 
  onOpenChange 
}: { 
  analysis: ArtistAnalysis | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!analysis) return null;
  const tierConfig = getTierConfig(analysis.market_tier);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start gap-4">
            {analysis.image_url ? (
              <img src={analysis.image_url} alt={analysis.artist_name} className="w-20 h-20 rounded-xl object-cover shadow-lg ring-2 ring-gray-100" />
            ) : (
              <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
                <Music className="h-10 w-10 text-white" />
              </div>
            )}
            <div className="flex-1 space-y-2">
              <DialogTitle className="text-xl flex items-center gap-3">
                {analysis.artist_name}
                {analysis.ai_score && (
                  <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-semibold ${analysis.ai_score >= 80 ? "bg-green-100 text-green-700" : analysis.ai_score >= 60 ? "bg-yellow-100 text-yellow-700" : analysis.ai_score >= 40 ? "bg-orange-100 text-orange-700" : "bg-red-100 text-red-700"}`}>
                    <Brain className="h-3.5 w-3.5" />
                    Score: {analysis.ai_score.toFixed(0)}
                  </div>
                )}
              </DialogTitle>
              <DialogDescription className="flex items-center gap-2 flex-wrap">
                {analysis.real_name && <span>({analysis.real_name})</span>}
                <Badge variant="outline">{analysis.genre || "Genre inconnu"}</Badge>
                <Badge variant="outline" className={tierConfig.className}>{(() => { const Icon = tierConfig.icon; return <Icon className="h-3 w-3 mr-1 inline" />; })()} {tierConfig.label}</Badge>
                <span className="text-xs">Analysé le {format(new Date(analysis.created_at), "dd MMMM yyyy à HH:mm", { locale: fr })}</span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full mt-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Aperçu</TabsTrigger>
            <TabsTrigger value="ai" className="flex items-center gap-1.5"><Brain className="h-3.5 w-3.5" />IA</TabsTrigger>
            <TabsTrigger value="predictions">Prédictions</TabsTrigger>
            <TabsTrigger value="booking">Booking</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 mt-4">
            <div className="p-5 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold flex items-center gap-2"><DollarSign className="h-4 w-4 text-green-600" /> Cachet estimé</h4>
                {analysis.optimal_fee && <Badge className="bg-green-600 text-white">Optimal: {analysis.optimal_fee.toLocaleString()}€</Badge>}
              </div>
              <div className="text-3xl font-bold text-green-700 dark:text-green-400">
                {analysis.fee_min.toLocaleString()}€ - {analysis.fee_max.toLocaleString()}€
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="text-sm text-muted-foreground">Confiance:</span>
                <Progress value={analysis.confidence_score * 100} className="flex-1 h-2" />
                <span className="text-sm font-medium">{(analysis.confidence_score * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div className="p-5 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl">
              <h4 className="font-semibold mb-4 flex items-center gap-2"><BarChart3 className="h-4 w-4 text-blue-600" /> Métriques Sociales</h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg">
                  <SpotifyIcon className="h-6 w-6 text-green-500" />
                  <div>
                    <div className="text-lg font-bold">{formatNumber(analysis.spotify_monthly_listeners)}</div>
                    <div className="text-xs text-muted-foreground">auditeurs/mois</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg">
                  <Youtube className="h-6 w-6 text-red-500" />
                  <div>
                    <div className="text-lg font-bold">{analysis.youtube_subscribers > 0 ? formatNumber(analysis.youtube_subscribers) : "—"}</div>
                    <div className="text-xs text-muted-foreground">abonnés</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg">
                  <Instagram className="h-6 w-6 text-pink-500" />
                  <div>
                    <div className="text-lg font-bold">{analysis.instagram_followers > 0 ? formatNumber(analysis.instagram_followers) : "—"}</div>
                    <div className="text-xs text-muted-foreground">followers</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg">
                  <TiktokIcon className="h-6 w-6" />
                  <div>
                    <div className="text-lg font-bold">{analysis.tiktok_followers > 0 ? formatNumber(analysis.tiktok_followers) : "—"}</div>
                    <div className="text-xs text-muted-foreground">followers</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-5 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl">
              <h4 className="font-semibold mb-4 flex items-center gap-2"><Building2 className="h-4 w-4 text-purple-600" /> Contacts Business</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {analysis.record_label && <div className="p-3 bg-white dark:bg-gray-800 rounded-lg"><span className="text-muted-foreground">Label</span><p className="font-medium">{analysis.record_label}</p></div>}
                {analysis.management && <div className="p-3 bg-white dark:bg-gray-800 rounded-lg"><span className="text-muted-foreground">Management</span><p className="font-medium">{analysis.management}</p></div>}
                {analysis.booking_agency && <div className="p-3 bg-white dark:bg-gray-800 rounded-lg"><span className="text-muted-foreground">Booking</span><p className="font-medium">{analysis.booking_agency}</p></div>}
                {analysis.booking_email && <div className="p-3 bg-white dark:bg-gray-800 rounded-lg"><span className="text-muted-foreground">Email</span><a href={`mailto:${analysis.booking_email}`} className="font-medium text-blue-600 hover:underline">{analysis.booking_email}</a></div>}
                {!analysis.record_label && !analysis.management && !analysis.booking_agency && !analysis.booking_email && <div className="col-span-2 text-center text-muted-foreground py-4">Aucun contact business disponible</div>}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="ai" className="space-y-4 mt-4">
            {analysis.ai_summary ? (
              <>
                <div className="p-5 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl">
                  <h4 className="font-semibold mb-3 flex items-center gap-2"><Brain className="h-4 w-4 text-purple-500" />Résumé IA</h4>
                  <p className="text-sm leading-relaxed">{analysis.ai_summary}</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {analysis.strengths && analysis.strengths.length > 0 && (
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-xl">
                      <h5 className="font-medium text-green-700 text-sm mb-3 flex items-center gap-2"><Zap className="h-4 w-4" /> Forces</h5>
                      <ul className="text-sm space-y-1.5">{analysis.strengths.slice(0, 3).map((s, i) => <li key={i} className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" /><span>{s}</span></li>)}</ul>
                    </div>
                  )}
                  {analysis.weaknesses && analysis.weaknesses.length > 0 && (
                    <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl">
                      <h5 className="font-medium text-red-700 text-sm mb-3 flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> Faiblesses</h5>
                      <ul className="text-sm space-y-1.5">{analysis.weaknesses.slice(0, 3).map((w, i) => <li key={i} className="flex items-start gap-2"><XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" /><span>{w}</span></li>)}</ul>
                    </div>
                  )}
                  {analysis.opportunities && analysis.opportunities.length > 0 && (
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                      <h5 className="font-medium text-blue-700 text-sm mb-3 flex items-center gap-2"><Lightbulb className="h-4 w-4" /> Opportunités</h5>
                      <ul className="text-sm space-y-1.5">{analysis.opportunities.slice(0, 3).map((o, i) => <li key={i} className="flex items-start gap-2"><Target className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" /><span>{o}</span></li>)}</ul>
                    </div>
                  )}
                  {analysis.threats && analysis.threats.length > 0 && (
                    <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl">
                      <h5 className="font-medium text-orange-700 text-sm mb-3 flex items-center gap-2"><Shield className="h-4 w-4" /> Menaces</h5>
                      <ul className="text-sm space-y-1.5">{analysis.threats.slice(0, 3).map((t, i) => <li key={i} className="flex items-start gap-2"><AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" /><span>{t}</span></li>)}</ul>
                    </div>
                  )}
                </div>

                {analysis.ai_recommendations && analysis.ai_recommendations.length > 0 && (
                  <div className="p-5 bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 rounded-xl">
                    <h4 className="font-semibold mb-3 flex items-center gap-2"><Sparkles className="h-4 w-4 text-yellow-500" />Recommandations IA</h4>
                    <ul className="space-y-2">{analysis.ai_recommendations.map((rec, i) => <li key={i} className="flex items-start gap-3 text-sm"><span className="flex items-center justify-center w-5 h-5 bg-yellow-200 text-yellow-800 rounded-full text-xs font-bold shrink-0">{i + 1}</span><span>{rec}</span></li>)}</ul>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Brain className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <p className="font-medium">Données IA non disponibles</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="predictions" className="space-y-4 mt-4">
            {analysis.predicted_listeners_30d ? (
              <>
                <div className="p-5 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-semibold flex items-center gap-2"><LineChart className="h-4 w-4" />Tendance de Croissance</h4>
                    <Badge className={`${analysis.growth_trend === "explosive" ? "bg-purple-500" : analysis.growth_trend === "rapid" ? "bg-green-500" : analysis.growth_trend === "strong" ? "bg-blue-500" : "bg-gray-500"} text-white`}>{analysis.growth_trend?.toUpperCase()}</Badge>
                  </div>
                  {analysis.growth_rate_monthly && <div className="text-4xl font-bold">{analysis.growth_rate_monthly > 0 ? "+" : ""}{analysis.growth_rate_monthly.toFixed(1)}%<span className="text-base font-normal text-muted-foreground ml-2">/ mois</span></div>}
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="p-5 border rounded-xl text-center">
                    <div className="text-xs text-muted-foreground mb-2">Dans 30 jours</div>
                    <div className="text-2xl font-bold text-blue-600">{formatNumber(analysis.predicted_listeners_30d)}</div>
                  </div>
                  <div className="p-5 border rounded-xl text-center">
                    <div className="text-xs text-muted-foreground mb-2">Dans 90 jours</div>
                    <div className="text-2xl font-bold text-green-600">{formatNumber(analysis.predicted_listeners_90d || 0)}</div>
                  </div>
                  <div className="p-5 border rounded-xl text-center">
                    <div className="text-xs text-muted-foreground mb-2">Dans 180 jours</div>
                    <div className="text-2xl font-bold text-purple-600">{formatNumber(analysis.predicted_listeners_180d || 0)}</div>
                  </div>
                </div>

                {analysis.best_platforms && analysis.best_platforms.length > 0 && (
                  <div className="p-5 bg-gradient-to-r from-pink-50 to-rose-50 dark:from-pink-900/20 dark:to-rose-900/20 rounded-xl">
                    <h4 className="font-semibold mb-4 flex items-center gap-2"><Smartphone className="h-4 w-4 text-pink-600" /> Meilleures Plateformes</h4>
                    <div className="flex flex-wrap gap-2 mb-4">{analysis.best_platforms.map((platform, i) => <Badge key={i} variant="secondary" className="text-sm py-1 px-3">{platform}</Badge>)}</div>
                    {analysis.viral_potential !== undefined && (
                      <div className="flex items-center gap-3"><span className="text-sm font-medium">Potentiel viral:</span><Progress value={analysis.viral_potential * 100} className="flex-1 h-2.5" /><span className="text-sm font-bold">{(analysis.viral_potential * 100).toFixed(0)}%</span></div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <LineChart className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <p className="font-medium">Prédictions non disponibles</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="booking" className="space-y-4 mt-4">
            {analysis.optimal_fee ? (
              <>
                <div className="p-5 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl">
                  <h4 className="font-semibold mb-2 flex items-center gap-2"><Gem className="h-4 w-4 text-green-600" /> Cachet Optimal Recommandé</h4>
                  <div className="text-4xl font-bold text-green-600">{analysis.optimal_fee.toLocaleString()}€</div>
                  <div className="text-sm text-muted-foreground mt-2">Fourchette: {analysis.fee_min.toLocaleString()}€ - {analysis.fee_max.toLocaleString()}€</div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {analysis.negotiation_power && (
                    <div className="p-5 border rounded-xl">
                      <div className="text-sm text-muted-foreground mb-2">Pouvoir de négociation</div>
                      <div className={`text-xl font-bold ${analysis.negotiation_power === "high" ? "text-red-600" : analysis.negotiation_power === "medium" ? "text-yellow-600" : "text-green-600"}`}>
                        {analysis.negotiation_power === "high" ? "● Élevé (Artiste)" : analysis.negotiation_power === "medium" ? "● Moyen" : "● Faible (Acheteur)"}
                      </div>
                    </div>
                  )}
                  {analysis.best_booking_window && (
                    <div className="p-5 border rounded-xl">
                      <div className="text-sm text-muted-foreground mb-2">Fenêtre idéale</div>
                      <div className="text-xl font-bold">{analysis.best_booking_window}</div>
                    </div>
                  )}
                </div>

                {analysis.event_type_fit && Object.keys(analysis.event_type_fit).length > 0 && (
                  <div className="p-5 border rounded-xl">
                    <h4 className="font-semibold mb-4 flex items-center gap-2"><Tent className="h-4 w-4" /> Compatibilité par Type d'Événement</h4>
                    <div className="space-y-3">
                      {Object.entries(analysis.event_type_fit).sort(([, a], [, b]) => b - a).map(([type, score]) => (
                        <div key={type} className="flex items-center gap-3">
                          <span className="w-28 text-sm font-medium capitalize">{type}</span>
                          <Progress value={score * 100} className="flex-1 h-2.5" />
                          <span className="text-sm font-bold w-12 text-right">{(score * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.seasonal_demand && Object.keys(analysis.seasonal_demand).length > 0 && (
                  <div className="p-5 border rounded-xl">
                    <h4 className="font-semibold mb-4 flex items-center gap-2"><Calendar className="h-4 w-4" /> Demande Saisonnière</h4>
                    <div className="grid grid-cols-4 gap-3">
                      {Object.entries(analysis.seasonal_demand).map(([season, score]) => (
                        <div key={season} className="text-center p-4 rounded-xl bg-muted/50">
                          <div className="text-xs text-muted-foreground capitalize mb-1">{season}</div>
                          <div className={`text-2xl font-bold ${score > 0.7 ? "text-green-600" : score > 0.4 ? "text-yellow-600" : "text-red-600"}`}>{(score * 100).toFixed(0)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Target className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <p className="font-medium">Intelligence Booking non disponible</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// BATCH ANALYSIS DIALOG
// ============================================================================

function BatchAnalysisDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [artistsText, setArtistsText] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [tasks, setTasks] = useState<Array<{ name: string; status: "pending" | "processing" | "completed" | "error"; error?: string }>>([]);
  const queryClient = useQueryClient();

  const parseArtists = (text: string): string[] => {
    return text.split(/[\n,]+/).map(name => name.trim()).filter(name => name.length > 0).filter((name, index, arr) => arr.indexOf(name) === index);
  };

  const startAnalysis = async () => {
    const artistNames = parseArtists(artistsText);
    if (artistNames.length === 0) return;

    setTasks(artistNames.map(name => ({ name, status: "pending" as const })));
    setIsRunning(true);

    for (let i = 0; i < artistNames.length; i++) {
      setTasks(prev => prev.map((t, idx) => idx === i ? { ...t, status: "processing" } : t));

      try {
        const response = await api.post("/ingestion/analyze-artist", { artist_name: artistNames[i], force_refresh: false });
        const taskId = response.data.task_id;
        let completed = false;
        let attempts = 0;

        while (!completed && attempts < 60) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          try {
            const statusResponse = await api.get(`/ingestion/task/${taskId}`);
            if (statusResponse.data.ready) {
              completed = true;
              setTasks(prev => prev.map((t, idx) => idx === i ? { ...t, status: statusResponse.data.result?.success || statusResponse.data.result?.result ? "completed" : "error" } : t));
            }
          } catch { attempts++; }
          attempts++;
        }

        if (!completed) setTasks(prev => prev.map((t, idx) => idx === i ? { ...t, status: "error", error: "Timeout" } : t));
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : "Erreur inconnue";
        setTasks(prev => prev.map((t, idx) => idx === i ? { ...t, status: "error", error: errorMessage } : t));
      }

      if (i < artistNames.length - 1) await new Promise(resolve => setTimeout(resolve, 1000));
    }

    setIsRunning(false);
    queryClient.invalidateQueries({ queryKey: ["artist-history"] });
    queryClient.invalidateQueries({ queryKey: ["artist-stats"] });
  };

  const handleReset = () => { setTasks([]); setArtistsText(""); setIsRunning(false); };
  const artistCount = parseArtists(artistsText).length;
  const completedCount = tasks.filter(t => t.status === "completed").length;
  const errorCount = tasks.filter(t => t.status === "error").length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Users className="h-5 w-5 text-purple-500" />Analyse Multiple d'Artistes</DialogTitle>
          <DialogDescription>Entrez un artiste par ligne ou séparez-les par des virgules</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {tasks.length === 0 ? (
            <>
              <textarea
                value={artistsText}
                onChange={(e) => setArtistsText(e.target.value)}
                placeholder="PNL&#10;Damso&#10;Aya Nakamura&#10;SDM"
                className="w-full h-48 p-4 border rounded-xl resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{artistCount} artiste{artistCount > 1 ? "s" : ""} détecté{artistCount > 1 ? "s" : ""}</span>
                <Button onClick={startAnalysis} disabled={artistCount === 0} className="bg-purple-600 hover:bg-purple-700"><Play className="h-4 w-4 mr-2" />Lancer l'analyse</Button>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Progression: {completedCount + errorCount} / {tasks.length}</span>
                <span className="text-sm text-muted-foreground"><CheckCircle2 className="h-3.5 w-3.5 text-green-500 inline mr-0.5" />{completedCount} réussies • <XCircle className="h-3.5 w-3.5 text-red-500 inline mr-0.5" />{errorCount} erreurs</span>
              </div>
              <Progress value={((completedCount + errorCount) / tasks.length) * 100} className="h-2" />
              
              <div className="max-h-64 overflow-y-auto space-y-2 mt-4">
                {tasks.map((task, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                    {task.status === "completed" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                    {task.status === "error" && <XCircle className="h-4 w-4 text-red-500" />}
                    {task.status === "processing" && <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />}
                    {task.status === "pending" && <Clock className="h-4 w-4 text-gray-400" />}
                    <span className="flex-1 font-medium">{task.name}</span>
                    {task.error && <span className="text-xs text-red-500">{task.error}</span>}
                  </div>
                ))}
              </div>
              
              {!isRunning && (
                <div className="flex justify-end gap-2 mt-4">
                  <Button variant="outline" onClick={handleReset}><RefreshCw className="h-4 w-4 mr-2" />Nouvelle analyse</Button>
                  <Button onClick={() => onOpenChange(false)}>Fermer</Button>
                </div>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// MAIN PAGE COMPONENT
// ============================================================================

function ArtistHistoryContent() {
  const [search, setSearch] = useState("");
  const [genre, setGenre] = useState<string>("");
  const [marketTier, setMarketTier] = useState<string>("");
  const [page, setPage] = useState(1);
  const [selectedAnalysis, setSelectedAnalysis] = useState<ArtistAnalysis | null>(null);
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
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

  const { data: queue } = useQuery<QueueResponse>({
    queryKey: ["discovery-queue"],
    queryFn: async () => {
      const response = await api.get("/discovery/queue");
      return response.data;
    },
    refetchInterval: 3000,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => { await api.delete(`/artist-history/${id}`); },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artist-history"] });
      queryClient.invalidateQueries({ queryKey: ["artist-stats"] });
      toast.success("Analyse supprimée");
    },
    onError: () => { toast.error("Erreur lors de la suppression"); },
  });

  const handleSearch = async (query: string, inputType: InputType) => {
    setIsSearching(true);
    try {
      await api.post("/discovery/search", { query, input_type: inputType });
      toast.success(`Analyse lancée pour "${query}"`, { description: "Vous pouvez suivre la progression ci-dessous" });
      queryClient.invalidateQueries({ queryKey: ["discovery-queue"] });
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number; data?: { detail?: { message?: string } | string } }; message?: string };
      if (axiosError.response?.status === 409) {
        toast.info("Artiste déjà analysé récemment", { description: typeof axiosError.response.data?.detail === 'object' ? axiosError.response.data.detail.message : undefined });
      } else {
        toast.error("Erreur lors de la recherche", { description: typeof axiosError.response?.data?.detail === 'string' ? axiosError.response.data.detail : axiosError.message });
      }
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Music className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Artistes</h1>
              <p className="text-muted-foreground text-sm">Recherchez et analysez des artistes</p>
            </div>
          </div>
          
          <Button variant="outline" onClick={() => setBatchDialogOpen(true)}>
            <Users className="h-4 w-4 mr-2" />Analyse Multiple
          </Button>
        </div>
        
        <GoogleSearchBar onSearch={handleSearch} isLoading={isSearching} />
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 pb-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left: Stats + Jobs */}
          <div className="lg:col-span-1 space-y-6">
            {stats && (
              <div className="space-y-4">
                <StatCard title="Total Analyses" value={stats.total_analyses} icon={BarChart3} iconColor="bg-blue-500" />
                <StatCard title="Artistes Uniques" value={stats.unique_artists} icon={Users} iconColor="bg-purple-500" />
                <StatCard title="Budget Moyen" value={`${(stats.avg_fee_min || 0).toLocaleString()}€`} subtitle={`à ${(stats.avg_fee_max || 0).toLocaleString()}€`} icon={DollarSign} iconColor="bg-green-500" />
                {stats.most_searched_artist && <StatCard title="Plus Recherché" value={stats.most_searched_artist} icon={TrendingUp} iconColor="bg-orange-500" />}
              </div>
            )}

            {queue?.jobs && queue.jobs.length > 0 && <ActiveJobsPanel jobs={queue.jobs} />}
          </div>

          {/* Right: Table */}
          <div className="lg:col-span-3 space-y-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input placeholder="Filtrer les résultats..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="pl-9" />
                  </div>
                  <Select value={genre} onValueChange={(v) => { setGenre(v === "all" ? "" : v); setPage(1); }}>
                    <SelectTrigger className="w-[160px]"><SelectValue placeholder="Genre" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous genres</SelectItem>
                      <SelectItem value="RAP">Rap</SelectItem>
                      <SelectItem value="POP">Pop</SelectItem>
                      <SelectItem value="ELECTRO">Electro</SelectItem>
                      <SelectItem value="RNB">RnB</SelectItem>
                      <SelectItem value="ROCK">Rock</SelectItem>
                      <SelectItem value="VARIETE">Variété</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={marketTier} onValueChange={(v) => { setMarketTier(v === "all" ? "" : v); setPage(1); }}>
                    <SelectTrigger className="w-[180px]"><SelectValue placeholder="Niveau" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous niveaux</SelectItem>
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

            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="font-semibold">Artiste</TableHead>
                      <TableHead className="font-semibold">Genre</TableHead>
                      <TableHead className="font-semibold">Cachet Estimé</TableHead>
                      <TableHead className="font-semibold">Niveau</TableHead>
                      <TableHead className="font-semibold">Score</TableHead>
                      <TableHead className="font-semibold">Spotify</TableHead>
                      <TableHead className="font-semibold">Tendance</TableHead>
                      <TableHead className="font-semibold">Date</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {isLoading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <TableRow key={i}>{Array.from({ length: 9 }).map((_, j) => <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>)}</TableRow>
                      ))
                    ) : history?.items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-16">
                          <div className="flex flex-col items-center gap-3">
                            <Music className="h-12 w-12 text-muted-foreground/30" />
                            <div>
                              <p className="font-medium text-muted-foreground">Aucune analyse trouvée</p>
                              <p className="text-sm text-muted-foreground/70">Utilisez la barre de recherche pour analyser un artiste</p>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      history?.items.map((analysis) => (
                        <ArtistTableRow key={analysis.id} analysis={analysis} onView={() => setSelectedAnalysis(analysis)} onDelete={() => deleteMutation.mutate(analysis.id)} />
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {history && history.total_pages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}><ChevronLeft className="h-4 w-4" /></Button>
                <span className="text-sm px-4">Page {page} sur {history.total_pages}</span>
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(history.total_pages, p + 1))} disabled={page === history.total_pages}><ChevronRight className="h-4 w-4" /></Button>
              </div>
            )}
          </div>
        </div>
      </div>

      <ArtistDetailDialog analysis={selectedAnalysis} open={!!selectedAnalysis} onOpenChange={(open) => !open && setSelectedAnalysis(null)} />
      <BatchAnalysisDialog open={batchDialogOpen} onOpenChange={setBatchDialogOpen} />
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
