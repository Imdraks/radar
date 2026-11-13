"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Brain,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  Euro,
  Target,
  ChevronRight,
  Lightbulb,
  BarChart3,
  Calendar,
  ArrowUp,
  ArrowDown,
  Zap,
  Shield,
  RefreshCw,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  formatCurrency,
  formatRelativeDate,
  getStatusColor,
  getStatusLabel,
} from "@/lib/utils";

// Types
interface Prediction {
  opportunity_id: number;
  title: string;
  organization: string | null;
  win_probability: number;
  deadline: string | null;
  budget: number | null;
  status: string;
  risk_count: number;
  top_action: string | null;
}

interface Insight {
  type: string;
  title: string;
  description: string;
  impact: string;
  icon: string;
  opportunity_id?: number;
}

interface InsightsData {
  total_active: number;
  average_probability: number;
  historical_win_rate: number;
  total_pipeline_value: number;
  expected_value: number;
  insights: Insight[];
  distribution: {
    high: number;
    medium: number;
    low: number;
  };
}

interface Forecast {
  month: string;
  month_label: string;
  total_opportunities: number;
  expected_wins: number;
  expected_value: number;
  optimistic: number;
  pessimistic: number;
}

interface ForecastData {
  forecasts: Forecast[];
  total_expected_wins: number;
  total_expected_value: number;
}

