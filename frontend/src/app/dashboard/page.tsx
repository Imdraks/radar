"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Target,
  TrendingUp,
  Calendar,
  Clock,
  ArrowRight,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/components/ui/toaster";
import { dashboardApi, ingestionApi } from "@/lib/api";
import {
  formatCurrency,
  formatRelativeDate,
  getStatusColor,
  getStatusLabel,
  getScoreColor,
  truncate,
} from "@/lib/utils";
import type { Opportunity, IngestionRun, DashboardStats } from "@/lib/types";
import { UnifiedCollectModal } from "@/components/collection";
import { ArtistAnalysisDialog } from "@/components/intelligence";
import { EmergingArtistsWidget } from "@/components/intelligence/EmergingArtistsWidget";
import { DashboardOnboarding } from "@/components/onboarding";

function DashboardContent() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: dashboardApi.getStats,
  });

  const { data: topOpportunities, isLoading: topLoading } = useQuery<Opportunity[]>({
    queryKey: ["dashboard", "top-opportunities"],
    queryFn: () => dashboardApi.getTopOpportunities(5),
  });

  const { data: upcomingDeadlines, isLoading: deadlinesLoading } = useQuery<Opportunity[]>({
    queryKey: ["dashboard", "upcoming-deadlines"],
    queryFn: () => dashboardApi.getUpcomingDeadlines(14, 5),
  });

  const { data: recentIngestions, isLoading: ingestionsLoading, refetch: refetchIngestions } = useQuery<IngestionRun[]>({
    queryKey: ["dashboard", "recent-ingestions"],
    queryFn: () => dashboardApi.getRecentIngestions(5),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Vue d&apos;ensemble de vos opportunités
          </p>
        </div>
        
        <div className="flex flex-wrap gap-2">
          {/* Bouton de collecte unifiée */}
          <div data-onboarding="collect-button">
            <UnifiedCollectModal />
          </div>
          
          {/* Analyse d'artiste */}
          <ArtistAnalysisDialog />
        </div>
      </div>

      {/* Stats Cards */}
      <div data-onboarding="stats-cards" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Opportunités
            </CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? "..." : stats?.total_opportunities || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Nouvelles aujourd&apos;hui
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              +{statsLoading ? "..." : stats?.new_today || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cette semaine
            </CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              +{statsLoading ? "..." : stats?.new_this_week || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Score moyen
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? "..." : (stats?.avg_score || 0).toFixed(1)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Status breakdown */}
      {stats?.by_status && (
        <Card>
          <CardHeader>
            <CardTitle>Répartition par statut</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(stats.by_status).map(([status, count]) => {
                const percentage = (count / stats.total_opportunities) * 100;
                return (
                  <div key={status} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <Badge className={getStatusColor(status)} variant="outline">
                          {getStatusLabel(status)}
                        </Badge>
                      </span>
                      <span className="text-muted-foreground">{count}</span>
                    </div>
                    <Progress value={percentage} className="h-2" />
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Opportunities */}
        <Card data-onboarding="top-opportunities">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Top Opportunités</CardTitle>
            <Link href="/opportunities?sort_by=score&sort_order=desc">
              <Button variant="ghost" size="sm">
                Voir tout
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              {topLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  Chargement...
                </div>
              ) : topOpportunities?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Aucune opportunité
                </div>
              ) : (
                <div className="space-y-3">
                  {topOpportunities?.map((opp) => (
                    <Link
                      key={opp.id}
                      href={`/opportunities/${opp.id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{opp.title}</p>
                          <p className="text-sm text-muted-foreground truncate">
                            {opp.organization_name || "Organisation inconnue"}
                          </p>
                        </div>
                        <div className={`text-lg font-bold ${getScoreColor(opp.score)}`}>
                          {opp.score?.toFixed(0) || 0}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge className={getStatusColor(opp.status)} variant="outline">
                          {getStatusLabel(opp.status)}
                        </Badge>
                        {opp.budget_amount && (
                          <span className="text-sm text-muted-foreground">
                            {formatCurrency(opp.budget_amount)}
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Upcoming Deadlines */}
        <Card data-onboarding="deadlines">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Deadlines à venir</CardTitle>
            <Link href="/opportunities?sort_by=deadline_at&sort_order=asc">
              <Button variant="ghost" size="sm">
                Voir tout
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              {deadlinesLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  Chargement...
                </div>
              ) : upcomingDeadlines?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Aucune deadline à venir
                </div>
              ) : (
                <div className="space-y-3">
                  {upcomingDeadlines?.map((opp) => (
                    <Link
                      key={opp.id}
                      href={`/opportunities/${opp.id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{opp.title}</p>
                          <p className="text-sm text-muted-foreground truncate">
                            {opp.organization_name || "Organisation inconnue"}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 text-orange-600">
                          <Clock className="h-4 w-4" />
                          <span className="text-sm font-medium">
                            {formatRelativeDate(opp.deadline_at)}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Emerging Artists Widget */}
      <div data-onboarding="emerging-artists">
        <EmergingArtistsWidget />
      </div>

      {/* Recent Ingestions */}
      <Card data-onboarding="ingestion-status">
        <CardHeader>
          <CardTitle>Dernières collectes</CardTitle>
        </CardHeader>
        <CardContent>
          {ingestionsLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Chargement...
            </div>
          ) : recentIngestions?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Aucune collecte récente
            </div>
          ) : (
            <div className="space-y-3">
              {recentIngestions?.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={run.status === "completed" ? "default" : "destructive"}>
                      {run.status === "completed" ? "Succès" : run.status}
                    </Badge>
                    <div>
                      <p className="font-medium">
                        {run.source_config?.name || run.source_type?.toUpperCase() || "Source"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {formatRelativeDate(run.started_at)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-green-600">
                      +{run.items_new} nouvelles
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {run.items_found} trouvées, {run.items_duplicate} doublons
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <DashboardOnboarding />
        <DashboardContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
