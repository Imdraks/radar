"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitCompare,
  Plus,
  Trash2,
  MoreHorizontal,
  Edit,
  RefreshCw,
  ChevronDown,
  Star,
  Users,
  TrendingUp,
  Clock,
  DollarSign,
  Check,
  X,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Search,
  ArrowRight,
  Sparkles,
  BarChart3,
  Scale,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Image from "next/image";

// ============================================================================
// TYPES
// ============================================================================

interface ComparisonList {
  id: number;
  name: string;
  artist_count: number;
  created_at: string;
  updated_at: string;
}

interface ArtistComparisonData {
  id: number;
  name: string;
  image_url?: string;
  score: number;
  timing_bucket?: string;
  timing_label?: string;
  recommendation?: string;
  monthly_listeners?: number;
  followers?: number;
  velocity?: number;
  acceleration?: number;
  data_quality?: string;
  country?: string;
  city?: string;
  genres: string[];
  drivers: { label: string; value?: string; impact?: number }[];
  risks: { label: string; value?: string; impact?: number }[];
  signals: string[];
  patterns: string[];
  booking_range?: { min: number; max: number; optimal: number };
  has_spotify: boolean;
  has_viberate: boolean;
  last_enriched_at?: string;
}

interface ComparisonListDetail {
  id: number;
  name: string;
  artists: ArtistComparisonData[];
  created_at: string;
  updated_at: string;
}

