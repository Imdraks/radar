"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
  Loader2,
  ChevronRight,
  Sparkles,
  Globe,
  Shield,
  BarChart3,
} from "lucide-react";

import { dossiersApi, DossierSummary, DossierStats } from "@/lib/api";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

// State badge component
function StateBadge({ state }: { state: string }) {
  const variants: Record<string, { color: string; icon: React.ReactNode }> = {
    NOT_CREATED: { color: "bg-gray-100 text-gray-700", icon: <FileText className="h-3 w-3" /> },
    PROCESSING: { color: "bg-blue-100 text-blue-700", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
    ENRICHING: { color: "bg-purple-100 text-purple-700", icon: <Globe className="h-3 w-3 animate-pulse" /> },
    MERGING: { color: "bg-indigo-100 text-indigo-700", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
    READY: { color: "bg-green-100 text-green-700", icon: <CheckCircle className="h-3 w-3" /> },
    FAILED: { color: "bg-red-100 text-red-700", icon: <XCircle className="h-3 w-3" /> },
  };

  const variant = variants[state] || variants.NOT_CREATED;

  return (
    <Badge className={`${variant.color} flex items-center gap-1`}>
      {variant.icon}
      {state}
    </Badge>
  );
}

// Confidence indicator
function ConfidenceBar({ value }: { value: number }) {
  const getColor = () => {
    if (value >= 80) return "bg-green-500";
    if (value >= 60) return "bg-yellow-500";
    if (value >= 40) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground">{value}%</span>
    </div>
  );
}

// Stats cards
function StatsCards({ stats }: { stats: DossierStats | undefined }) {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{stats.total}</p>
            </div>
            <FileText className="h-8 w-8 text-muted-foreground/30" />
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Prêts</p>
              <p className="text-2xl font-bold text-green-600">{stats.ready}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-500/30" />
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">En traitement</p>
              <p className="text-2xl font-bold text-blue-600">{stats.processing}</p>
            </div>
            <Clock className="h-8 w-8 text-blue-500/30" />
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Confiance moy.</p>
              <p className="text-2xl font-bold">{stats.average_confidence}%</p>
            </div>
            <BarChart3 className="h-8 w-8 text-muted-foreground/30" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Dossier card
function DossierCard({ dossier, onClick }: { dossier: DossierSummary; onClick: () => void }) {
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      <CardContent className="pt-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm truncate pr-2">
              {dossier.opportunity_title}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Mis à jour: {new Date(dossier.updated_at).toLocaleDateString("fr-FR")}
            </p>
          </div>
          <StateBadge state={dossier.state} />
        </div>

        {dossier.summary_short && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
            {dossier.summary_short}
          </p>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Score</p>
              <p className="font-bold text-lg">{dossier.score_final}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Confiance</p>
              <ConfidenceBar value={dossier.confidence_plus} />
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground" />
        </div>

        {/* Quality flags */}
        {dossier.quality_flags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t">
            {dossier.quality_flags.slice(0, 3).map((flag) => (
              <Badge
                key={flag}
                variant="outline"
                className="text-xs bg-amber-50 text-amber-700 border-amber-200"
              >
                <AlertTriangle className="h-3 w-3 mr-1" />
                {flag.replace("missing_", "").replace("_", " ")}
              </Badge>
            ))}
            {dossier.quality_flags.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{dossier.quality_flags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DossiersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  
  // Filters
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [minConfidence, setMinConfidence] = useState<string>("all");
  const [hasMissing, setHasMissing] = useState<string>("all");

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ["dossier-stats"],
    queryFn: () => dossiersApi.getStats(),
  });

  // Fetch dossiers
  const { data: dossiers, isLoading, refetch } = useQuery({
    queryKey: ["dossiers", search, stateFilter, minConfidence, hasMissing],
    queryFn: () =>
      dossiersApi.list({
        q: search || undefined,
        state: stateFilter !== "all" ? stateFilter : undefined,
        min_confidence: minConfidence !== "all" ? parseInt(minConfidence) : undefined,
        has_missing_fields: hasMissing === "yes" ? true : hasMissing === "no" ? false : undefined,
        limit: 50,
      }),
  });

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (debouncedSearch !== search) {
      refetch();
    }
  }, [debouncedSearch, refetch, search]);

  const handleDossierClick = (dossier: DossierSummary) => {
    router.push(`/dossiers/${dossier.id}`);
  };

  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="container mx-auto py-6 px-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <FileText className="h-6 w-6" />
                Dossiers
              </h1>
              <p className="text-muted-foreground">
                Opportunités analysées avec sources vérifiées
              </p>
            </div>
            <Button onClick={() => refetch()} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Actualiser
            </Button>
          </div>

          {/* Stats */}
          <StatsCards stats={stats} />

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Rechercher..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            <Select value={stateFilter} onValueChange={setStateFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="État" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les états</SelectItem>
                <SelectItem value="READY">Prêt</SelectItem>
                <SelectItem value="PROCESSING">En traitement</SelectItem>
                <SelectItem value="ENRICHING">Enrichissement</SelectItem>
                <SelectItem value="FAILED">Échec</SelectItem>
              </SelectContent>
            </Select>

            <Select value={minConfidence} onValueChange={setMinConfidence}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Confiance min" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toute confiance</SelectItem>
                <SelectItem value="80">≥ 80%</SelectItem>
                <SelectItem value="60">≥ 60%</SelectItem>
                <SelectItem value="40">≥ 40%</SelectItem>
              </SelectContent>
            </Select>

            <Select value={hasMissing} onValueChange={setHasMissing}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Champs manquants" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="yes">Avec manquants</SelectItem>
                <SelectItem value="no">Complets</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Dossiers grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : dossiers && dossiers.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dossiers.map((dossier) => (
            <DossierCard
              key={dossier.id}
              dossier={dossier}
              onClick={() => handleDossierClick(dossier)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <h3 className="font-medium mb-2">Aucun dossier</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Les dossiers sont créés à partir des opportunités enrichies par GPT.
            </p>
            <Button onClick={() => router.push("/opportunities")}>
              Voir les opportunités
            </Button>
          </CardContent>
        </Card>
      )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
