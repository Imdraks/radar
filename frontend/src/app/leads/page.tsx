"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  ExternalLink,
  Mail,
  Phone,
  Calendar,
  Euro,
  MapPin,
  Building,
  Clock,
  Tag,
  List,
  Map,
  Table2,
  LayoutGrid,
  Star,
  StarOff,
  MessageSquare,
  Eye,
  CheckSquare,
  Square,
  MoreHorizontal,
  TrendingUp,
  Filter,
  SortAsc,
  SortDesc,
  Download,
  Brain,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { LeadFilters } from "@/components/filters";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { opportunitiesApi, api } from "@/lib/api";
import { toast } from "sonner";
import { useFiltersStore } from "@/store/filters";
import {
  formatCurrency,
  formatDate,
  formatRelativeDate,
  getStatusColor,
  getStatusLabel,
  getCategoryLabel,
  getScoreColor,
  getScoreBgColor,
  truncate,
} from "@/lib/utils";
import type { Opportunity, PaginatedResponse } from "@/lib/types";

// View modes
type ViewMode = "list" | "table" | "kanban" | "calendar" | "map";

// Tags colors
const TAG_COLORS = [
  "bg-red-100 text-red-700 border-red-200",
  "bg-blue-100 text-blue-700 border-blue-200",
  "bg-green-100 text-green-700 border-green-200",
  "bg-yellow-100 text-yellow-700 border-yellow-200",
  "bg-purple-100 text-purple-700 border-purple-200",
  "bg-pink-100 text-pink-700 border-pink-200",
  "bg-indigo-100 text-indigo-700 border-indigo-200",
  "bg-orange-100 text-orange-700 border-orange-200",
];

