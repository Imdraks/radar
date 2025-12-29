"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Activity,
  Server,
  CheckCircle,
  AlertCircle,
  XCircle,
  RefreshCw,
  Loader2,
  PowerOff,
  BarChart3,
  Clock,
  Copy,
} from "lucide-react";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toaster";
import { sourceHealthApi, sourcesApi } from "@/lib/api";
import type { SourceHealthOverview, SourceHealthSummary, SourceHealthMetrics } from "@/lib/types";

function getHealthColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 50) return "text-yellow-500";
  return "text-red-500";
}

function getHealthBgColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 50) return "bg-yellow-500";
  return "bg-red-500";
}

function getStatusIcon(status: "healthy" | "warning" | "critical") {
  switch (status) {
    case "healthy":
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case "warning":
      return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    case "critical":
      return <XCircle className="h-5 w-5 text-red-500" />;
  }
}

function getRecommendationBadge(rec: string | null | undefined) {
  switch (rec) {
    case "disable":
      return <Badge variant="destructive">À désactiver</Badge>;
    case "repair":
      return <Badge className="bg-yellow-500 text-white">À réparer</Badge>;
    case "prioritize":
      return <Badge className="bg-green-500 text-white">À prioriser</Badge>;
    default:
      return null;
  }
}

function SourceHealthCard({
  summary,
  onToggle,
  isToggling,
}: {
  summary: SourceHealthSummary;
  onToggle: (sourceId: string, isActive: boolean) => void;
  isToggling: boolean;
}) {
  const { source_id, source_name, is_active, avg_health_score, total_items_last_7_days, error_rate_last_7_days, recommendation } = summary;
  const status = avg_health_score >= 80 ? "healthy" : avg_health_score >= 50 ? "warning" : "critical";

  return (
    <Card className={`border-l-4 ${getHealthBgColor(avg_health_score)} hover:shadow-md transition-shadow`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            {getStatusIcon(status)}
            <div>
              <h3 className="font-semibold">{source_name}</h3>
              {getRecommendationBadge(recommendation)}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={is_active}
              onCheckedChange={(checked) => onToggle(source_id, checked)}
              disabled={isToggling}
            />
          </div>
        </div>

        {/* Health score */}
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-1">
            <span>Santé</span>
            <span className={`font-bold ${getHealthColor(avg_health_score)}`}>
              {avg_health_score.toFixed(0)}%
            </span>
          </div>
          <Progress value={avg_health_score} className="h-2" />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Items 7j</p>
            <p className="font-semibold">{total_items_last_7_days}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Taux erreur</p>
            <p className={`font-semibold ${error_rate_last_7_days > 0.1 ? 'text-red-500' : 'text-green-500'}`}>
              {(error_rate_last_7_days * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SourceHealthContent() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);

  // Fetch overview
  const { data: overview, isLoading: overviewLoading } = useQuery<SourceHealthOverview>({
    queryKey: ["source-health", "overview"],
    queryFn: sourceHealthApi.getOverview,
  });

  // Fetch detailed metrics for selected source
  const { data: sourceMetrics, isLoading: metricsLoading } = useQuery<SourceHealthMetrics[]>({
    queryKey: ["source-health", "source", selectedSourceId],
    queryFn: () => sourceHealthApi.getOne(selectedSourceId!, 30),
    enabled: !!selectedSourceId,
  });

  // Toggle source mutation
  const toggleMutation = useMutation({
    mutationFn: ({ sourceId, isActive }: { sourceId: number; isActive: boolean }) =>
      sourceHealthApi.updateSource(sourceId, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["source-health"] });
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      addToast({
        title: "Source mise à jour",
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de mettre à jour la source",
        type: "error",
      });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Activity className="h-8 w-8 text-green-500" />
            Source Health
          </h1>
          <p className="text-muted-foreground">
            Monitoring et qualité de vos sources de données
          </p>
        </div>

        <div className="flex gap-2">
          <Link href="/sources">
            <Button variant="outline">
              <Server className="h-4 w-4 mr-2" />
              Gérer les sources
            </Button>
          </Link>
          <Button
            onClick={() => queryClient.invalidateQueries({ queryKey: ["source-health"] })}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualiser
          </Button>
        </div>
      </div>

      {/* Overview stats */}
      {overviewLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : overview ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${getHealthBgColor(overview.avg_health_score)} bg-opacity-20`}>
                    <Activity className={`h-5 w-5 ${getHealthColor(overview.avg_health_score)}`} />
                  </div>
                  <div>
                    <p className={`text-2xl font-bold ${getHealthColor(overview.avg_health_score)}`}>
                      {overview.avg_health_score.toFixed(0)}%
                    </p>
                    <p className="text-sm text-muted-foreground">Santé moyenne</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-100">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-600">{overview.total_active}</p>
                    <p className="text-sm text-muted-foreground">Sources actives</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-gray-100">
                    <PowerOff className="h-5 w-5 text-gray-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-600">{overview.total_inactive}</p>
                    <p className="text-sm text-muted-foreground">Sources inactives</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-orange-100">
                    <AlertCircle className="h-5 w-5 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-orange-600">{overview.sources_needing_attention}</p>
                    <p className="text-sm text-muted-foreground">À surveiller</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sources grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {overview.sources.map((summary) => (
              <div
                key={summary.source_id}
                onClick={() => setSelectedSourceId(Number(summary.source_id))}
                className="cursor-pointer"
              >
                <SourceHealthCard
                  summary={summary}
                  onToggle={(sourceId, isActive) =>
                    toggleMutation.mutate({ sourceId: Number(sourceId), isActive })
                  }
                  isToggling={toggleMutation.isPending}
                />
              </div>
            ))}
          </div>

          {overview.sources.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center">
                <Server className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="font-semibold text-lg mb-2">Aucune source configurée</h3>
                <p className="text-muted-foreground mb-4">
                  Ajoutez des sources pour commencer le monitoring
                </p>
                <Link href="/sources">
                  <Button>
                    Configurer les sources
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}

      {/* Detailed metrics for selected source */}
      {selectedSourceId && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Historique détaillé
            </CardTitle>
            <CardDescription>
              Métriques des 30 derniers jours
            </CardDescription>
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : sourceMetrics && sourceMetrics.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Opportunités</TableHead>
                    <TableHead className="text-right">Doublons</TableHead>
                    <TableHead className="text-right">Score moy.</TableHead>
                    <TableHead className="text-right">Erreurs</TableHead>
                    <TableHead className="text-right">Fraîcheur</TableHead>
                    <TableHead className="text-right">Santé</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sourceMetrics.slice(0, 14).map((metric) => (
                    <TableRow key={metric.date}>
                      <TableCell>
                        {new Date(metric.date).toLocaleDateString("fr-FR", {
                          day: "numeric",
                          month: "short",
                        })}
                      </TableCell>
                      <TableCell className="text-right">{metric.opportunities_found}</TableCell>
                      <TableCell className="text-right">
                        {metric.duplicates_found > 0 && (
                          <Badge variant="secondary" className="text-xs">
                            <Copy className="h-3 w-3 mr-1" />
                            {metric.duplicates_found}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">{metric.avg_score.toFixed(0)}%</TableCell>
                      <TableCell className="text-right">
                        {metric.error_rate > 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            {metric.error_rate.toFixed(0)}%
                          </Badge>
                        ) : (
                          <span className="text-green-500">0%</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {metric.freshness_hours < 24 ? (
                          <span className="text-green-500">{metric.freshness_hours.toFixed(0)}h</span>
                        ) : (
                          <span className="text-yellow-500">{metric.freshness_hours.toFixed(0)}h</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={getHealthColor(metric.health_score)}>
                          {metric.health_score.toFixed(0)}%
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-center py-4 text-muted-foreground">
                Pas de données disponibles
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function SourceHealthPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <SourceHealthContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
