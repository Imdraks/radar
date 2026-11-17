"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Eye,
  Plus,
  Trash2,
  Trophy,
  Target,
  Users,
  Loader2,
  MapPin,
  Music,
  Calendar,
  ArrowRight,
} from "lucide-react";
import { competitiveApi, analyticsV2Api } from "@/lib/api";
import { AppLayout, ProtectedRoute } from "@/components/layout";

// ── Types ──

interface Competitor {
  id: number;
  name: string;
  keywords: string[];
  website?: string;
  notes?: string;
  is_active: boolean;
  mentions_count: number;
  created_at: string;
}

interface Winner {
  organization: string;
  wins: number;
  total_value: number;
  categories: string[];
  avg_value: number;
}

interface WinnersData {
  period: string;
  total_won: number;
  unique_winners: number;
  top_winners: Winner[];
  potential_competitors: Winner[];
  insights: string[];
}

interface GapsData {
  underserved_zones: {
    city: string;
    scored_artists: number;
    avg_score: number;
    upcoming_events: number;
  }[];
  underrepresented_genres: {
    genre: string;
    growing_artists: number;
    avg_velocity: number;
    upcoming_events: number;
  }[];
  empty_slots: {
    month: string;
    city: string;
  }[];
}

// ── Helpers ──

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };
const fadeUp = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.35 } } };

// ── Main ──

