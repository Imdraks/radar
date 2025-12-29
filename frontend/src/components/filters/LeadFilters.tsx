"use client";

import { useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X, Filter } from "lucide-react";
import { useFiltersStore, OpportunityFilters as FiltersType } from "@/store/filters";
import { opportunitiesApi } from "@/lib/api";
import { BudgetFilter } from "./BudgetFilter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

const STATUS_OPTIONS = [
  { value: "new", label: "Nouveau" },
  { value: "to_qualify", label: "À qualifier" },
  { value: "qualified", label: "Qualifié" },
  { value: "in_progress", label: "En cours" },
  { value: "submitted", label: "Soumis" },
  { value: "won", label: "Gagné" },
  { value: "lost", label: "Perdu" },
  { value: "archived", label: "Archivé" },
];

const CATEGORY_OPTIONS = [
  { value: "appel_offres", label: "Appel d'offres" },
  { value: "partenariat", label: "Partenariat" },
  { value: "sponsoring", label: "Sponsoring" },
  { value: "privatisation", label: "Privatisation" },
  { value: "production", label: "Production" },
  { value: "prestation", label: "Prestation" },
  { value: "autre", label: "Autre" },
];

const SOURCE_TYPE_OPTIONS = [
  { value: "email", label: "Email" },
  { value: "rss", label: "RSS" },
  { value: "html", label: "HTML" },
  { value: "api", label: "API" },
];

const REGION_OPTIONS = [
  "Île-de-France",
  "Auvergne-Rhône-Alpes",
  "Nouvelle-Aquitaine",
  "Occitanie",
  "Provence-Alpes-Côte d'Azur",
  "Hauts-de-France",
  "Grand Est",
  "Bretagne",
  "Pays de la Loire",
  "Normandie",
  "Bourgogne-Franche-Comté",
  "Centre-Val de Loire",
  "Corse",
  "National",
];

