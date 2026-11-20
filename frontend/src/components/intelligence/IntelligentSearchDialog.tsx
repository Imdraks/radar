"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Search, Sparkles, User, DollarSign, Phone, TrendingUp } from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';

interface SearchParams {
  query: string;
  budget_min?: number;
  budget_max?: number;
  region?: string;
  city?: string;
}

interface TaskResult {
  task_id: string;
  status: string;
  ready: boolean;
  result?: {
    query: string;
    status: string;
    opportunities_found: number;
    artists_found: number;
    contacts_found: number;
    prices_found: number;
    summary: {
      total_opportunities: number;
      high_quality_count: number;
      avg_budget?: number;
      artists_found?: Array<{
        name: string;
        fee_range: { min: number; max: number };
        trend: string;
      }>;
    };
  };
  error?: string;
}

export function IntelligentSearchDialog() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [budgetMin, setBudgetMin] = useState<string>("");
  const [budgetMax, setBudgetMax] = useState<string>("");
  const [region, setRegion] = useState("");
  const [city, setCity] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  // Mutation for starting intelligent search
  const searchMutation = useMutation({
    mutationFn: async (params: SearchParams) => {
      const response = await api.post("/ingestion/intelligent-search", params);
      return response.data;
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
      setPolling(true);
    },
  });

  // Query for polling task status
  const { data: taskStatus, isLoading: taskLoading } = useQuery<TaskResult>({
    queryKey: ["task", taskId],
    queryFn: async () => {
      const response = await api.get(`/ingestion/task/${taskId}`);
      return response.data;
    },
    enabled: !!taskId && polling,
    refetchInterval: polling ? 2000 : false,
  });

  // Stop polling when task is complete
  if (taskStatus?.ready && polling) {
    setPolling(false);
  }

  const handleSearch = () => {
    const params: SearchParams = {
      query,
    };
    if (budgetMin) params.budget_min = parseFloat(budgetMin);
    if (budgetMax) params.budget_max = parseFloat(budgetMax);
    if (region) params.region = region;
    if (city) params.city = city;

    searchMutation.mutate(params);
  };

  const handleReset = () => {
    setTaskId(null);
    setPolling(false);
    searchMutation.reset();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Sparkles className="h-4 w-4" />
          Recherche Intelligente
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Recherche Intelligente
          </DialogTitle>
          <DialogDescription>
            Recherche avancée avec extraction de prix, contacts et analyse d'artistes.
          </DialogDescription>
        </DialogHeader>

        {!taskId ? (
          <>
            <div className="space-y-4 py-4">
              {/* Query input */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Recherche</label>
                <Input
                  placeholder="Ex: concert rap Paris, PNL cachet, festival hip-hop..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>

              {/* Budget range */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Budget min (€)</label>
                  <Input
                    type="number"
                    placeholder="5000"
                    value={budgetMin}
                    onChange={(e) => setBudgetMin(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Budget max (€)</label>
                  <Input
                    type="number"
                    placeholder="100000"
                    value={budgetMax}
                    onChange={(e) => setBudgetMax(e.target.value)}
                  />
                </div>
              </div>

              {/* Location */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Région</label>
                  <Input
                    placeholder="Île-de-France"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Ville</label>
                  <Input
                    placeholder="Paris"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                onClick={handleSearch}
                disabled={!query || searchMutation.isPending}
                className="gap-2"
              >
                {searchMutation.isPending ? (
                  <RadarSpinner className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Lancer la recherche
              </Button>
            </DialogFooter>
          </>
        ) : (
          /* Results view */
          <div className="py-4">
            {polling || taskLoading ? (
              <div className="flex flex-col items-center justify-center py-8 space-y-4">
                <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">
                  Analyse en cours... {taskStatus?.status || "PENDING"}
                </p>
              </div>
            ) : taskStatus?.ready ? (
              taskStatus.result ? (
                <div className="space-y-4">
                  {/* Summary */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {taskStatus.result.opportunities_found}
                      </div>
                      <div className="text-sm text-muted-foreground">Opportunités trouvées</div>
                    </div>
                    <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {taskStatus.result.summary.high_quality_count || 0}
                      </div>
                      <div className="text-sm text-muted-foreground">Haute qualité (A/A+)</div>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline" className="gap-1">
                      <Phone className="h-3 w-3" />
                      {taskStatus.result.contacts_found} contacts
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <DollarSign className="h-3 w-3" />
                      {taskStatus.result.prices_found} prix
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <User className="h-3 w-3" />
                      {taskStatus.result.artists_found} artistes
                    </Badge>
                    {taskStatus.result.summary.avg_budget && (
                      <Badge variant="secondary" className="gap-1">
                        Budget moyen: {taskStatus.result.summary.avg_budget.toLocaleString()}€
                      </Badge>
                    )}
                  </div>

                  {/* Artists found */}
                  {taskStatus.result.summary.artists_found && 
                   taskStatus.result.summary.artists_found.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-medium">Artistes analysés</h4>
                      {taskStatus.result.summary.artists_found.map((artist, idx) => (
                        <div key={idx} className="p-3 bg-muted rounded-lg flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">{artist.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">
                              {artist.fee_range.min?.toLocaleString()}€ - {artist.fee_range.max?.toLocaleString()}€
                            </span>
                            <Badge variant={artist.trend === 'rising' ? 'default' : 'secondary'}>
                              <TrendingUp className="h-3 w-3 mr-1" />
                              {artist.trend}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="text-sm text-muted-foreground">
                    Les opportunités ont été ajoutées. Consultez la page Opportunités pour les voir.
                  </p>
                </div>
              ) : taskStatus.error ? (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600">
                  Erreur: {taskStatus.error}
                </div>
              ) : null
            ) : null}

            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={handleReset}>
                Nouvelle recherche
              </Button>
              <Button onClick={() => setOpen(false)}>
                Fermer
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