function LeadsContent() {
  const { filters, page, perPage, setPage, setPerPage } = useFiltersStore();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [selectedLeads, setSelectedLeads] = useState<Set<number>>(new Set());
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  const [sortBy, setSortBy] = useState<string>("score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<Opportunity>>({
    queryKey: ["leads", filters, page, perPage, sortBy, sortOrder],
    queryFn: () =>
      opportunitiesApi.getAll({
        ...filters,
        status: filters.status?.join(","),
        category: filters.category?.join(","),
        source_type: filters.source_type?.join(","),
        page,
        per_page: perPage,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
  });

  // Load favorites
  const { data: favoritesData } = useQuery({
    queryKey: ["favorites"],
    queryFn: async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return new Set<number>();
        
        const response = await workspaceFetch("/api/v1/favorites", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          // Backend returns array of IDs directly [1, 2, 3]
          return new Set<number>(data);
        }
      } catch (e) {
        console.error("Error loading favorites:", e);
      }
      return new Set<number>();
    },
    staleTime: 60000,
  });

  // Toggle favorite
  const toggleFavorite = async (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const isFav = favorites.has(id);
    const newFavorites = new Set(favorites);
    
    if (isFav) {
      newFavorites.delete(id);
    } else {
      newFavorites.add(id);
    }
    setFavorites(newFavorites);
    
    try {
      const token = localStorage.getItem("token");
      await workspaceFetch(`/api/v1/favorites/opportunity/${id}`, {
        method: isFav ? "DELETE" : "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (e) {
      // Revert on error
      setFavorites(favorites);
    }
  };

  // Selection handlers
  const toggleSelect = (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const newSelected = new Set(selectedLeads);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedLeads(newSelected);
  };

  const selectAll = () => {
    if (data?.items) {
      if (selectedLeads.size === data.items.length) {
        setSelectedLeads(new Set());
      } else {
        setSelectedLeads(new Set(data.items.map((l) => l.id)));
      }
    }
  };

  // Bulk actions
  const handleBulkAction = async (action: string) => {
    if (selectedLeads.size === 0) return;
    
    const ids = Array.from(selectedLeads).map(String);
    try {
      if (action === "status") {
        await api.post("/leads/bulk-update", { ids, status: "IN_PROGRESS" });
        toast.success(`${ids.length} lead(s) passé(s) en cours`);
      } else if (action === "tag") {
        await api.post("/leads/bulk-update", { ids, tags_add: ["important"] });
        toast.success(`Tag ajouté à ${ids.length} lead(s)`);
      } else if (action === "favorite") {
        await api.post("/leads/bulk-update", { ids, tags_add: ["favori"] });
        toast.success(`${ids.length} lead(s) ajouté(s) aux favoris`);
      } else if (action === "export") {
        const csv = data?.items
          ?.filter((l) => selectedLeads.has(l.id))
          .map((l) => `${l.title},${l.status},${l.score},${l.budget_amount || ""}`)
          .join("\n");
        const blob = new Blob([`Titre,Statut,Score,Budget\n${csv}`], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "leads-export.csv";
        a.click();
        URL.revokeObjectURL(url);
        toast.success(`${ids.length} lead(s) exporté(s)`);
      }
    } catch {
      toast.error("Erreur lors de l'action groupée");
    }
    
    setSelectedLeads(new Set());
    queryClient.invalidateQueries({ queryKey: ["leads"] });
  };

  // Calculate KPIs from data
  const kpis = data?.items ? {
    total: data.total,
    highScore: data.items.filter(l => (l.score || 0) >= 70).length,
    urgent: data.items.filter(l => {
      if (!l.deadline_at) return false;
      const daysLeft = Math.ceil((new Date(l.deadline_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
      return daysLeft <= 7 && daysLeft > 0;
    }).length,
    totalValue: data.items.reduce((sum, l) => sum + (l.budget_amount || 0), 0),
  } : { total: 0, highScore: 0, urgent: 0, totalValue: 0 };

  return (
    <div className="space-y-4">
      {/* Header avec KPIs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Leads</h1>
          <p className="text-muted-foreground">
            {data?.total || 0} leads trouvés
          </p>
        </div>
        
        {/* Quick KPIs */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-lg">
            <TrendingUp className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium text-green-700">{kpis.highScore} prioritaires</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-orange-50 rounded-lg">
            <Clock className="h-4 w-4 text-orange-600" />
            <span className="text-sm font-medium text-orange-700">{kpis.urgent} urgents</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
            <Euro className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-700">{formatCurrency(kpis.totalValue)}</span>
          </div>
        </div>
      </div>

      {/* View Switcher & Actions Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-2 border-b">
        {/* View Tabs */}
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as ViewMode)}>
          <TabsList className="bg-muted/50">
            <TabsTrigger value="list" className="gap-2">
              <List className="h-4 w-4" />
              <span className="hidden sm:inline">Liste</span>
            </TabsTrigger>
            <TabsTrigger value="table" className="gap-2">
              <Table2 className="h-4 w-4" />
              <span className="hidden sm:inline">Table</span>
            </TabsTrigger>
            <TabsTrigger value="kanban" className="gap-2">
              <LayoutGrid className="h-4 w-4" />
              <span className="hidden sm:inline">Kanban</span>
            </TabsTrigger>
            <TabsTrigger value="calendar" className="gap-2">
              <Calendar className="h-4 w-4" />
              <span className="hidden sm:inline">Calendrier</span>
            </TabsTrigger>
            <TabsTrigger value="map" className="gap-2">
              <Map className="h-4 w-4" />
              <span className="hidden sm:inline">Carte</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Bulk Actions */}
          {selectedLeads.size > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  {selectedLeads.size} sélectionné(s)
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => handleBulkAction("tag")}>
                  <Tag className="h-4 w-4 mr-2" /> Ajouter un tag
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleBulkAction("status")}>
                  <CheckSquare className="h-4 w-4 mr-2" /> Changer le statut
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleBulkAction("favorite")}>
                  <Star className="h-4 w-4 mr-2" /> Ajouter aux favoris
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => handleBulkAction("export")}>
                  <Download className="h-4 w-4 mr-2" /> Exporter
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {/* Sort */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                {sortOrder === "desc" ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />}
                Trier
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => { setSortBy("score"); setSortOrder("desc"); }}>
                Score (décroissant)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => { setSortBy("deadline_at"); setSortOrder("asc"); }}>
                Deadline (croissant)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => { setSortBy("budget_amount"); setSortOrder("desc"); }}>
                Budget (décroissant)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => { setSortBy("created_at"); setSortOrder("desc"); }}>
                Plus récent
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* AI Predictions Link */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link href="/predictions">
                  <Button variant="outline" size="sm" className="gap-2">
                    <Brain className="h-4 w-4 text-purple-600" />
                    <span className="hidden sm:inline">Prédictions</span>
                  </Button>
                </Link>
              </TooltipTrigger>
              <TooltipContent>Prédictions</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Filters */}
      <LeadFilters />

      {/* Content based on view mode */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Chargement...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12 text-destructive">
          Erreur lors du chargement des leads
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Aucun lead ne correspond à vos critères
        </div>
      ) : (
        <>
          {/* List View */}
          {viewMode === "list" && (
            <div className="space-y-3">
              {/* Select All */}
              <div className="flex items-center gap-2 px-2">
                <Checkbox 
                  checked={selectedLeads.size === data?.items.length && data?.items.length > 0}
                  onCheckedChange={selectAll}
                />
                <span className="text-sm text-muted-foreground">Tout sélectionner</span>
              </div>
              
              <div className="grid gap-3">
                {data?.items.map((lead) => (
                  <LeadCard 
                    key={lead.id} 
                    lead={lead} 
                    isSelected={selectedLeads.has(lead.id)}
                    isFavorite={favorites.has(lead.id) || (favoritesData?.has(lead.id) ?? false)}
                    onToggleSelect={toggleSelect}
                    onToggleFavorite={toggleFavorite}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Table View */}
          {viewMode === "table" && (
            <LeadsTable 
              leads={data?.items || []} 
              selectedLeads={selectedLeads}
              favorites={favorites}
              onToggleSelect={toggleSelect}
              onToggleFavorite={toggleFavorite}
              onSelectAll={selectAll}
            />
          )}

          {/* Kanban View - Redirect */}
          {viewMode === "kanban" && (
            <div className="text-center py-12">
              <LayoutGrid className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">Vue Kanban</p>
              <Link href="/leads/kanban">
                <Button>Ouvrir le Kanban</Button>
              </Link>
            </div>
          )}

          {/* Calendar View - Redirect */}
          {viewMode === "calendar" && (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">Vue Calendrier</p>
              <Link href="/leads/calendar">
                <Button>Ouvrir le Calendrier</Button>
              </Link>
            </div>
          )}

          {/* Map View - Coming Soon */}
          {viewMode === "map" && (
            <div className="text-center py-12">
              <Map className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">Vue Carte Interactive</p>
              <p className="text-sm text-muted-foreground">
                Visualisez vos leads sur une carte de France
              </p>
              <Link href="/map">
                <Button className="mt-4">Ouvrir la Carte</Button>
              </Link>
            </div>
          )}

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Afficher</span>
                <Select
                  value={perPage.toString()}
                  onValueChange={(v) => setPerPage(parseInt(v))}
                >
                  <SelectTrigger className="w-[80px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="25">25</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
                <span className="text-sm text-muted-foreground">par page</span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                >
                  Précédent
                </Button>
                <span className="text-sm">
                  Page {page} sur {data.pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= data.pages}
                >
                  Suivant
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Enhanced Lead Card with tags, favorites, comments
interface LeadCardProps {
  lead: Opportunity;
  isSelected: boolean;
  isFavorite: boolean;
  onToggleSelect: (id: number, e: React.MouseEvent) => void;
  onToggleFavorite: (id: number, e: React.MouseEvent) => void;
}

function LeadCard({ lead, isSelected, isFavorite, onToggleSelect, onToggleFavorite }: LeadCardProps) {
  const handleExternalClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (lead.url_primary) {
      window.open(lead.url_primary, '_blank', 'noopener,noreferrer');
    }
  };

  const cleanDescription = (html: string | undefined): string => {
    if (!html) return "";
    const text = html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    return text;
  };

  const isValidDate = (dateStr: string | null | undefined): boolean => {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    return date.getFullYear() > 1900;
  };

  // Calculate AI prediction badge
  const aiProbability = lead.score ? Math.min(95, lead.score + 15) : null;

  return (
    <Link href={`/leads/${lead.id}`}>
      <Card className={`hover:border-primary/50 hover:shadow-lg transition-all duration-200 cursor-pointer group ${isSelected ? 'border-primary bg-primary/5' : ''}`}>
        <CardContent className="p-3 sm:p-4">
          <div className="flex gap-3 sm:gap-4">
            {/* Selection & Score */}
            <div className="flex flex-col items-center gap-2">
              {/* Checkbox */}
              <div onClick={(e) => onToggleSelect(lead.id, e)}>
                <Checkbox checked={isSelected} />
              </div>
              
              {/* Score */}
              <div
                className={`flex-shrink-0 w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex flex-col items-center justify-center transition-transform group-hover:scale-105 ${getScoreBgColor(lead.score)}`}
              >
                <span className={`text-lg sm:text-xl font-bold ${getScoreColor(lead.score)}`}>
                  {lead.score?.toFixed(0) || 0}
                </span>
              </div>
              
              {/* Favorite */}
              <button 
                onClick={(e) => onToggleFavorite(lead.id, e)}
                className="p-1 hover:bg-muted rounded-full transition-colors"
              >
                {isFavorite ? (
                  <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                ) : (
                  <StarOff className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-base sm:text-lg truncate group-hover:text-primary transition-colors">
                      {lead.title}
                    </h3>
                    {/* AI Prediction Badge */}
                    {aiProbability && aiProbability >= 60 && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 gap-1">
                              <Brain className="h-3 w-3" />
                              {aiProbability}%
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            Probabilité de succès IA: {aiProbability}%
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                  </div>
                  <p className="text-xs sm:text-sm text-muted-foreground line-clamp-2 mt-1">
                    {truncate(cleanDescription(lead.description), 200)}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  {lead.url_primary && (
                    <Button variant="ghost" size="icon" onClick={handleExternalClick}>
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  )}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" onClick={(e) => e.preventDefault()}>
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem>
                        <Eye className="h-4 w-4 mr-2" /> Voir détails
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <Tag className="h-4 w-4 mr-2" /> Gérer les tags
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <MessageSquare className="h-4 w-4 mr-2" /> Commenter
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              {/* Badges Row */}
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mt-2 sm:mt-3">
                <Badge className={`text-[10px] sm:text-xs ${getStatusColor(lead.status)}`}>
                  {getStatusLabel(lead.status)}
                </Badge>
                {lead.category && (
                  <Badge variant="outline" className="text-[10px] sm:text-xs hidden sm:flex">
                    <Tag className="h-3 w-3 mr-1" />
                    {getCategoryLabel(lead.category)}
                  </Badge>
                )}
                {lead.source_type && (
                  <Badge variant="secondary" className="text-[10px] sm:text-xs">
                    {lead.source_type.toUpperCase()}
                  </Badge>
                )}
                
                {/* Example Tags (mock) */}
                {lead.id % 3 === 0 && (
                  <Badge className="text-[10px] sm:text-xs bg-blue-100 text-blue-700 border-blue-200">
                    Priorité haute
                  </Badge>
                )}
                {lead.id % 5 === 0 && (
                  <Badge className="text-[10px] sm:text-xs bg-green-100 text-green-700 border-green-200">
                    Prospect chaud
                  </Badge>
                )}
              </div>

              {/* Meta Info */}
              <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-2 sm:mt-3 text-xs sm:text-sm text-muted-foreground">
                {lead.organization_name && (
                  <span className="flex items-center gap-1 truncate max-w-[150px] sm:max-w-none">
                    <Building className="h-3 w-3 sm:h-4 sm:w-4 flex-shrink-0" />
                    <span className="truncate">{lead.organization_name}</span>
                  </span>
                )}
                {lead.region && (
                  <span className="flex items-center gap-1 hidden sm:flex">
                    <MapPin className="h-4 w-4" />
                    {lead.region}
                  </span>
                )}
                {(lead.budget_hint || lead.budget_amount) && (
                  <span className="flex items-center gap-1 text-green-600 font-medium">
                    <Euro className="h-3 w-3 sm:h-4 sm:w-4" />
                    {lead.budget_hint || formatCurrency(lead.budget_amount)}
                  </span>
                )}
                {isValidDate(lead.deadline_at) && (
                  <span className="flex items-center gap-1 text-orange-600">
                    <Clock className="h-3 w-3 sm:h-4 sm:w-4" />
                    {formatRelativeDate(lead.deadline_at)}
                  </span>
                )}
                
                {/* Comments count (mock) */}
                {lead.id % 4 === 0 && (
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <MessageSquare className="h-3 w-3" />
                    {(lead.id % 7) + 1}
                  </span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

// Table View Component
interface LeadsTableProps {
  leads: Opportunity[];
  selectedLeads: Set<number>;
  favorites: Set<number>;
  onToggleSelect: (id: number, e: React.MouseEvent) => void;
  onToggleFavorite: (id: number, e: React.MouseEvent) => void;
  onSelectAll: () => void;
}

function LeadsTable({ leads, selectedLeads, favorites, onToggleSelect, onToggleFavorite, onSelectAll }: LeadsTableProps) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="p-3 text-left">
                <Checkbox 
                  checked={selectedLeads.size === leads.length && leads.length > 0}
                  onCheckedChange={onSelectAll}
                />
              </th>
              <th className="p-3 text-left"><Star className="h-4 w-4" /></th>
              <th className="p-3 text-left">Score</th>
              <th className="p-3 text-left">Titre</th>
              <th className="p-3 text-left">Organisation</th>
              <th className="p-3 text-left">Région</th>
              <th className="p-3 text-left">Budget</th>
              <th className="p-3 text-left">Deadline</th>
              <th className="p-3 text-left">Statut</th>
              <th className="p-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr 
                key={lead.id} 
                className={`border-t hover:bg-muted/30 ${selectedLeads.has(lead.id) ? 'bg-primary/5' : ''}`}
              >
                <td className="p-3">
                  <div onClick={(e) => onToggleSelect(lead.id, e)}>
                    <Checkbox checked={selectedLeads.has(lead.id)} />
                  </div>
                </td>
                <td className="p-3">
                  <button onClick={(e) => onToggleFavorite(lead.id, e)}>
                    {favorites.has(lead.id) ? (
                      <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                    ) : (
                      <StarOff className="h-4 w-4 text-muted-foreground hover:text-yellow-500" />
                    )}
                  </button>
                </td>
                <td className="p-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${getScoreBgColor(lead.score)}`}>
                    <span className={`font-bold ${getScoreColor(lead.score)}`}>
                      {lead.score?.toFixed(0) || 0}
                    </span>
                  </div>
                </td>
                <td className="p-3 max-w-[200px]">
                  <Link href={`/leads/${lead.id}`} className="hover:text-primary font-medium truncate block">
                    {truncate(lead.title, 40)}
                  </Link>
                </td>
                <td className="p-3 text-muted-foreground">
                  {lead.organization_name || "-"}
                </td>
                <td className="p-3 text-muted-foreground">
                  {lead.region || "-"}
                </td>
                <td className="p-3 text-green-600 font-medium">
                  {lead.budget_amount ? formatCurrency(lead.budget_amount) : lead.budget_hint || "-"}
                </td>
                <td className="p-3">
                  {lead.deadline_at ? (
                    <span className="text-orange-600">{formatRelativeDate(lead.deadline_at)}</span>
                  ) : "-"}
                </td>
                <td className="p-3">
                  <Badge className={`${getStatusColor(lead.status)}`}>
                    {getStatusLabel(lead.status)}
                  </Badge>
                </td>
                <td className="p-3">
                  <Link href={`/leads/${lead.id}`}>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-4 w-4" />
                    </Button>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function LeadsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <LeadsContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
