"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import {
  Brain,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Target,
  Calendar,
  Lightbulb,
  BarChart2,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';

interface PredictionResult {
  opportunity_id: string;
  success_probability: number;
  confidence_level: number;
  predicted_outcome: "won" | "lost" | "undetermined";
  key_factors: {
    name: string;
    value: any;
    weight: number;
    impact: number;
    description: string;
  }[];
  recommendations: string[];
  risk_assessment: "low" | "medium" | "high";
  estimated_decision_date?: string;
}

interface OpportunityPredictionProps {
  opportunityId: number;
  opportunityTitle: string;
}

export function OpportunityPrediction({
  opportunityId,
  opportunityTitle,
}: OpportunityPredictionProps) {
  const [isOpen, setIsOpen] = useState(false);

  const { data: prediction, isLoading, refetch } = useQuery({
    queryKey: ["prediction", opportunityId],
    queryFn: async () => {
      const response = await api.get(`/predictions/${opportunityId}`);
      return response.data as PredictionResult;
    },
    enabled: isOpen,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const getProbabilityColor = (prob: number) => {
    if (prob >= 0.6) return "text-green-600 dark:text-green-400";
    if (prob >= 0.4) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getProbabilityBg = (prob: number) => {
    if (prob >= 0.6) return "bg-green-100 dark:bg-green-900/30";
    if (prob >= 0.4) return "bg-yellow-100 dark:bg-yellow-900/30";
    return "bg-red-100 dark:bg-red-900/30";
  };

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case "low":
        return <Badge className="bg-green-500">Risque faible</Badge>;
      case "medium":
        return <Badge className="bg-yellow-500">Risque modéré</Badge>;
      case "high":
        return <Badge className="bg-red-500">Risque élevé</Badge>;
      default:
        return null;
    }
  };

  const getOutcomeIcon = (outcome: string) => {
    switch (outcome) {
      case "won":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "lost":
        return <TrendingDown className="h-5 w-5 text-red-500" />;
      default:
        return <HelpCircle className="h-5 w-5 text-yellow-500" />;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Brain className="h-4 w-4 mr-2" />
          Prédiction IA
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            Analyse - {opportunityTitle}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <RadarSpinner className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">Analyse en cours...</p>
          </div>
        ) : prediction ? (
          <div className="space-y-6">
            {/* Main probability card */}
            <Card className={getProbabilityBg(prediction.success_probability)}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {getOutcomeIcon(prediction.predicted_outcome)}
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Probabilité de succès
                      </p>
                      <p
                        className={`text-4xl font-bold ${getProbabilityColor(
                          prediction.success_probability
                        )}`}
                      >
                        {Math.round(prediction.success_probability * 100)}%
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {getRiskBadge(prediction.risk_assessment)}
                    <p className="text-sm text-muted-foreground mt-2">
                      Confiance: {Math.round(prediction.confidence_level * 100)}%
                    </p>
                  </div>
                </div>

                {prediction.estimated_decision_date && (
                  <div className="mt-4 pt-4 border-t flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>
                      Décision estimée:{" "}
                      {new Date(prediction.estimated_decision_date).toLocaleDateString("fr-FR", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Key factors */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart2 className="h-4 w-4" />
                  Facteurs clés
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {prediction.key_factors.map((factor) => (
                  <div key={factor.name} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="cursor-help">
                            {getFactorLabel(factor.name)}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{factor.description}</p>
                        </TooltipContent>
                      </Tooltip>
                      <span className="text-muted-foreground">
                        Impact: {Math.round(factor.impact * 100)}%
                      </span>
                    </div>
                    <Progress
                      value={factor.impact * 100 / 0.25} // Normalize to max weight
                      className="h-2"
                    />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  Recommandations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {prediction.recommendations.map((rec, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Target className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Refresh button */}
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
              >
                <Brain className="h-4 w-4 mr-2" />
                Réanalyser
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Impossible de générer la prédiction</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function getFactorLabel(name: string): string {
  const labels: Record<string, string> = {
    score: "Score opportunité",
    budget_fit: "Adéquation budget",
    deadline_timing: "Timing deadline",
    source_reliability: "Fiabilité source",
    domain_match: "Correspondance domaine",
    competition_level: "Niveau concurrence",
  };
  return labels[name] || name;
}

// Trend Analysis Component
export function TrendAnalysis() {
  const { data: trends, isLoading } = useQuery({
    queryKey: ["trends"],
    queryFn: async () => {
      const response = await api.get("/predictions/trends/analysis?period_days=30");
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (!trends) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Analyse des tendances (30 jours)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-muted rounded-lg">
            <p className="text-2xl font-bold">{trends.total_opportunities}</p>
            <p className="text-sm text-muted-foreground">Total</p>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <p className="text-2xl font-bold">{trends.average_score}/10</p>
            <p className="text-sm text-muted-foreground">Score moyen</p>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <p className="text-2xl font-bold">{trends.growth_rate}/jour</p>
            <p className="text-sm text-muted-foreground">Rythme</p>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <p className="text-2xl font-bold text-green-600">
              {trends.predicted_next_period}
            </p>
            <p className="text-sm text-muted-foreground">Prévu prochain mois</p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-2">
          <div className="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <p className="font-semibold text-red-600">{trends.score_distribution.low}</p>
            <p className="text-xs text-muted-foreground">Score faible</p>
          </div>
          <div className="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
            <p className="font-semibold text-yellow-600">{trends.score_distribution.medium}</p>
            <p className="text-xs text-muted-foreground">Score moyen</p>
          </div>
          <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <p className="font-semibold text-green-600">{trends.score_distribution.high}</p>
            <p className="text-xs text-muted-foreground">Score élevé</p>
          </div>
        </div>

        {trends.recommendations && trends.recommendations.length > 0 && (
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <p className="font-medium mb-2 flex items-center gap-2">
              <Lightbulb className="h-4 w-4" />
              Recommandations
            </p>
            <ul className="text-sm space-y-1">
              {trends.recommendations.map((rec: string, i: number) => (
                <li key={i}>• {rec}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