function CompetitiveContent() {
  const queryClient = useQueryClient();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newCompetitor, setNewCompetitor] = useState({ name: "", keywords: "" });

  const { data: competitors, isLoading: competitorsLoading } = useQuery<Competitor[]>({
    queryKey: ["competitive", "competitors"],
    queryFn: competitiveApi.getCompetitors,
  });

  const { data: winners, isLoading: winnersLoading } = useQuery<WinnersData>({
    queryKey: ["competitive", "winners"],
    queryFn: () => competitiveApi.getWinnersAnalysis("90d"),
  });

  const { data: gaps, isLoading: gapsLoading } = useQuery<GapsData>({
    queryKey: ["analytics-v2", "competitive-gaps"],
    queryFn: () => analyticsV2Api.getCompetitiveGaps(),
    refetchInterval: 120_000,
  });

  const addMutation = useMutation({
    mutationFn: competitiveApi.addCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["competitive"] });
      setIsAddDialogOpen(false);
      setNewCompetitor({ name: "", keywords: "" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: competitiveApi.deleteCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["competitive"] });
    },
  });

  const handleAddCompetitor = () => {
    if (!newCompetitor.name.trim()) return;
    const keywords = newCompetitor.keywords
      .split(",")
      .map((k) => k.trim())
      .filter((k) => k.length > 0);
    addMutation.mutate({
      name: newCompetitor.name.trim(),
      keywords: keywords.length > 0 ? keywords : [newCompetitor.name.toLowerCase()],
    });
  };

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);

  const kpiItems = [
    { label: "Concurrents suivis", value: competitors?.length ?? 0, icon: Eye, color: "#0000FF" },
    { label: "Zones sous-couvertes", value: gaps?.underserved_zones?.length ?? 0, icon: MapPin, color: "#f59e0b" },
    { label: "Genres en croissance", value: gaps?.underrepresented_genres?.length ?? 0, icon: Music, color: "#7c3aed" },
    { label: "Créneaux vides", value: gaps?.empty_slots?.length ?? 0, icon: Calendar, color: "#ef4444" },
  ];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-8 space-y-8">
      {/* ── Header ── */}
      <div>
        <h1 className="text-[1.65rem] font-semibold tracking-tight">Veille Concurrentielle</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Concurrents, dynamiques du marché et espaces à prendre</p>
      </div>

      {/* ── KPIs ── */}
      <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiItems.map(({ label, value, icon: Icon, color }) => (
          <motion.div key={label} variants={fadeUp}>
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ backgroundColor: `${color}10` }}>
                  <Icon className="h-[18px] w-[18px]" style={{ color }} />
                </div>
              </div>
              <p className="text-2xl font-bold tracking-tight">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Tabs ── */}
      <Tabs defaultValue="competitors" className="space-y-6">
        <TabsList className="bg-muted/60 p-1">
          <TabsTrigger value="competitors" className="text-xs">Concurrents surveillés</TabsTrigger>
          <TabsTrigger value="market" className="text-xs">Activité du marché</TabsTrigger>
          <TabsTrigger value="gaps" className="text-xs">Espaces à prendre</TabsTrigger>
        </TabsList>

        {/* ── Tab 1: Concurrents ── */}
        <TabsContent value="competitors">
          <div className="rounded-xl border bg-card">
            <div className="flex items-center justify-between px-6 pt-5 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold">Concurrents surveillés</h2>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5">Suivez les acteurs du marché</p>
              </div>
              <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="h-8 text-xs">
                    <Plus className="h-3.5 w-3.5 mr-1" />
                    Ajouter
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Ajouter un concurrent</DialogTitle>
                    <DialogDescription>Surveillez ce concurrent dans le marché</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div>
                      <label className="text-sm font-medium">Nom</label>
                      <Input placeholder="Ex: Live Nation" value={newCompetitor.name} onChange={(e) => setNewCompetitor({ ...newCompetitor, name: e.target.value })} />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Mots-clés (optionnel)</label>
                      <Input placeholder="Ex: livenation, live-nation" value={newCompetitor.keywords} onChange={(e) => setNewCompetitor({ ...newCompetitor, keywords: e.target.value })} />
                      <p className="text-xs text-muted-foreground mt-1">Séparés par virgule</p>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>Annuler</Button>
                    <Button onClick={handleAddCompetitor} disabled={addMutation.isPending}>
                      {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Ajouter"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            <div className="px-4 pb-4">
              {competitorsLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-6 w-6 animate-spin text-primary/60" />
                </div>
              ) : competitors && competitors.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Nom</TableHead>
                      <TableHead className="text-xs">Mots-clés</TableHead>
                      <TableHead className="text-xs">Mentions</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {competitors.map((comp) => (
                      <TableRow key={comp.id} className="hover:bg-muted/40">
                        <TableCell className="font-medium text-[13px]">{comp.name}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {comp.keywords.slice(0, 3).map((kw) => (
                              <Badge key={kw} variant="secondary" className="text-[10px] px-1.5 py-0">{kw}</Badge>
                            ))}
                            {comp.keywords.length > 3 && (
                              <Badge variant="outline" className="text-[10px] px-1.5 py-0">+{comp.keywords.length - 3}</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={`text-xs font-medium tabular-nums ${comp.mentions_count > 0 ? "text-primary" : "text-muted-foreground"}`}>
                            {comp.mentions_count}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => deleteMutation.mutate(comp.id)}>
                            <Trash2 className="h-3.5 w-3.5 text-red-500" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12">
                  <Users className="h-8 w-8 mx-auto text-muted-foreground/40 mb-3" />
                  <p className="text-sm text-muted-foreground">Aucun concurrent surveillé</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Ajoutez des concurrents pour commencer</p>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* ── Tab 2: Activité du marché ── */}
        <TabsContent value="market" className="space-y-6">
          <div className="rounded-xl border bg-card">
            <div className="flex items-center gap-2 px-6 pt-5 pb-3">
              <Trophy className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Qui gagne sur le terrain ?</h2>
            </div>
            <div className="px-4 pb-4">
              {winnersLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-6 w-6 animate-spin text-primary/60" />
                </div>
              ) : winners && winners.top_winners.length > 0 ? (
                <div className="space-y-1.5">
                  {winners.top_winners.slice(0, 8).map((w, i) => (
                    <motion.div
                      key={w.organization}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.04 }}
                      className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold text-muted-foreground w-5 tabular-nums">#{i + 1}</span>
                        <div>
                          <p className="text-[13px] font-medium">{w.organization}</p>
                          <div className="flex gap-1 mt-0.5">
                            {w.categories.slice(0, 2).map((c) => (
                              <Badge key={c} variant="outline" className="text-[10px] px-1.5 py-0">{c}</Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-[13px] font-bold tabular-nums">{w.wins} victoires</p>
                        <p className="text-[11px] text-muted-foreground">{formatCurrency(w.total_value)}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">Pas assez de données</p>
              )}
            </div>
          </div>

          {winners && winners.potential_competitors.length > 0 && (
            <div className="rounded-xl border bg-card px-6 py-5">
              <div className="flex items-center gap-2 mb-3">
                <Target className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold">Concurrents potentiels à surveiller</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {winners.potential_competitors.map((comp) => (
                  <button
                    key={comp.organization}
                    className="flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs transition-colors hover:bg-muted"
                    onClick={() => {
                      setNewCompetitor({ name: comp.organization, keywords: "" });
                      setIsAddDialogOpen(true);
                    }}
                  >
                    <Plus className="h-3 w-3" />
                    {comp.organization} ({comp.wins})
                  </button>
                ))}
              </div>
            </div>
          )}

          {winners && winners.insights.length > 0 && (
            <div className="rounded-xl border border-primary/20 bg-primary/[0.03] px-6 py-4">
              <div className="space-y-1">
                {winners.insights.map((insight, i) => (
                  <p key={i} className="text-[13px]">{insight}</p>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* ── Tab 3: Espaces à prendre ── */}
        <TabsContent value="gaps" className="space-y-6">
          {gapsLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-primary/60" />
            </div>
          ) : (
            <>
              {/* Underserved zones */}
              <div className="rounded-xl border bg-card">
                <div className="flex items-center justify-between px-6 pt-5 pb-1">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <h2 className="text-sm font-semibold">Zones sous-couvertes</h2>
                  </div>
                  <Link href="/map" className="text-[11px] text-primary hover:underline flex items-center gap-1">
                    Carte <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
                <p className="text-[11px] text-muted-foreground px-6 pb-3">Villes avec des artistes scorés mais peu d&apos;événements</p>
                <div className="px-4 pb-4">
                  {gaps?.underserved_zones && gaps.underserved_zones.length > 0 ? (
                    <div className="space-y-1.5">
                      {gaps.underserved_zones.map((z, i) => (
                        <motion.div
                          key={z.city}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: i * 0.04 }}
                          className="flex items-center justify-between px-3 py-2.5 rounded-lg border border-amber-200/40 bg-amber-50/30 dark:border-amber-800/20 dark:bg-amber-950/10"
                        >
                          <div className="flex items-center gap-3">
                            <MapPin className="h-3.5 w-3.5 text-amber-600 flex-shrink-0" />
                            <div>
                              <p className="text-[13px] font-medium">{z.city}</p>
                              <p className="text-[11px] text-muted-foreground">{z.scored_artists} artistes scorés · score moyen {z.avg_score}</p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-[10px] bg-amber-100/60 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800/30">
                            {z.upcoming_events} événement{z.upcoming_events !== 1 ? "s" : ""}
                          </Badge>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <p className="py-8 text-center text-sm text-muted-foreground">Toutes les zones actives sont bien couvertes</p>
                  )}
                </div>
              </div>

              {/* Underrepresented genres */}
              <div className="rounded-xl border bg-card">
                <div className="px-6 pt-5 pb-1">
                  <div className="flex items-center gap-2">
                    <Music className="h-4 w-4 text-muted-foreground" />
                    <h2 className="text-sm font-semibold">Genres sous-représentés</h2>
                  </div>
                </div>
                <p className="text-[11px] text-muted-foreground px-6 pb-3">Genres avec des artistes en croissance mais peu d&apos;événements</p>
                <div className="px-4 pb-4">
                  {gaps?.underrepresented_genres && gaps.underrepresented_genres.length > 0 ? (
                    <div className="space-y-1.5">
                      {gaps.underrepresented_genres.map((g, i) => (
                        <motion.div
                          key={g.genre}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: i * 0.04 }}
                          className="flex items-center justify-between px-3 py-2.5 rounded-lg border border-primary/10 bg-primary/[0.02]"
                        >
                          <div className="flex items-center gap-3">
                            <Music className="h-3.5 w-3.5 text-primary flex-shrink-0" />
                            <div>
                              <p className="text-[13px] font-medium capitalize">{g.genre}</p>
                              <p className="text-[11px] text-muted-foreground">{g.growing_artists} artistes en croissance · vélocité +{g.avg_velocity}%</p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-[10px] bg-primary/5 text-primary border-primary/20">
                            {g.upcoming_events} événement{g.upcoming_events !== 1 ? "s" : ""}
                          </Badge>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <p className="py-8 text-center text-sm text-muted-foreground">Tous les genres en croissance sont bien couverts</p>
                  )}
                </div>
              </div>

              {/* Empty slots */}
              <div className="rounded-xl border bg-card px-6 py-5">
                <div className="flex items-center gap-2 mb-1">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold">Créneaux vides</h2>
                </div>
                <p className="text-[11px] text-muted-foreground mb-4">Mois sans événements dans des villes actives</p>
                {gaps?.empty_slots && gaps.empty_slots.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {gaps.empty_slots.map((s, i) => (
                      <span
                        key={`${s.month}-${s.city}-${i}`}
                        className="inline-flex items-center rounded-full border border-red-200/50 bg-red-50/40 px-3 py-1 text-xs text-red-700 dark:border-red-800/30 dark:bg-red-950/10 dark:text-red-400"
                      >
                        <Calendar className="h-3 w-3 mr-1.5" />
                        {s.month} · {s.city}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="py-6 text-center text-sm text-muted-foreground">Pas de créneau vide détecté</p>
                )}
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function CompetitivePage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <CompetitiveContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