interface ArtistSearchResult {
  id: number;
  name: string;
  image_url?: string;
  score: number;
  monthly_listeners?: number;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

const fetchLists = async (): Promise<ComparisonList[]> => {
  const response = await api.get("/comparison/lists");
  return response.data;
};

const fetchListDetail = async (listId: number): Promise<ComparisonListDetail> => {
  const response = await api.get(`/comparison/lists/${listId}`);
  return response.data;
};

const createList = async (name: string): Promise<ComparisonList> => {
  const response = await api.post("/comparison/lists", { name });
  return response.data;
};

const deleteList = async (listId: number): Promise<void> => {
  await api.delete(`/comparison/lists/${listId}`);
};

const addArtistToList = async (listId: number, artistId: number): Promise<ComparisonList> => {
  const response = await api.post(`/comparison/lists/${listId}/artists`, { artist_id: artistId });
  return response.data;
};

const removeArtistFromList = async (listId: number, artistId: number): Promise<void> => {
  await api.delete(`/comparison/lists/${listId}/artists/${artistId}`);
};

const searchArtists = async (query: string): Promise<ArtistSearchResult[]> => {
  const response = await api.get(`/discovery/artists?search=${encodeURIComponent(query)}&limit=10`);
  return response.data;
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const formatNumber = (num?: number): string => {
  if (!num) return "-";
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
  return num.toString();
};

const formatCurrency = (num: number): string => {
  return num.toLocaleString("fr-FR") + "€";
};

const getScoreColor = (score: number): string => {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-blue-600";
  if (score >= 40) return "text-yellow-600";
  return "text-gray-600";
};

const getRecommendationStyle = (rec?: string): string => {
  switch (rec) {
    case "SIGN":
      return "bg-green-100 text-green-800";
    case "WATCH":
      return "bg-blue-100 text-blue-800";
    case "PASS":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

const getTimingStyle = (bucket?: string): string => {
  switch (bucket) {
    case "IMMINENT":
      return "bg-red-100 text-red-800";
    case "1_3M":
      return "bg-orange-100 text-orange-800";
    case "3_6M":
      return "bg-yellow-100 text-yellow-800";
    case "6_12M":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

// ============================================================================
// COMPONENTS
// ============================================================================

function ListCard({
  list,
  isSelected,
  onSelect,
  onDelete,
}: {
  list: ComparisonList;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md ${
        isSelected ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20" : "hover:border-blue-200 dark:hover:border-blue-800"
      }`}
      onClick={onSelect}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium flex items-center gap-2">
              {isSelected && <div className="w-2 h-2 rounded-full bg-blue-500" />}
              {list.name}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              <Users className="h-3 w-3 inline mr-1" />
              {list.artist_count} artiste{list.artist_count > 1 ? "s" : ""}
            </p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                className="text-red-600"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Supprimer
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
}

function ComparisonTable({ artists }: { artists: ArtistComparisonData[] }) {
  if (artists.length === 0) {
    return (
      <div className="text-center py-16 px-6">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
          <Scale className="h-10 w-10 text-blue-500" />
        </div>
        <h3 className="text-xl font-semibold mb-3">Aucun artiste à comparer</h3>
        <p className="text-muted-foreground max-w-md mx-auto mb-6">
          Ajoutez des artistes depuis votre historique ou la page Discovery pour créer une comparaison détaillée.
        </p>
        <Link href="/discovery">
          <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-md">
            <Sparkles className="h-4 w-4 mr-2" />
            Découvrir des artistes
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </Link>
      </div>
    );
  }

  // Find best values for highlighting
  const maxScore = Math.max(...artists.map((a) => a.score));
  const maxListeners = Math.max(...artists.map((a) => a.monthly_listeners || 0));
  const maxVelocity = Math.max(...artists.map((a) => a.velocity || 0));

  // Comparison rows configuration
  const rows = [
    {
      label: "Score Discovery",
      icon: Star,
      getValue: (a: ArtistComparisonData) => a.score,
      format: (v: number) => v.toString(),
      isBest: (v: number) => v === maxScore,
      color: (v: number) => getScoreColor(v),
    },
    {
      label: "Recommandation",
      icon: Check,
      getValue: (a: ArtistComparisonData) => a.recommendation || "-",
      format: (v: string) => v === "SIGN" ? "À signer" : v === "WATCH" ? "À suivre" : v === "PASS" ? "Passer" : v,
      isBest: (v: string) => v === "SIGN",
      badgeStyle: (a: ArtistComparisonData) => getRecommendationStyle(a.recommendation),
    },
    {
      label: "Timing",
      icon: Clock,
      getValue: (a: ArtistComparisonData) => a.timing_label || a.timing_bucket || "-",
      format: (v: string) => v,
      isBest: (v: string, a: ArtistComparisonData) => a.timing_bucket === "IMMINENT",
      badgeStyle: (a: ArtistComparisonData) => getTimingStyle(a.timing_bucket),
    },
    {
      label: "Auditeurs mensuels",
      icon: Users,
      getValue: (a: ArtistComparisonData) => a.monthly_listeners || 0,
      format: (v: number) => formatNumber(v),
      isBest: (v: number) => v === maxListeners && v > 0,
    },
    {
      label: "Croissance",
      icon: TrendingUp,
      getValue: (a: ArtistComparisonData) => a.velocity || 0,
      format: (v: number) => v > 0 ? `+${(v * 100).toFixed(0)}%/mois` : "-",
      isBest: (v: number) => v === maxVelocity && v > 0,
      color: (v: number) => v > 0 ? "text-green-600" : "",
    },
    {
      label: "Accélération",
      icon: TrendingUp,
      getValue: (a: ArtistComparisonData) => a.acceleration || 0,
      format: (v: number) => {
        if (v === 0) return "-";
        return v > 0 ? `+${(v * 100).toFixed(0)}%` : `${(v * 100).toFixed(0)}%`;
      },
      icon2: (v: number) => v > 0 ? ArrowUpRight : v < 0 ? ArrowDownRight : Minus,
      color: (v: number) => v > 0 ? "text-green-600" : v < 0 ? "text-red-600" : "",
    },
    {
      label: "Pays",
      icon: null,
      getValue: (a: ArtistComparisonData) => a.country || "-",
      format: (v: string) => v,
    },
    {
      label: "Genres",
      icon: null,
      getValue: (a: ArtistComparisonData) => a.genres?.join(", ") || "-",
      format: (v: string) => v,
    },
    {
      label: "Cachet estimé",
      icon: DollarSign,
      getValue: (a: ArtistComparisonData) => a.booking_range?.optimal || 0,
      format: (v: number, a: ArtistComparisonData) => {
        if (!a.booking_range) return "-";
        return `${formatCurrency(a.booking_range.min)} - ${formatCurrency(a.booking_range.max)}`;
      },
    },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left p-3 bg-gray-50 dark:bg-gray-800 font-medium text-sm w-48">
              Critère
            </th>
            {artists.map((artist) => (
              <th key={artist.id} className="p-3 bg-gray-50 dark:bg-gray-800 text-center min-w-[200px]">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-16 h-16 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                    {artist.image_url ? (
                      <Image
                        src={artist.image_url}
                        alt={artist.name}
                        width={64}
                        height={64}
                        className="object-cover w-full h-full"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Users className="h-6 w-6 text-gray-400" />
                      </div>
                    )}
                  </div>
                  <span className="font-medium">{artist.name}</span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx} className="border-t">
              <td className="p-3 font-medium text-sm flex items-center gap-2">
                {row.icon && <row.icon className="h-4 w-4 text-muted-foreground" />}
                {row.label}
              </td>
              {artists.map((artist) => {
                const value = row.getValue(artist);
                const formatted = row.format(value as never, artist);
                const isBest = row.isBest?.(value as never, artist);
                const colorClass = row.color?.(value as never) || "";
                const badgeStyle = row.badgeStyle?.(artist);

                return (
                  <td
                    key={artist.id}
                    className={`p-3 text-center ${isBest ? "bg-green-50 dark:bg-green-900/20" : ""}`}
                  >
                    {badgeStyle ? (
                      <Badge className={badgeStyle}>{formatted}</Badge>
                    ) : (
                      <span className={`font-medium ${colorClass}`}>
                        {formatted}
                        {isBest && <span className="ml-1 text-green-500">✓</span>}
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DriversRisksComparison({ artists }: { artists: ArtistComparisonData[] }) {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${artists.length}, 1fr)` }}>
      {artists.map((artist) => (
        <Card key={artist.id}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{artist.name}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Drivers */}
            <div>
              <h4 className="text-sm font-medium text-green-600 mb-2 flex items-center gap-1">
                <ArrowUpRight className="h-4 w-4" />
                Points forts
              </h4>
              {artist.drivers.length > 0 ? (
                <ul className="space-y-1">
                  {artist.drivers.slice(0, 3).map((d, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <Check className="h-3 w-3 text-green-500 mt-1 flex-shrink-0" />
                      <span>{d.label}</span>
                      {d.value && <span className="text-green-600 ml-auto">{d.value}</span>}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">Aucun</p>
              )}
            </div>

            {/* Risks */}
            <div>
              <h4 className="text-sm font-medium text-red-600 mb-2 flex items-center gap-1">
                <ArrowDownRight className="h-4 w-4" />
                Points de vigilance
              </h4>
              {artist.risks.length > 0 ? (
                <ul className="space-y-1">
                  {artist.risks.slice(0, 3).map((r, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <X className="h-3 w-3 text-red-500 mt-1 flex-shrink-0" />
                      <span>{r.label}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">Aucun</p>
              )}
            </div>

            {/* Signals */}
            {artist.signals.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-blue-600 mb-2">Signaux</h4>
                <div className="flex flex-wrap gap-1">
                  {artist.signals.map((s, i) => (
                    <Badge key={i} variant="secondary" className="text-xs">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================

function ComparisonV3Page() {
  const queryClient = useQueryClient();

  // State
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showAddArtistDialog, setShowAddArtistDialog] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [artistSearch, setArtistSearch] = useState("");

  // Queries
  const listsQuery = useQuery({
    queryKey: ["comparison-lists"],
    queryFn: fetchLists,
    staleTime: 60 * 1000,
  });

  const listDetailQuery = useQuery({
    queryKey: ["comparison-list", selectedListId],
    queryFn: () => fetchListDetail(selectedListId!),
    enabled: !!selectedListId,
    staleTime: 30 * 1000,
  });

  const artistSearchQuery = useQuery({
    queryKey: ["artist-search", artistSearch],
    queryFn: () => searchArtists(artistSearch),
    enabled: artistSearch.length >= 2,
    staleTime: 10 * 1000,
  });

  // Auto-select first list
  useEffect(() => {
    if (listsQuery.data && listsQuery.data.length > 0 && !selectedListId) {
      setSelectedListId(listsQuery.data[0].id);
    }
  }, [listsQuery.data, selectedListId]);

  // Mutations
  const createListMutation = useMutation({
    mutationFn: createList,
    onSuccess: (newList) => {
      queryClient.invalidateQueries({ queryKey: ["comparison-lists"] });
      setSelectedListId(newList.id);
      setShowCreateDialog(false);
      setNewListName("");
      toast.success("Shortlist créée", { description: `"${newList.name}" a été créée` });
    },
  });

  const deleteListMutation = useMutation({
    mutationFn: deleteList,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comparison-lists"] });
      setSelectedListId(null);
      toast.success("Shortlist supprimée");
    },
  });

  const addArtistMutation = useMutation({
    mutationFn: ({ listId, artistId }: { listId: number; artistId: number }) =>
      addArtistToList(listId, artistId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comparison-list", selectedListId] });
      queryClient.invalidateQueries({ queryKey: ["comparison-lists"] });
      setShowAddArtistDialog(false);
      setArtistSearch("");
      toast.success("Artiste ajouté");
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.detail || "Erreur lors de l'ajout";
      toast.error("Erreur", { description: msg });
    },
  });

  const removeArtistMutation = useMutation({
    mutationFn: ({ listId, artistId }: { listId: number; artistId: number }) =>
      removeArtistFromList(listId, artistId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comparison-list", selectedListId] });
      queryClient.invalidateQueries({ queryKey: ["comparison-lists"] });
      toast.success("Artiste retiré");
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <GitCompare className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Comparaison</h1>
            <p className="text-muted-foreground text-sm">
              {listsQuery.data?.length || 0} shortlists · {listsQuery.data?.reduce((acc, l) => acc + l.artist_count, 0) || 0} artistes
            </p>
          </div>
        </div>
        
        <Button onClick={() => setShowCreateDialog(true)} className="bg-primary hover:bg-primary/90">
          <Plus className="h-4 w-4 mr-2" />
          Nouvelle shortlist
        </Button>
      </div>

      {/* Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar: Lists */}
        <div className="space-y-4">
          <h2 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
            Mes shortlists
          </h2>

          {listsQuery.isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
          ) : listsQuery.data?.length === 0 ? (
            <Card className="p-6 text-center border-dashed border-2">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-3">
                <GitCompare className="h-6 w-6 text-blue-500" />
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                Créez votre première shortlist
              </p>
              <Button size="sm" onClick={() => setShowCreateDialog(true)} className="bg-primary hover:bg-primary/90">
                <Plus className="h-4 w-4 mr-1" />
                Nouvelle shortlist
              </Button>
            </Card>
          ) : (
            <div className="space-y-2">
              {listsQuery.data?.map((list) => (
                <ListCard
                  key={list.id}
                  list={list}
                  isSelected={list.id === selectedListId}
                  onSelect={() => setSelectedListId(list.id)}
                  onDelete={() => deleteListMutation.mutate(list.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Main: Comparison */}
        <div className="lg:col-span-3 space-y-6">
          {!selectedListId ? (
            <Card className="p-16 text-center border-dashed border-2">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                <GitCompare className="h-10 w-10 text-blue-500" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Sélectionnez une shortlist</h3>
              <p className="text-muted-foreground max-w-md mx-auto mb-6">
                Choisissez une shortlist existante ou créez-en une nouvelle pour commencer à comparer des artistes
              </p>
              <Button onClick={() => setShowCreateDialog(true)} className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white">
                <Plus className="h-4 w-4 mr-2" />
                Créer une shortlist
              </Button>
            </Card>
          ) : listDetailQuery.isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          ) : listDetailQuery.data ? (
            <>
              {/* List header */}
              <Card className="p-4">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                      <GitCompare className="h-5 w-5 text-blue-500" />
                      {listDetailQuery.data.name}
                    </h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      {listDetailQuery.data.artists.length}/4 artistes
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => listDetailQuery.refetch()}
                      disabled={listDetailQuery.isRefetching}
                    >
                      <RefreshCw
                        className={`h-4 w-4 mr-1 ${
                          listDetailQuery.isRefetching ? "animate-spin" : ""
                        }`}
                      />
                      Actualiser
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => setShowAddArtistDialog(true)}
                      disabled={listDetailQuery.data.artists.length >= 4}
                      className="bg-primary hover:bg-primary/90"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Ajouter un artiste
                    </Button>
                  </div>
                </div>

                {/* Artists chips for removal */}
                {listDetailQuery.data.artists.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t">
                    <span className="text-sm text-muted-foreground self-center mr-2">Artistes:</span>
                    {listDetailQuery.data.artists.map((artist) => (
                      <Badge
                        key={artist.id}
                        variant="secondary"
                        className="py-1.5 px-3 flex items-center gap-2 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30"
                      >
                        {artist.image_url && (
                          <div className="w-5 h-5 rounded-full overflow-hidden">
                            <Image src={artist.image_url} alt={artist.name} width={20} height={20} className="object-cover" />
                          </div>
                        )}
                        {artist.name}
                        <button
                          onClick={() =>
                            removeArtistMutation.mutate({
                              listId: selectedListId,
                              artistId: artist.id,
                            })
                          }
                          className="hover:text-red-500 transition-colors"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </Card>

              {/* Comparison table */}
              <Card>
                <CardContent className="p-0">
                  <ComparisonTable artists={listDetailQuery.data.artists} />
                </CardContent>
              </Card>

              {/* Drivers/Risks comparison */}
              {listDetailQuery.data.artists.length > 0 && (
                <div>
                  <h3 className="font-medium mb-4">Analyse qualitative</h3>
                  <DriversRisksComparison artists={listDetailQuery.data.artists} />
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>

      {/* Create List Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Créer une shortlist</DialogTitle>
            <DialogDescription>
              Donnez un nom à votre nouvelle shortlist de comparaison
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="list-name">Nom de la shortlist</Label>
            <Input
              id="list-name"
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              placeholder="Ex: Candidats Festival 2025"
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Annuler
            </Button>
            <Button
              onClick={() => createListMutation.mutate(newListName)}
              disabled={!newListName.trim() || createListMutation.isPending}
            >
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Artist Dialog */}
      <Dialog open={showAddArtistDialog} onOpenChange={setShowAddArtistDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ajouter un artiste</DialogTitle>
            <DialogDescription>
              Recherchez un artiste de votre base Discovery
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <Label htmlFor="artist-search">Rechercher</Label>
              <Input
                id="artist-search"
                value={artistSearch}
                onChange={(e) => setArtistSearch(e.target.value)}
                placeholder="Nom de l'artiste..."
                className="mt-2"
              />
            </div>

            {artistSearchQuery.isLoading && (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            )}

            {artistSearchQuery.data && artistSearchQuery.data.length > 0 && (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {artistSearchQuery.data.map((artist) => (
                  <div
                    key={artist.id}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer"
                    onClick={() =>
                      addArtistMutation.mutate({
                        listId: selectedListId!,
                        artistId: artist.id,
                      })
                    }
                  >
                    <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 overflow-hidden">
                      {artist.image_url ? (
                        <Image
                          src={artist.image_url}
                          alt={artist.name}
                          width={40}
                          height={40}
                          className="object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Users className="h-4 w-4 text-gray-400" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{artist.name}</p>
                      <p className="text-xs text-muted-foreground">
                        Score: {artist.score} • {formatNumber(artist.monthly_listeners)} auditeurs
                      </p>
                    </div>
                    <Plus className="h-4 w-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            )}

            {artistSearchQuery.data && artistSearchQuery.data.length === 0 && artistSearch.length >= 2 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                Aucun artiste trouvé. Ajoutez-le d'abord via Discovery.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddArtistDialog(false)}>
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// EXPORT
// ============================================================================

export default function ComparisonPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <ComparisonV3Page />
      </AppLayout>
    </ProtectedRoute>
  );
}
