"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  TrendingUp,
  DollarSign,
  Users,
  Zap,
  Music,
  MapPin,
  Calendar,
  AlertTriangle,
  Flame,
  Target,
  BarChart3,
  ExternalLink,
  ChevronRight,
  Sparkles,
  ArrowUpRight,
  MessageCircle,
  Lightbulb,
  Bell,
  Headphones,
  Building2,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { marketIntelligenceApi } from "@/lib/api";

// ── Types ──

interface FeedItem {
  type: string;
  priority: string;
  message: string;
  artist_name?: string;
  artist_image?: string;
  artist_id?: string;
  genres?: string[];
  score?: number;
  velocity?: number;
  acceleration?: number;
  monthly_listeners?: number;
  fee_min?: number;
  fee_max?: number;
  recommendation?: string;
  timing?: string;
  confidence?: number;
  drivers?: { label: string; value: number; impact: number }[];
  signals?: { type: string; strength: number }[];
  social?: { spotify: number; instagram: number; tiktok: number; total: number };
  event_name?: string;
  event_type?: string;
  venue?: string;
  city?: string;
  date?: string;
  date_label?: string;
  price_min?: number;
  price_max?: number;
  event_url?: string;
  promoter?: string;
  source?: string;
  event_count?: number;
  avg_price_min?: number;
  avg_price_max?: number;
}

interface IntelFeed {
  feed: FeedItem[];
  kpis: {
    total_artists: number;
    avg_score: number;
    high_score_count: number;
    rising_count: number;
    avg_fee_min: number;
    avg_fee_max: number;
    fee_range_min: number;
    fee_range_max: number;
    events_total: number;
    events_upcoming: number;
  };
  trends: {
    genres: { name: string; count: number }[];
    score_distribution: Record<string, number>;
    fee_tiers: Record<string, number>;
  };
}

// ── Helpers ──

function formatK(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function formatFee(min: number, max: number): string {
  if (!min && !max) return "N/A";
  return `${formatK(min)} – ${formatK(max)}€`;
}

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-400",
  high: "bg-orange-500/10 border-orange-500/30 text-orange-700 dark:text-orange-400",
  medium: "bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-400",
  low: "bg-slate-500/10 border-slate-500/30 text-slate-600 dark:text-slate-400",
  info: "bg-purple-500/10 border-purple-500/30 text-purple-700 dark:text-purple-400",
};

const TYPE_ICONS: Record<string, typeof Flame> = {
  trending_artist: TrendingUp,
  fee_opportunity: Lightbulb,
  book_alert: Flame,
  upcoming_event: Calendar,
  market_saturation: BarChart3,
};

const TYPE_LABELS: Record<string, string> = {
  trending_artist: "Croissance",
  fee_opportunity: "Opportunité",
  book_alert: "Recommandation",
  upcoming_event: "Agenda",
  market_saturation: "Marché",
};

// ── Components ──

function KpiCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: typeof Users;
  label: string;
  value: string | number;
  sub?: string;
  color: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${color}15` }}
          >
            <Icon className="h-5 w-5" style={{ color }} />
          </div>
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-lg font-bold truncate">{value}</p>
            {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function FeedCard({ item }: { item: FeedItem }) {
  const Icon = TYPE_ICONS[item.type] || Zap;
  const typeLabel = TYPE_LABELS[item.type] || item.type;
  const style = PRIORITY_STYLES[item.priority] || PRIORITY_STYLES.low;

  return (
    <div className={`rounded-lg border p-4 ${style} transition-all hover:shadow-md`}>
      <div className="flex items-start gap-3">
        {/* Avatar / Icon */}
        <div className="flex-shrink-0">
          {item.artist_image ? (
            <img
              src={item.artist_image}
              alt={item.artist_name || ""}
              className="h-10 w-10 rounded-full object-cover"
            />
          ) : (
            <div className="h-10 w-10 rounded-full bg-background/50 flex items-center justify-center">
              <Icon className="h-5 w-5" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              {typeLabel}
            </Badge>
            {item.recommendation && item.recommendation !== "WATCHLIST" && (
              <Badge
                variant={item.recommendation === "BOOK" ? "default" : "secondary"}
                className="text-[10px] px-1.5 py-0"
              >
                {item.recommendation}
              </Badge>
            )}
            {item.score && item.score > 0 && (
              <span className="text-[10px] font-medium">Score {item.score}</span>
            )}
          </div>

          <p className="text-sm font-medium leading-snug">{item.message}</p>

          {/* Metrics row */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[11px] opacity-80">
            {item.velocity !== undefined && item.velocity > 0 && (
              <span className="flex items-center gap-0.5">
                <ArrowUpRight className="h-3 w-3" />
                +{item.velocity}%
              </span>
            )}
            {(item.fee_min || item.fee_max) && (item.fee_min! > 0 || item.fee_max! > 0) && (
              <span className="flex items-center gap-0.5"><DollarSign className="h-3 w-3" />{formatFee(item.fee_min || 0, item.fee_max || 0)}</span>
            )}
            {item.monthly_listeners && item.monthly_listeners > 0 && (
              <span className="flex items-center gap-0.5"><Headphones className="h-3 w-3" />{formatK(item.monthly_listeners)}</span>
            )}
            {item.city && <span className="flex items-center gap-0.5"><MapPin className="h-3 w-3" />{item.city}</span>}
            {item.date_label && <span className="flex items-center gap-0.5"><Calendar className="h-3 w-3" />{item.date_label}</span>}
            {item.promoter && <span className="flex items-center gap-0.5"><Building2 className="h-3 w-3" />{item.promoter}</span>}
          </div>

          {/* Genres */}
          {item.genres && item.genres.length > 0 && (
            <div className="flex gap-1 mt-2">
              {item.genres.map((g) => (
                <span
                  key={g}
                  className="text-[10px] px-1.5 py-0.5 rounded-full bg-background/50 border"
                >
                  {g}
                </span>
              ))}
            </div>
          )}

          {/* Event link */}
          {item.event_url && (
            <a
              href={item.event_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-[11px] font-medium hover:underline"
            >
              Voir billetterie <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function GenreBar({ genres }: { genres: { name: string; count: number }[] }) {
  const max = Math.max(...genres.map((g) => g.count), 1);
  return (
    <div className="space-y-2">
      {genres.map((g) => (
        <div key={g.name} className="flex items-center gap-2">
          <span className="text-xs w-24 truncate text-muted-foreground">{g.name}</span>
          <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all"
              style={{ width: `${(g.count / max) * 100}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground w-6 text-right">{g.count}</span>
        </div>
      ))}
    </div>
  );
}

