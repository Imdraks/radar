"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Activity,
  Calendar,
  Loader2,
  MapPin,
  RefreshCw,
  TrendingUp,
  Radio,
  Target,
  ArrowRight,
  BarChart3,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { analyticsV2Api } from "@/lib/api";

// ── Types ──

interface CockpitData {
  signals_count: number;
  kpis: {
    events_30d: number;
    artists_moving: number;
    active_cities: number;
    qualified_opportunities: number;
  };
  movements: {
    type: string;
    icon: string;
    text: string;
    timestamp: string | null;
    artist_name?: string;
    city?: string;
  }[];
  upcoming: {
    artist_name: string;
    venue: string;
    city: string;
    date: string | null;
    date_label: string;
    days_until: number;
    event_type: string;
  }[];
  data_quality: {
    total_artists: number;
    scored_pct: number;
    fee_estimated_pct: number;
    event_coverage_pct: number;
  };
  hotspots: {
    city: string;
    count: number;
    lat: number;
    lng: number;
  }[];
}

// ── Helpers ──

function timeAgo(ts: string | null): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}j`;
}

const MOVEMENT_ICONS: Record<string, typeof TrendingUp> = {
  "trending-up": TrendingUp,
  calendar: Calendar,
  "map-pin": MapPin,
};

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

// ── Main ──

function CockpitContent() {
  const { data, isLoading, refetch } = useQuery<CockpitData>({
    queryKey: ["analytics-v2", "cockpit"],
    queryFn: () => analyticsV2Api.getCockpit(),
    refetchInterval: 120_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <Loader2 className="h-7 w-7 animate-spin text-primary/60" />
      </div>
    );
  }

  const k = data?.kpis;
  const q = data?.data_quality;
  const signalCount = data?.signals_count || 0;
  const hotspots = data?.hotspots || [];
  const movements = data?.movements || [];
  const upcoming = data?.upcoming || [];
  const maxHotspot = Math.max(...hotspots.map((h) => h.count), 1);

  const kpiItems = k
    ? [
        { label: "Événements (30j)", value: k.events_30d, icon: Calendar, color: "#0000FF", href: "/map" },
        { label: "Artistes en mouvement", value: k.artists_moving, icon: TrendingUp, color: "#10b981", href: "/discovery" },
        { label: "Zones actives", value: k.active_cities, icon: MapPin, color: "#7c3aed", href: "/map" },
        { label: "Opportunités", value: k.qualified_opportunities, icon: Target, color: "#f59e0b", href: "/intelligence" },
      ]
    : [];

  const qualityItems = q
    ? [
        { label: "Scorés", pct: q.scored_pct, color: "#0000FF" },
        { label: "Cachet estimé", pct: q.fee_estimated_pct, color: "#f59e0b" },
        { label: "Événement réel", pct: q.event_coverage_pct, color: "#10b981" },
      ]
    : [];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8 space-y-8">
      {/* ── Header ── */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[1.65rem] font-semibold tracking-tight">Cockpit</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Tour de contrôle du marché</p>
        </div>
        <Button onClick={() => refetch()} variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* ── Signal Banner ── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={`relative overflow-hidden rounded-2xl p-6 ${
          signalCount > 0
            ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600"
            : "bg-muted"
        }`}
      >
        {signalCount > 0 && (
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.12),transparent_60%)]" />
        )}
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${
              signalCount > 0 ? "bg-white/15 backdrop-blur-sm" : "bg-muted-foreground/10"
            }`}>
              <Radio className={`h-6 w-6 ${signalCount > 0 ? "text-white" : "text-muted-foreground"}`} />
            </div>
            <div>
              <p className={`text-sm font-medium ${signalCount > 0 ? "text-white/70" : "text-muted-foreground"}`}>
                Signaux détectés
              </p>
              <p className={`text-4xl font-bold tracking-tight ${signalCount > 0 ? "text-white" : "text-muted-foreground"}`}>
                {signalCount}
              </p>
            </div>
          </div>
          <p className={`text-sm hidden sm:block ${signalCount > 0 ? "text-white/70" : "text-muted-foreground"}`}>
            {signalCount > 0
              ? `${signalCount} artiste${signalCount > 1 ? "s" : ""} en mouvement cette semaine`
              : "Le marché est calme — aucun mouvement notable"}
          </p>
        </div>
      </motion.div>

      {/* ── KPIs ── */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 lg:grid-cols-4 gap-4"
      >
        {kpiItems.map(({ label, value, icon: Icon, color, href }) => (
          <motion.div key={label} variants={fadeUp}>
            <Link href={href} className="group block">
              <div className="rounded-xl border bg-card p-5 transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between mb-3">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-lg"
                    style={{ backgroundColor: `${color}10` }}
                  >
                    <Icon className="h-[18px] w-[18px]" style={{ color }} />
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 -translate-x-1 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
                </div>
                <p className="text-3xl font-bold tracking-tight">{value}</p>
                <p className="text-xs text-muted-foreground mt-1">{label}</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Grid: Movements + Hotspots ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Movements */}
        <div className="lg:col-span-3 rounded-xl border bg-card">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Mouvements récents</h2>
            </div>
            <Badge variant="secondary" className="text-[10px] font-normal">{movements.length}</Badge>
          </div>
          <div className="px-4 pb-4">
            {movements.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Aucun mouvement détecté</p>
            ) : (
              <div className="space-y-1">
                {movements.map((m, i) => {
                  const Icon = MOVEMENT_ICONS[m.icon] || Activity;
                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.04 }}
                      className="flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/50"
                    >
                      <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-muted">
                        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[13px] leading-snug">{m.text}</p>
                        {m.timestamp && (
                          <p className="mt-0.5 text-[11px] text-muted-foreground">{timeAgo(m.timestamp)}</p>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Hotspots */}
        <div className="lg:col-span-2 rounded-xl border bg-card">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Zones actives</h2>
            </div>
            <Link href="/map" className="text-[11px] text-primary hover:underline flex items-center gap-1">
              Carte <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="px-5 pb-5">
            {hotspots.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Aucune zone active</p>
            ) : (
              <div className="space-y-3">
                {hotspots.slice(0, 6).map((h, i) => (
                  <motion.div
                    key={h.city}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-3"
                  >
                    <span className="w-24 truncate text-[13px]">{h.city}</span>
                    <div className="flex-1 h-[6px] rounded-full bg-muted overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(h.count / maxHotspot) * 100}%` }}
                        transition={{ duration: 0.5, delay: i * 0.06 }}
                        className="h-full rounded-full bg-primary"
                      />
                    </div>
                    <span className="w-5 text-right text-xs font-medium tabular-nums text-muted-foreground">
                      {h.count}
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Upcoming Events ── */}
      {upcoming.length > 0 && (
        <div className="rounded-xl border bg-card">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Prochains événements</h2>
            </div>
            <Link href="/map" className="text-[11px] text-primary hover:underline flex items-center gap-1">
              Voir tout <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="px-4 pb-4">
            <div className="divide-y divide-border">
              {upcoming.map((ev, i) => {
                const urgency =
                  ev.days_until <= 3
                    ? "bg-red-500 text-white"
                    : ev.days_until <= 7
                    ? "bg-amber-500 text-white"
                    : "bg-muted text-muted-foreground";
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className="flex items-center gap-4 px-2 py-3"
                  >
                    <div className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold ${urgency}`}>
                      J-{ev.days_until}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium">{ev.artist_name}</p>
                      <p className="truncate text-[11px] text-muted-foreground">
                        {ev.venue} · {ev.city}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-xs font-medium">{ev.date_label}</p>
                      <Badge variant="outline" className="mt-0.5 text-[10px] px-1.5 py-0">{ev.event_type}</Badge>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Data Quality ── */}
      {q && (
        <div className="rounded-xl border bg-card px-6 py-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Qualité des données</h2>
            </div>
            <span className="text-[11px] text-muted-foreground">{q.total_artists} artistes</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {qualityItems.map((it) => (
              <div key={it.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-muted-foreground">{it.label}</span>
                  <span className="text-sm font-semibold tabular-nums" style={{ color: it.color }}>
                    {it.pct}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${it.pct}%` }}
                    transition={{ duration: 0.7, ease: "easeOut" }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: it.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function CockpitPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <CockpitContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