export function LeadFilters() {
  const { filters, setFilters, resetFilters } = useFiltersStore();

  // Fetch budget stats for histogram
  const { data: budgetStats } = useQuery({
    queryKey: ["budgetStats"],
    queryFn: () => opportunitiesApi.getBudgetStats(),
    staleTime: 60000,
  });

  // Calculate active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.status?.length) count++;
    if (filters.category?.length) count++;
    if (filters.source_type?.length) count++;
    if (filters.region) count++;
    if (filters.budget_min !== undefined || filters.budget_max !== undefined) count++;
    if (filters.score_min !== undefined) count++;
    return count;
  }, [filters]);

  // Handle search input
  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setFilters({ search: e.target.value || undefined });
    },
    [setFilters]
  );

  // Handle status change
  const handleStatusChange = useCallback(
    (status: string) => {
      const currentStatuses = filters.status || [];
      const newStatuses = currentStatuses.includes(status)
        ? currentStatuses.filter((s) => s !== status)
        : [...currentStatuses, status];
      setFilters({ status: newStatuses.length ? newStatuses : undefined });
    },
    [filters.status, setFilters]
  );

  // Handle category change
  const handleCategoryChange = useCallback(
    (category: string) => {
      const currentCategories = filters.category || [];
      const newCategories = currentCategories.includes(category)
        ? currentCategories.filter((c) => c !== category)
        : [...currentCategories, category];
      setFilters({ category: newCategories.length ? newCategories : undefined });
    },
    [filters.category, setFilters]
  );

  // Handle budget range change
  const handleBudgetChange = useCallback(
    (value: [number, number]) => {
      setFilters({
        budget_min: value[0],
        budget_max: value[1],
      });
    },
    [setFilters]
  );

  // Handle region change
  const handleRegionChange = useCallback(
    (region: string) => {
      setFilters({ region: region === "all" ? undefined : region });
    },
    [setFilters]
  );

  // Handle sort change
  const handleSortChange = useCallback(
    (value: string) => {
      const [sort_by, sort_order] = value.split("-");
      setFilters({ sort_by, sort_order: sort_order as "asc" | "desc" });
    },
    [setFilters]
  );

  return (
    <div className="space-y-4">
      {/* Search and Quick Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher..."
            value={filters.search || ""}
            onChange={handleSearchChange}
            className="pl-9"
          />
        </div>

        {/* Sort */}
        <Select
          value={`${filters.sort_by || "score"}-${filters.sort_order || "desc"}`}
          onValueChange={handleSortChange}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Trier par..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="score-desc">Score (décroissant)</SelectItem>
            <SelectItem value="score-asc">Score (croissant)</SelectItem>
            <SelectItem value="deadline_at-asc">Deadline (proche)</SelectItem>
            <SelectItem value="deadline_at-desc">Deadline (loin)</SelectItem>
            <SelectItem value="ingested_at-desc">Plus récent</SelectItem>
            <SelectItem value="ingested_at-asc">Plus ancien</SelectItem>
            <SelectItem value="budget_amount-desc">Budget (décroissant)</SelectItem>
            <SelectItem value="budget_amount-asc">Budget (croissant)</SelectItem>
          </SelectContent>
        </Select>

        {/* Filter Dialog */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="relative">
              <Filter className="h-4 w-4 mr-2" />
              Filtres
              {activeFilterCount > 0 && (
                <Badge
                  variant="default"
                  className="absolute -top-2 -right-2 h-5 w-5 p-0 flex items-center justify-center text-xs"
                >
                  {activeFilterCount}
                </Badge>
              )}
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Filtres avancés</DialogTitle>
            </DialogHeader>
            
            <div className="space-y-6 py-4">
              {/* Status */}
              <div className="space-y-2">
                <Label>Statut</Label>
                <div className="flex flex-wrap gap-2">
                  {STATUS_OPTIONS.map((option) => (
                    <Badge
                      key={option.value}
                      variant={filters.status?.includes(option.value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => handleStatusChange(option.value)}
                    >
                      {option.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Category */}
              <div className="space-y-2">
                <Label>Catégorie</Label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORY_OPTIONS.map((option) => (
                    <Badge
                      key={option.value}
                      variant={filters.category?.includes(option.value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => handleCategoryChange(option.value)}
                    >
                      {option.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Source Type */}
              <div className="space-y-2">
                <Label>Source</Label>
                <div className="flex flex-wrap gap-2">
                  {SOURCE_TYPE_OPTIONS.map((option) => (
                    <Badge
                      key={option.value}
                      variant={filters.source_type?.includes(option.value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => {
                        const current = filters.source_type || [];
                        const newTypes = current.includes(option.value)
                          ? current.filter((t) => t !== option.value)
                          : [...current, option.value];
                        setFilters({ source_type: newTypes.length ? newTypes : undefined });
                      }}
                    >
                      {option.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Region */}
              <div className="space-y-2">
                <Label>Région</Label>
                <Select value={filters.region || "all"} onValueChange={handleRegionChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Toutes les régions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Toutes les régions</SelectItem>
                    {REGION_OPTIONS.map((region) => (
                      <SelectItem key={region} value={region}>
                        {region}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Budget Filter with Histogram */}
              {budgetStats && budgetStats.histogram?.length > 0 && (
                <BudgetFilter
                  min={budgetStats.min}
                  max={budgetStats.max}
                  histogram={budgetStats.histogram}
                  value={[
                    filters.budget_min ?? budgetStats.min,
                    filters.budget_max ?? budgetStats.max,
                  ]}
                  onChange={handleBudgetChange}
                />
              )}

              {/* Score minimum */}
              <div className="space-y-2">
                <Label>Score minimum</Label>
                <Input
                  type="number"
                  min={0}
                  value={filters.score_min ?? ""}
                  onChange={(e) =>
                    setFilters({
                      score_min: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                  placeholder="Ex: 5"
                />
              </div>
            </div>

            {/* Reset button */}
            <div className="flex justify-end">
              <Button variant="ghost" onClick={resetFilters}>
                <X className="h-4 w-4 mr-2" />
                Réinitialiser les filtres
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Reset button (visible when filters active) */}
        {activeFilterCount > 0 && (
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            <X className="h-4 w-4 mr-1" />
            Effacer ({activeFilterCount})
          </Button>
        )}
      </div>

      {/* Active filters display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.status?.map((status) => (
            <Badge key={status} variant="secondary" className="gap-1">
              {STATUS_OPTIONS.find((s) => s.value === status)?.label}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => handleStatusChange(status)}
              />
            </Badge>
          ))}
          {filters.category?.map((category) => (
            <Badge key={category} variant="secondary" className="gap-1">
              {CATEGORY_OPTIONS.find((c) => c.value === category)?.label}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => handleCategoryChange(category)}
              />
            </Badge>
          ))}
          {filters.region && (
            <Badge variant="secondary" className="gap-1">
              {filters.region}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => setFilters({ region: undefined })}
              />
            </Badge>
          )}
          {(filters.budget_min !== undefined || filters.budget_max !== undefined) && (
            <Badge variant="secondary" className="gap-1">
              Budget: {filters.budget_min ?? 0}€ - {filters.budget_max ?? "∞"}€
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => setFilters({ budget_min: undefined, budget_max: undefined })}
              />
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

export default OpportunityFilters;
