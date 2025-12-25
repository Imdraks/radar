"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Sparkles,
  Globe,
  AlertTriangle,
  CheckCircle,
  Loader2,
  ExternalLink,
  Shield,
  ChevronRight,
  RefreshCw,
} from "lucide-react";

import { dossiersApi, DossierDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";

interface DossierPanelProps {
  opportunityId: string;
  opportunityTitle: string;
}

// State badge
function StateBadge({ state }: { state: string }) {
  const config: Record<string, { bg: string; icon: React.ReactNode }> = {
    NOT_CREATED: { bg: "bg-gray-100 text-gray-700", icon: <FileText className="h-3 w-3" /> },
    PROCESSING: { bg: "bg-blue-100 text-blue-700", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
    ENRICHING: { bg: "bg-purple-100 text-purple-700", icon: <Globe className="h-3 w-3" /> },
    MERGING: { bg: "bg-indigo-100 text-indigo-700", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
    READY: { bg: "bg-green-100 text-green-700", icon: <CheckCircle className="h-3 w-3" /> },
    FAILED: { bg: "bg-red-100 text-red-700", icon: <AlertTriangle className="h-3 w-3" /> },
  };

  const c = config[state] || config.NOT_CREATED;

  return (
    <Badge className={`${c.bg} flex items-center gap-1`}>
      {c.icon}
      {state === "READY" ? "Prêt" : state}
    </Badge>
  );
}

// Confidence bar
function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 80 ? "bg-green-500" : value >= 60 ? "bg-yellow-500" : value >= 40 ? "bg-orange-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-medium">{value}%</span>
    </div>
  );
}

export function DossierPanel({ opportunityId, opportunityTitle }: DossierPanelProps) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Try to fetch dossier
  const { data: dossier, isLoading, error } = useQuery({
    queryKey: ["dossier-by-opp", opportunityId],
    queryFn: async () => {
      try {
        return await dossiersApi.getByOpportunity(opportunityId);
      } catch (e: any) {
        if (e?.response?.status === 404) {
          return null;
        }
        throw e;
      }
    },
    retry: false,
  });

  // Build mutation
  const buildMutation = useMutation({
    mutationFn: () => dossiersApi.build(opportunityId, { force_rebuild: false, auto_enrich: true }),
    onSuccess: () => {
      toast.success("Création du dossier lancée");
      queryClient.invalidateQueries({ queryKey: ["dossier-by-opp", opportunityId] });
    },
    onError: () => toast.error("Erreur lors de la création"),
  });

  // Full pipeline mutation
  const pipelineMutation = useMutation({
    mutationFn: () => dossiersApi.fullPipeline(opportunityId, true),
    onSuccess: () => {
      toast.success("Analyse complète lancée");
      queryClient.invalidateQueries({ queryKey: ["dossier-by-opp", opportunityId] });
    },
    onError: () => toast.error("Erreur lors du lancement"),
  });

  // Enrich mutation
  const enrichMutation = useMutation({
    mutationFn: () => dossiersApi.enrich(opportunityId, { auto_merge: true }),
    onSuccess: () => {
      toast.success("Enrichissement web lancé");
      queryClient.invalidateQueries({ queryKey: ["dossier-by-opp", opportunityId] });
    },
    onError: () => toast.error("Erreur lors de l'enrichissement"),
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  // No dossier yet
  if (!dossier) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Dossier
          </CardTitle>
          <CardDescription>
            Analyse automatique avec extraction de données
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            className="w-full"
            onClick={() => buildMutation.mutate()}
            disabled={buildMutation.isPending}
          >
            {buildMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <FileText className="h-4 w-4 mr-2" />
            )}
            Créer le dossier
          </Button>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => pipelineMutation.mutate()}
            disabled={pipelineMutation.isPending}
          >
            {pipelineMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Globe className="h-4 w-4 mr-2" />
            )}
            Analyse complète
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Dossier exists
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            Dossier enrichi
          </CardTitle>
          <StateBadge state={dossier.state} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scores */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Score final</p>
            <p className="text-2xl font-bold">{dossier.score_final}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Confiance</p>
            <ConfidenceBar value={dossier.confidence_plus} />
          </div>
        </div>

        {/* Summary */}
        {dossier.summary_short && (
          <div>
            <p className="text-sm">{dossier.summary_short}</p>
          </div>
        )}

        {/* Quality flags */}
        {dossier.quality_flags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {dossier.quality_flags.slice(0, 3).map((flag) => (
              <Badge
                key={flag}
                variant="outline"
                className="text-xs bg-amber-50 text-amber-700 border-amber-200"
              >
                <AlertTriangle className="h-3 w-3 mr-1" />
                {flag.replace("missing_", "").replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        )}

        {/* Key points preview */}
        {dossier.key_points.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">Points clés</p>
            <ul className="text-sm space-y-1">
              {dossier.key_points.slice(0, 3).map((point, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckCircle className="h-3 w-3 text-green-500 mt-1 shrink-0" />
                  <span className="line-clamp-1">{point}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2 border-t">
          <Button
            variant="default"
            size="sm"
            className="flex-1"
            onClick={() => router.push(`/dossiers/${dossier.id}`)}
          >
            Voir détails
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
          
          {dossier.missing_fields.length > 0 && dossier.state === "READY" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => enrichMutation.mutate()}
              disabled={enrichMutation.isPending}
            >
              {enrichMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Globe className="h-4 w-4" />
              )}
            </Button>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => buildMutation.mutate()}
            disabled={buildMutation.isPending}
            title="Reconstruire"
          >
            {buildMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