function DistChart({ data, colors }: { data: Record<string, number>; colors: string[] }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([label, count], i) => (
        <div key={label} className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded"
            style={{ backgroundColor: colors[i % colors.length] }}
          />
          <span className="text-xs flex-1">{label}</span>
          <span className="text-xs font-medium">{count}</span>
          <span className="text-[10px] text-muted-foreground w-10 text-right">
            {((count / total) * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Main page ──

function IntelligenceContent() {
  const [tab, setTab] = useState("all");

  const { data, isLoading } = useQuery<IntelFeed>({
    queryKey: ["market-intelligence", "feed"],
    queryFn: () => marketIntelligenceApi.getFeed(),
    refetchInterval: 120_000,
  });

  const filteredFeed = data?.feed?.filter((item) => {
    if (tab === "all") return true;
    if (tab === "alerts") return ["book_alert", "trending_artist"].includes(item.type);
    if (tab === "fees") return item.type === "fee_opportunity";
    if (tab === "events") return ["upcoming_event", "market_saturation"].includes(item.type);
    return true;
  }) || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RadarSpinner className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const kpis = data?.kpis;
  const trends = data?.trends;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Radar Intelligence</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          {(data?.feed?.length || 0) > 0
            ? `${data?.feed?.length} éléments résumés depuis tes artistes et le marché.`
            : "Aucun élément pour le moment — les résumés apparaîtront quand tu auras des artistes dans Discovery."}
        </p>
      </div>

      {/* KPIs */}
      {kpis && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard
            icon={Users}
            label="Artistes suivis"
            value={kpis.total_artists}
            color="#6366f1"
          />
          <KpiCard
            icon={Target}
            label="Score moyen"
            value={kpis.avg_score}
            sub={`${kpis.high_score_count} au-dessus de 75`}
            color="#8b5cf6"
          />
          <KpiCard
            icon={TrendingUp}
            label="En croissance"
            value={kpis.rising_count}
            color="#10b981"
          />
          <KpiCard
            icon={DollarSign}
            label="Cachet moyen"
            value={formatFee(kpis.avg_fee_min, kpis.avg_fee_max)}
            sub={`${formatK(kpis.fee_range_min)} – ${formatK(kpis.fee_range_max)}€`}
            color="#f59e0b"
          />
          <KpiCard
            icon={Music}
            label="Événements"
            value={kpis.events_total}
            sub={`${kpis.events_upcoming} à venir`}
            color="#ec4899"
          />
          <KpiCard
            icon={Flame}
            label="Potentiel élevé"
            value={data?.feed?.filter((f) => f.type === "book_alert").length || 0}
            sub="Recommandation BOOK"
            color="#ef4444"
          />
        </div>
      )}

      {/* Main content: feed + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Feed (2/3) */}
        <div className="lg:col-span-2 space-y-4">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="all">
                Résumé ({data?.feed?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="alerts">
                Mouvements ({data?.feed?.filter((f) => ["book_alert", "trending_artist"].includes(f.type)).length || 0})
              </TabsTrigger>
              <TabsTrigger value="fees">
                Cachets ({data?.feed?.filter((f) => f.type === "fee_opportunity").length || 0})
              </TabsTrigger>
              <TabsTrigger value="events">
                Agenda ({data?.feed?.filter((f) => ["upcoming_event", "market_saturation"].includes(f.type)).length || 0})
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {filteredFeed.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                <Sparkles className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p className="font-medium">Rien à afficher</p>
                <p className="text-xs mt-1">
                  Les résumés apparaîtront automatiquement à partir des artistes que tu suis dans Discovery.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredFeed.map((item, i) => (
                <FeedCard key={`${item.type}-${item.artist_name || item.city}-${i}`} item={item} />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar (1/3) */}
        <div className="space-y-4">
          {/* Genre distribution */}
          {trends && trends.genres.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Genres dominants</CardTitle>
              </CardHeader>
              <CardContent>
                <GenreBar genres={trends.genres} />
              </CardContent>
            </Card>
          )}

          {/* Score distribution */}
          {trends && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Distribution des scores</CardTitle>
              </CardHeader>
              <CardContent>
                <DistChart
                  data={trends.score_distribution}
                  colors={["#ef4444", "#f59e0b", "#3b82f6", "#10b981"]}
                />
              </CardContent>
            </Card>
          )}

          {/* Fee tier distribution */}
          {trends && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Fourchettes de cachets</CardTitle>
              </CardHeader>
              <CardContent>
                <DistChart
                  data={trends.fee_tiers}
                  colors={["#6366f1", "#8b5cf6", "#a855f7", "#c084fc", "#d8b4fe"]}
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

export default function IntelligencePage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <IntelligenceContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
