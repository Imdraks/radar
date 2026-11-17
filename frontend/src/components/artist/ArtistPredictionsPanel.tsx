"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  LineChart,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  RefreshCw,
  Info,
  BarChart3,
  Target,
  Zap,
  CheckCircle,
  XCircle,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";

// ============================================================================
// TYPES
// ============================================================================

interface PredictionScenario {
  value_30d: number;
  value_90d: number;
  growth_rate: number;
}

interface PredictionExplanation {
  text: string;
  impact: "positive" | "negative" | "neutral";
  weight: number;
}

interface HistoricalDataPoint {
  date: string;
  listeners: number;
}

interface ArtistPredictionData {
  artist_name: string;
  current_listeners: number;
  pessimistic: PredictionScenario;
  central: PredictionScenario;
  optimistic: PredictionScenario;
  growth_probability: number;
  confidence_score: number;
  confidence_label: string;
  historical_data: HistoricalDataPoint[];
  explanations: PredictionExplanation[];
  snapshot_count: number;
  data_span_days: number;
  last_update: string | null;
  is_valid: boolean;
  error_message: string | null;
}

interface ArtistPredictionsPanelProps {
  artistName: string;
  onRefresh?: () => void;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(0)}K`;
  return num.toString();
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

function getConfidenceBadgeColor(label: string): string {
  switch (label) {
    case "Élevée":
      return "bg-green-100 text-green-800 border-green-200";
    case "Moyenne":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "Faible":
      return "bg-red-100 text-red-800 border-red-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

function getImpactIcon(impact: string) {
  switch (impact) {
    case "positive":
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    case "negative":
      return <TrendingDown className="h-4 w-4 text-red-500" />;
    default:
      return <Info className="h-4 w-4 text-gray-500" />;
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

export function ArtistPredictionsPanel({ artistName, onRefresh }: ArtistPredictionsPanelProps) {
  // Fetch predictions from API
  const {
    data: prediction,
    isLoading,
    isError,
    refetch,
  } = useQuery<ArtistPredictionData>({
    queryKey: ["artist-prediction", artistName],
    queryFn: async () => {
      const response = await api.get(`/artist-predictions/${encodeURIComponent(artistName)}`);
      return response.data;
    },
    enabled: !!artistName,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-muted-foreground mb-4">Erreur lors du chargement des prédictions</p>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Réessayer
        </Button>
      </div>
    );
  }

  // Invalid prediction (not enough data)
  if (!prediction?.is_valid) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
        </div>
        <h3 className="text-lg font-semibold mb-2">Prédictions indisponibles</h3>
        <p className="text-muted-foreground mb-4 max-w-md mx-auto">
          {prediction?.error_message || "Historique insuffisant pour générer des prédictions"}
        </p>
        <p className="text-sm text-muted-foreground mb-4">
          Les prédictions nécessitent au moins 2 analyses de cet artiste.
        </p>
        <Button variant="outline" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Rafraîchir l'analyse
        </Button>
      </div>
    );
  }

  // Prepare chart data
  const chartData = prepareChartData(prediction);

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Spotify 30 jours */}
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="text-sm text-muted-foreground mb-1">Spotify à 30 jours</div>
            <div className="text-lg font-bold">
              {formatNumber(prediction.pessimistic.value_30d)} - {formatNumber(prediction.optimistic.value_30d)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Central: {formatNumber(prediction.central.value_30d)}
            </div>
          </CardContent>
        </Card>

        {/* Spotify 90 jours */}
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="text-sm text-muted-foreground mb-1">Spotify à 90 jours</div>
            <div className="text-lg font-bold">
              {formatNumber(prediction.pessimistic.value_90d)} - {formatNumber(prediction.optimistic.value_90d)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Central: {formatNumber(prediction.central.value_90d)}
            </div>
          </CardContent>
        </Card>

        <Card><CardContent className="pt-4 pb-3"><p className="text-sm">Confiance non calibrée</p><p className="text-xs text-muted-foreground">Scénarios indicatifs fondés sur l’historique disponible. Aucune probabilité de croissance validée.</p></CardContent></Card>
      </div>

      {/* Low confidence warning */}
      {prediction.confidence_label === "Faible" && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-amber-800 dark:text-amber-200">
              Prédiction à faible confiance
            </p>
            <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
              Les résultats sont indicatifs. Plus d'analyses amélioreront la précision.
            </p>
          </div>
        </div>
      )}

      {/* Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-purple-500" />
            Projection Spotify
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPessimistic" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#9ca3af" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#9ca3af" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorCentral" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorOptimistic" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }} 
                  tickFormatter={(value) => formatDate(value)}
                />
                <YAxis 
                  tick={{ fontSize: 12 }} 
                  tickFormatter={(value) => formatNumber(value)}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const data = payload[0]?.payload;
                    return (
                      <div className="bg-background border rounded-lg shadow-lg p-3">
                        <p className="font-medium mb-2">{formatDate(label)}</p>
                        {data.historical && (
                          <p className="text-sm">
                            <span className="text-purple-600">●</span> Réel: {formatNumber(data.historical)}
                          </p>
                        )}
                        {data.central && !data.historical && (
                          <>
                            <p className="text-sm">
                              <span className="text-green-600">●</span> Optimiste: {formatNumber(data.optimistic)}
                            </p>
                            <p className="text-sm">
                              <span className="text-purple-600">●</span> Central: {formatNumber(data.central)}
                            </p>
                            <p className="text-sm">
                              <span className="text-gray-500">●</span> Pessimiste: {formatNumber(data.pessimistic)}
                            </p>
                          </>
                        )}
                      </div>
                    );
                  }}
                />
                <ReferenceLine x={chartData.find(d => d.isToday)?.date} stroke="#6b7280" strokeDasharray="5 5" />
                
                {/* Historical data */}
                <Area
                  type="monotone"
                  dataKey="historical"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  fill="url(#colorCentral)"
                  dot={false}
                />
                
                {/* Projections */}
                <Area
                  type="monotone"
                  dataKey="optimistic"
                  stroke="#22c55e"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  fill="url(#colorOptimistic)"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="central"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  fill="url(#colorCentral)"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="pessimistic"
                  stroke="#9ca3af"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  fill="url(#colorPessimistic)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500" />
              <span>Historique / Central</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Optimiste</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-400" />
              <span>Pessimiste</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Explanations */}
      {prediction.explanations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              Pourquoi cette prédiction
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {prediction.explanations.map((explanation, index) => (
                <div
                  key={index}
                  className={`flex items-center gap-3 p-3 rounded-lg ${
                    explanation.impact === "positive"
                      ? "bg-green-50 dark:bg-green-900/20"
                      : explanation.impact === "negative"
                      ? "bg-red-50 dark:bg-red-900/20"
                      : "bg-gray-50 dark:bg-gray-800/50"
                  }`}
                >
                  {getImpactIcon(explanation.impact)}
                  <span className="text-sm">{explanation.text}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <div className="text-center text-xs text-muted-foreground space-y-1">
        <p>
          Basé sur {prediction.snapshot_count} analyse(s) · 
          {prediction.data_span_days > 0 && ` Données sur ${prediction.data_span_days} jours ·`}
          {prediction.last_update && ` Dernière mise à jour: ${formatDate(prediction.last_update)}`}
        </p>
        <p className="italic">
          Les prédictions Radar sont des projections statistiques basées sur les tendances réelles observées sur les plateformes musicales.
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// CHART DATA PREPARATION
// ============================================================================

function prepareChartData(prediction: ArtistPredictionData) {
  const data: any[] = [];
  const today = new Date();
  
  // Add historical data
  prediction.historical_data.forEach((point) => {
    data.push({
      date: point.date,
      historical: point.listeners,
      isToday: false,
    });
  });
  
  // Add today marker
  const todayStr = today.toISOString();
  data.push({
    date: todayStr,
    historical: prediction.current_listeners,
    central: prediction.current_listeners,
    pessimistic: prediction.current_listeners,
    optimistic: prediction.current_listeners,
    isToday: true,
  });
  
  // Add 30-day projection
  const day30 = new Date(today);
  day30.setDate(day30.getDate() + 30);
  data.push({
    date: day30.toISOString(),
    central: prediction.central.value_30d,
    pessimistic: prediction.pessimistic.value_30d,
    optimistic: prediction.optimistic.value_30d,
    isToday: false,
  });
  
  // Add 90-day projection
  const day90 = new Date(today);
  day90.setDate(day90.getDate() + 90);
  data.push({
    date: day90.toISOString(),
    central: prediction.central.value_90d,
    pessimistic: prediction.pessimistic.value_90d,
    optimistic: prediction.optimistic.value_90d,
    isToday: false,
  });
  
  return data;
}

export default ArtistPredictionsPanel;