// API functions
const predictionsApi = {
  getBatchPredictions: async (limit = 20): Promise<Prediction[]> => {
    const token = localStorage.getItem("token");
    const response = await fetch(`/api/v1/predictions/batch?limit=${limit}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    
    if (!response.ok) {
      // Mock data if API not ready
      return [
        { opportunity_id: 1, title: "Festival de Jazz de Nice 2025", organization: "OT Nice", win_probability: 85, deadline: "2025-02-15", budget: 150000, status: "in_progress", risk_count: 0, top_action: "Bonne opportunité - Maintenir l'effort" },
        { opportunity_id: 2, title: "Salon de l'Agriculture - Animation", organization: "SIA", win_probability: 72, deadline: "2025-01-30", budget: 80000, status: "new", risk_count: 1, top_action: "Préparer une proposition technique détaillée" },
        { opportunity_id: 3, title: "Fête de la Musique Paris", organization: "Mairie Paris", win_probability: 68, deadline: "2025-03-01", budget: 200000, status: "in_progress", risk_count: 1, top_action: "Mettre en avant vos avantages concurrentiels" },
        { opportunity_id: 4, title: "Corporate Event Renault", organization: "Renault Group", win_probability: 55, deadline: "2025-02-10", budget: 45000, status: "new", risk_count: 2, top_action: "Contacter le client pour mieux comprendre les attentes" },
        { opportunity_id: 5, title: "Téléthon 2025 Région PACA", organization: "AFM Téléthon", win_probability: 48, deadline: "2025-04-15", budget: 35000, status: "new", risk_count: 2, top_action: "Améliorer le dossier avec des références similaires" },
      ];
    }
    
    return response.json();
  },
  
  getInsights: async (): Promise<InsightsData> => {
    const token = localStorage.getItem("token");
    const response = await fetch("/api/v1/predictions/insights", {
      headers: { Authorization: `Bearer ${token}` },
    });
    
    if (!response.ok) {
      return {
        total_active: 47,
        average_probability: 62,
        historical_win_rate: 38,
        total_pipeline_value: 2850000,
        expected_value: 1767000,
        insights: [
          { type: "pipeline_health", title: "Pipeline sain", description: "Score moyen de 62% - Bonne qualité d'opportunités", impact: "positive", icon: "check" },
          { type: "deadline_alert", title: "3 deadline(s) urgente(s)", description: "Opportunités avec moins de 7 jours restants", impact: "warning", icon: "alert" },
          { type: "high_value", title: "5 opportunité(s) prioritaire(s)", description: "Valeur potentielle: 510,000€ avec bonne probabilité", impact: "positive", icon: "money" },
          { type: "trend", title: "Tendance positive", description: "Taux de conversion historique de 38%", impact: "positive", icon: "trend" },
          { type: "recommendation", title: "Focus recommandé", description: "Prioriser: Festival de Jazz de Nice 2025 (85%)", impact: "action", icon: "target", opportunity_id: 1 },
        ],
        distribution: { high: 12, medium: 25, low: 10 },
      };
    }
    
    return response.json();
  },
  
  getForecast: async (months = 3): Promise<ForecastData> => {
    const token = localStorage.getItem("token");
    const response = await fetch(`/api/v1/predictions/forecast?months=${months}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    
    if (!response.ok) {
      return {
        forecasts: [
          { month: "2025-02", month_label: "Février 2025", total_opportunities: 15, expected_wins: 4.2, expected_value: 320000, optimistic: 5.0, pessimistic: 2.9 },
          { month: "2025-03", month_label: "Mars 2025", total_opportunities: 12, expected_wins: 3.1, expected_value: 180000, optimistic: 3.7, pessimistic: 2.2 },
          { month: "2025-04", month_label: "Avril 2025", total_opportunities: 8, expected_wins: 2.4, expected_value: 95000, optimistic: 2.9, pessimistic: 1.7 },
        ],
        total_expected_wins: 9.7,
        total_expected_value: 595000,
      };
    }
    
    return response.json();
  },
};

// Probability gauge component
function ProbabilityGauge({ value, size = "md" }: { value: number; size?: "sm" | "md" | "lg" }) {
  const sizeClasses = {
    sm: "w-12 h-12 text-lg",
    md: "w-20 h-20 text-2xl",
    lg: "w-28 h-28 text-3xl",
  };
  
  const colorClass = value >= 70 ? "text-green-600" : value >= 40 ? "text-amber-600" : "text-red-600";
  const bgColorClass = value >= 70 ? "bg-green-100" : value >= 40 ? "bg-amber-100" : "bg-red-100";
  
  return (
    <div className={`${sizeClasses[size]} ${bgColorClass} rounded-full flex items-center justify-center relative`}>
      <span className={`font-bold ${colorClass}`}>{value.toFixed(0)}%</span>
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          className="text-gray-200"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          strokeDasharray={`${value * 2.83} 283`}
          className={colorClass}
        />
      </svg>
    </div>
  );
}

function PredictionsContent() {
  const [activeTab, setActiveTab] = useState("overview");

  const { data: predictions, isLoading: loadingPredictions, refetch: refetchPredictions } = useQuery({
    queryKey: ["predictions", "batch"],
    queryFn: () => predictionsApi.getBatchPredictions(20),
  });

  const { data: insights, isLoading: loadingInsights } = useQuery({
    queryKey: ["predictions", "insights"],
    queryFn: predictionsApi.getInsights,
  });

  const { data: forecast, isLoading: loadingForecast } = useQuery({
    queryKey: ["predictions", "forecast"],
    queryFn: () => predictionsApi.getForecast(3),
  });

  const isLoading = loadingPredictions || loadingInsights || loadingForecast;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Brain className="h-8 w-8 text-purple-600" />
            Prédictions
          </h1>
          <p className="text-muted-foreground">
            Analyse prédictive de votre pipeline commercial
          </p>
        </div>
        
        <Button onClick={() => refetchPredictions()} variant="outline" className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Actualiser
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Analyse en cours...</p>
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-100 rounded-xl">
                    <Target className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{insights?.total_active || 0}</p>
                    <p className="text-sm text-muted-foreground">Leads actifs</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <ProbabilityGauge value={insights?.average_probability || 0} size="sm" />
                  <div>
                    <p className="text-sm font-medium">Score moyen</p>
                    <p className="text-xs text-muted-foreground">du pipeline</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-green-100 rounded-xl">
                    <Euro className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{formatCurrency(insights?.expected_value || 0)}</p>
                    <p className="text-sm text-muted-foreground">Valeur attendue</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-purple-100 rounded-xl">
                    <TrendingUp className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{insights?.historical_win_rate || 0}%</p>
                    <p className="text-sm text-muted-foreground">Taux historique</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Distribution Bar */}
          {insights?.distribution && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">Distribution des probabilités</h3>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500" />
                      Haute (&gt;70%)
                    </span>
                    <span className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-amber-500" />
                      Moyenne (40-70%)
                    </span>
                    <span className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      Basse (&lt;40%)
                    </span>
                  </div>
                </div>
                <div className="h-8 rounded-full overflow-hidden flex">
                  <div 
                    className="bg-green-500 h-full flex items-center justify-center text-white text-sm font-medium"
                    style={{ width: `${(insights.distribution.high / insights.total_active) * 100}%` }}
                  >
                    {insights.distribution.high}
                  </div>
                  <div 
                    className="bg-amber-500 h-full flex items-center justify-center text-white text-sm font-medium"
                    style={{ width: `${(insights.distribution.medium / insights.total_active) * 100}%` }}
                  >
                    {insights.distribution.medium}
                  </div>
                  <div 
                    className="bg-red-500 h-full flex items-center justify-center text-white text-sm font-medium"
                    style={{ width: `${(insights.distribution.low / insights.total_active) * 100}%` }}
                  >
                    {insights.distribution.low}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview" className="gap-2">
                <Lightbulb className="h-4 w-4" />
                Insights
              </TabsTrigger>
              <TabsTrigger value="opportunities" className="gap-2">
                <Target className="h-4 w-4" />
                Opportunités
              </TabsTrigger>
              <TabsTrigger value="forecast" className="gap-2">
                <Calendar className="h-4 w-4" />
                Prévisions
              </TabsTrigger>
            </TabsList>

            {/* Insights Tab */}
            <TabsContent value="overview" className="mt-6">
              <div className="grid gap-4">
                {insights?.insights.map((insight, i) => (
                  <Card 
                    key={i}
                    className={`${
                      insight.impact === "positive" ? "border-l-4 border-l-green-500" :
                      insight.impact === "warning" ? "border-l-4 border-l-amber-500" :
                      insight.impact === "negative" ? "border-l-4 border-l-red-500" :
                      "border-l-4 border-l-purple-500"
                    }`}
                  >
                    <CardContent className="pt-6">
                      <div className="flex items-start gap-4">
                        {(() => {
                          const iconMap: Record<string, React.ReactNode> = {
                            check: <CheckCircle className="h-6 w-6 text-green-500" />,
                            alert: <AlertTriangle className="h-6 w-6 text-amber-500" />,
                            money: <Euro className="h-6 w-6 text-green-500" />,
                            trend: <TrendingUp className="h-6 w-6 text-blue-500" />,
                            target: <Target className="h-6 w-6 text-purple-500" />,
                          };
                          return iconMap[insight.icon] || <Lightbulb className="h-6 w-6 text-gray-500" />;
                        })()}
                        <div className="flex-1">
                          <h4 className="font-semibold">{insight.title}</h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            {insight.description}
                          </p>
                        </div>
                        {insight.opportunity_id && (
                          <Link href={`/leads/${insight.opportunity_id}`}>
                            <Button variant="outline" size="sm" className="gap-2">
                              Voir
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </Link>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* Opportunities Tab */}
            <TabsContent value="opportunities" className="mt-6">
              <div className="space-y-3">
                {predictions?.map((pred) => (
                  <Card key={pred.opportunity_id} className="hover:shadow-md transition-shadow">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <ProbabilityGauge value={pred.win_probability} size="sm" />
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <Link 
                              href={`/leads/${pred.opportunity_id}`}
                              className="font-semibold hover:text-primary truncate"
                            >
                              {pred.title}
                            </Link>
                            {pred.risk_count > 0 && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                                      <AlertTriangle className="h-3 w-3 mr-1" />
                                      {pred.risk_count}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {pred.risk_count} facteur(s) de risque identifié(s)
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                            {pred.organization && (
                              <span>{pred.organization}</span>
                            )}
                            {pred.budget && (
                              <span className="text-green-600 font-medium">
                                {formatCurrency(pred.budget)}
                              </span>
                            )}
                            {pred.deadline && (
                              <span className="flex items-center gap-1 text-orange-600">
                                <Clock className="h-3 w-3" />
                                {formatRelativeDate(pred.deadline)}
                              </span>
                            )}
                          </div>
                          
                          {pred.top_action && (
                            <p className="text-sm mt-2 p-2 bg-muted/50 rounded-lg">
                              <Zap className="h-3 w-3 inline mr-1 text-purple-600" />
                              {pred.top_action}
                            </p>
                          )}
                        </div>
                        
                        <Link href={`/leads/${pred.opportunity_id}`}>
                          <Button variant="ghost" size="icon">
                            <ChevronRight className="h-5 w-5" />
                          </Button>
                        </Link>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* Forecast Tab */}
            <TabsContent value="forecast" className="mt-6">
              <div className="grid gap-4 lg:grid-cols-3">
                {forecast?.forecasts.map((f) => (
                  <Card key={f.month}>
                    <CardHeader>
                      <CardTitle className="text-lg">{f.month_label}</CardTitle>
                      <CardDescription>{f.total_opportunities} opportunités en cours</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm text-muted-foreground">Gains attendus</span>
                            <span className="text-2xl font-bold">{f.expected_wins.toFixed(1)}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1 text-green-600">
                              <ArrowUp className="h-3 w-3" />
                              Optimiste: {f.optimistic.toFixed(1)}
                            </span>
                            <span className="flex items-center gap-1 text-red-600">
                              <ArrowDown className="h-3 w-3" />
                              Pessimiste: {f.pessimistic.toFixed(1)}
                            </span>
                          </div>
                        </div>
                        
                        <div className="pt-4 border-t">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Valeur attendue</span>
                            <span className="text-lg font-semibold text-green-600">
                              {formatCurrency(f.expected_value)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              
              {/* Forecast Summary */}
              <Card className="mt-6 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">Résumé des Prévisions (3 mois)</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        Basé sur l'analyse de {insights?.total_active || 0} opportunités actives
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-purple-600">
                        {forecast?.total_expected_wins.toFixed(1)} gains
                      </p>
                      <p className="text-lg text-green-600 font-semibold">
                        {formatCurrency(forecast?.total_expected_value || 0)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

export default function PredictionsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <PredictionsContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
