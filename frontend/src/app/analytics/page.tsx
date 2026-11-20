"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  BarChart3,
  Calendar,
  Filter,
  MapPin,
  Music,
  RefreshCw,
  Target,
  Users,
  Zap,
  ArrowRight,
  DollarSign,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { analyticsV2Api } from "@/lib/api";

// ── Types ──

interface TerrainData {
  overview: {
    total_artists: number;
    total_events: number;
    real_events: number;
    contact_coverage_pct: number;
    total_budget_estimated: number;
  };
  by_genre: { name: string; count: number; avg_score: number }[];
  by_zone: { city: string; count: number; density: string }[];
  by_event_type: Record<string, number>;
  by_source: Record<string, number>;
  by_fee_tier: Record<string, number>;
  timeline: { month: string; count: number }[];
  heatmap: { month: string; label: string; count: number }[];
  funnel: {
    detected: number;
    scored: number;
    contact_found: number;
    fee_estimated: number;
    actionable: number;
  };
}

// ── Helpers ──

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M€`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}k€`;
  return `${value}€`;
}

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };
const fadeUp = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.35 } } };
const PALETTE = ["#0000FF", "#7c3aed", "#ec4899", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#84cc16"];

// ── Main ──

function AnalyticsContent() {
  const { data, isLoading, refetch } = useQuery<TerrainData>({
    queryKey: ["analytics-v2", "terrain"],
    queryFn: () => analyticsV2Api.getTerrain(),
    refetchInterval: 120_000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <RadarSpinner className="h-7 w-7 animate-spin text-primary/60" />
      </div>
    );
  }

  const ov = data?.overview;
  const fn = data?.funnel;
  const genres = data?.by_genre || [];
  const zones = data?.by_zone || [];
  const timeline = data?.timeline || [];
  const heatmap = data?.heatmap || [];
  const maxGenre = Math.max(...genres.map((g) => g.count), 1);
  const maxZone = Math.max(...zones.map((z) => z.count), 1);
  const maxTimeline = Math.max(...timeline.map((t) => t.count), 1);
  const maxHeatmap = Math.max(...heatmap.map((h) => h.count), 1);
  const funnelMax = fn?.detected || 1;

  const kpiItems = ov
    ? [
        { label: "Artistes", value: String(ov.total_artists), icon: Users, color: "#0000FF" },
        { label: "Événements", value: String(ov.total_events), icon: Calendar, color: "#7c3aed", sub: `${ov.real_events} Ticketmaster` },
        { label: "Couverture contact", value: `${ov.contact_coverage_pct}%`, icon: Target, color: "#10b981" },
        { label: "Budget estimé", value: formatCurrency(ov.total_budget_estimated), icon: DollarSign, color: "#f59e0b" },
        { label: "Actionnables", value: String(fn?.actionable || 0), icon: Zap, color: "#ec4899", sub: `sur ${fn?.detected || 0} détectés` },
      ]
    : [];

  const feeOrdered = ["< 5k", "5-15k", "15-40k", "40-100k", "> 100k"];
  const feeColors = ["#10b981", "#0000FF", "#7c3aed", "#ec4899", "#ef4444"];
  const feeMax = Math.max(...Object.values(data?.by_fee_tier || {}), 1);

  const funnelSteps = fn
    ? [
        { label: "Détectés", value: fn.detected, color: "#0000FF" },
        { label: "Scorés", value: fn.scored, color: "#7c3aed" },
        { label: "Contact trouvé", value: fn.contact_found, color: "#a78bfa" },
        { label: "Cachet estimé", value: fn.fee_estimated, color: "#c4b5fd" },
        { label: "Actionnables", value: fn.actionable, color: "#10b981" },
      ]
    : [];

  const eventEntries = Object.entries(data?.by_event_type || {}).sort((a, b) => b[1] - a[1]);
  const sourceEntries = Object.entries(data?.by_source || {}).sort((a, b) => b[1] - a[1]);
  const totalEvents = eventEntries.reduce((s, [, v]) => s + v, 0) || 1;
  const totalSource = sourceEntries.reduce((s, [, v]) => s + v, 0) || 1;

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8 space-y-8">
      {/* ── Header ── */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[1.65rem] font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Structure du marché et couverture terrain</p>
        </div>
        <Button onClick={() => refetch()} variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* ── KPIs ── */}
      <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {kpiItems.map(({ label, value, icon: Icon, color, sub }) => (
          <motion.div key={label} variants={fadeUp}>
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ backgroundColor: `${color}10` }}>
                  <Icon className="h-[18px] w-[18px]" style={{ color }} />
                </div>
              </div>
              <p className="text-2xl font-bold tracking-tight">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
              {sub && <p className="text-[11px] text-muted-foreground">{sub}</p>}
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Genres + Zones ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border bg-card">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div className="flex items-center gap-2">
              <Music className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Répartition par genre</h2>
            </div>
            <Link href="/discovery" className="text-[11px] text-primary hover:underline flex items-center gap-1">
              Explorer <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="px-5 pb-5">
            {genres.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Aucune donnée</p>
            ) : (
              <div className="space-y-2.5">
                {genres.slice(0, 10).map((g, i) => (
                  <motion.div key={g.name} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }} className="flex items-center gap-2.5">
                    <span className="w-24 truncate text-[13px]">{g.name}</span>
                    <div className="flex-1 h-[7px] rounded-full bg-muted overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(g.count / maxGenre) * 100}%` }} transition={{ duration: 0.5, delay: i * 0.04 }} className="h-full rounded-full bg-primary" />
                    </div>
                    <span className="w-7 text-right text-xs font-medium tabular-nums">{g.count}</span>
                    <span className="w-9 text-right text-[10px] text-muted-foreground tabular-nums">ø{g.avg_score}</span>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border bg-card">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Répartition par zone</h2>
            </div>
            <Link href="/map" className="text-[11px] text-primary hover:underline flex items-center gap-1">
              Carte <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="px-5 pb-5">
            {zones.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Aucune donnée</p>
            ) : (
              <div className="space-y-2.5">
                {zones.map((z, i) => {
                  const dColor = z.density === "forte" ? "bg-primary/10 text-primary" : z.density === "moyenne" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" : "bg-muted text-muted-foreground";
                  return (
                    <motion.div key={z.city} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }} className="flex items-center gap-2.5">
                      <span className="w-24 truncate text-[13px]">{z.city}</span>
                      <div className="flex-1 h-[7px] rounded-full bg-muted overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${(z.count / maxZone) * 100}%` }} transition={{ duration: 0.5 }} className="h-full rounded-full bg-primary" />
                      </div>
                      <span className="w-7 text-right text-xs font-medium tabular-nums">{z.count}</span>
                      <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${dColor}`}>{z.density}</Badge>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Event type + Source ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[
          { title: "Type d\u2019événement", entries: eventEntries, total: totalEvents },
          { title: "Source des données", entries: sourceEntries, total: totalSource },
        ].map(({ title, entries, total }) => (
          <div key={title} className="rounded-xl border bg-card px-6 py-5">
            <h2 className="text-sm font-semibold mb-4">{title}</h2>
            {entries.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Aucune donnée</p>
            ) : (
              <>
                <div className="flex h-3 rounded-full overflow-hidden bg-muted mb-3">
                  {entries.map(([key, val], i) => (
                    <div key={key} style={{ width: `${(val / total) * 100}%`, backgroundColor: PALETTE[i % PALETTE.length] }} className="h-full" title={`${key}: ${val}`} />
                  ))}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {entries.map(([key, val], i) => (
                    <div key={key} className="flex items-center gap-1.5">
                      <div className="h-2 w-2 rounded-full" style={{ backgroundColor: PALETTE[i % PALETTE.length] }} />
                      <span className="text-xs text-muted-foreground">{key} <span className="font-medium text-foreground">{val}</span></span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* ── Fee tiers ── */}
      <div className="rounded-xl border bg-card px-6 py-5">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Répartition par cachet estimé</h2>
        </div>
        {data?.by_fee_tier ? (
          <div className="space-y-2.5">
            {feeOrdered.map((tier, i) => {
              const val = (data.by_fee_tier as Record<string, number>)[tier] || 0;
              return (
                <div key={tier} className="flex items-center gap-2.5">
                  <span className="w-16 text-xs text-muted-foreground font-medium">{tier}</span>
                  <div className="flex-1 h-[7px] rounded-full bg-muted overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${(val / feeMax) * 100}%` }} transition={{ duration: 0.5, delay: i * 0.05 }} className="h-full rounded-full" style={{ backgroundColor: feeColors[i] }} />
                  </div>
                  <span className="w-6 text-right text-xs font-medium tabular-nums">{val}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-muted-foreground">Aucune donnée</p>
        )}
      </div>

      {/* ── Timeline + Heatmap ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border bg-card px-6 py-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Activité (12 derniers mois)</h2>
          </div>
          {timeline.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">Pas de données</p>
          ) : (
            <div className="flex items-end gap-[3px] h-36">
              {timeline.map((d) => (
                <div key={d.month} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[9px] text-muted-foreground font-medium tabular-nums">{d.count || ""}</span>
                  <div className="w-full rounded-t-sm bg-muted relative overflow-hidden" style={{ height: "100%" }}>
                    <motion.div initial={{ height: 0 }} animate={{ height: `${(d.count / maxTimeline) * 100}%` }} transition={{ duration: 0.5 }} className="absolute bottom-0 w-full rounded-t-sm bg-primary" />
                  </div>
                  <span className="text-[9px] text-muted-foreground">{d.month.slice(5)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border bg-card px-6 py-5">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Calendrier à venir</h2>
          </div>
          {heatmap.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">Pas de données</p>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {heatmap.map((d) => {
                const intensity = d.count / maxHeatmap;
                const bg = intensity === 0 ? "bg-muted" : intensity < 0.25 ? "bg-primary/10" : intensity < 0.5 ? "bg-primary/20" : intensity < 0.75 ? "bg-primary/40 text-white" : "bg-primary text-white";
                return (
                  <div key={d.month} className={`rounded-lg p-2.5 text-center transition-colors ${bg}`}>
                    <p className="text-[10px] font-medium">{d.label}</p>
                    <p className="text-lg font-bold tabular-nums">{d.count}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Funnel ── */}
      {fn && (
        <div className="rounded-xl border bg-card px-6 py-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Entonnoir de qualification</h2>
            </div>
            <span className="text-[11px] text-muted-foreground">{fn.actionable} actionnables sur {fn.detected} détectés</span>
          </div>
          <div className="space-y-3">
            {funnelSteps.map((s, i) => (
              <div key={s.label} className="flex items-center gap-3">
                <span className="w-28 text-[13px] text-muted-foreground">{s.label}</span>
                <div className="flex-1 h-7 rounded-lg bg-muted overflow-hidden relative">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(s.value / funnelMax) * 100}%` }}
                    transition={{ duration: 0.6, delay: i * 0.08 }}
                    className="h-full rounded-lg flex items-center px-2.5"
                    style={{ backgroundColor: s.color }}
                  >
                    <span className="text-xs text-white font-bold tabular-nums">{s.value}</span>
                  </motion.div>
                </div>
                <span className="w-10 text-right text-xs text-muted-foreground tabular-nums">{funnelMax > 0 ? Math.round((s.value / funnelMax) * 100) : 0}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <AnalyticsContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
