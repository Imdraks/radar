"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useFiltersStore } from "@/store/filters";
import {
  Bookmark,
  BookmarkPlus,
  MoreVertical,
  Trash2,
  Edit,
  Play,
  Star,
  Clock,
} from "lucide-react";

interface SavedSearch {
  id: string;
  name: string;
  filters: {
    status?: string[];
    source_type?: string[];
    score_min?: number;
    maxScore?: number;
    search?: string;
    region?: string;
    budget_min?: number;
    budget_max?: number;
  };
  createdAt: string;
  lastUsed?: string;
  isFavorite: boolean;
  useCount: number;
}

const STORAGE_KEY = "opportunities_saved_searches";

export function SavedSearches() {
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newSearchName, setNewSearchName] = useState("");
  const [editingSearch, setEditingSearch] = useState<SavedSearch | null>(null);
  
  const { filters, setFilters, resetFilters } = useFiltersStore();

  // Load saved searches from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setSavedSearches(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse saved searches:", e);
      }
    }
  }, []);

  // Save to localStorage whenever savedSearches changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(savedSearches));
  }, [savedSearches]);

  const handleSaveSearch = () => {
    if (!newSearchName.trim()) return;

    const newSearch: SavedSearch = {
      id: crypto.randomUUID(),
      name: newSearchName.trim(),
      filters: { ...filters },
      createdAt: new Date().toISOString(),
      isFavorite: false,
      useCount: 0,
    };

    setSavedSearches((prev) => [...prev, newSearch]);
    setNewSearchName("");
    setIsDialogOpen(false);
  };

  const handleApplySearch = (search: SavedSearch) => {
    setFilters(search.filters);
    
    // Update last used and count
    setSavedSearches((prev) =>
      prev.map((s) =>
        s.id === search.id
          ? { ...s, lastUsed: new Date().toISOString(), useCount: s.useCount + 1 }
          : s
      )
    );
  };

  const handleDeleteSearch = (id: string) => {
    setSavedSearches((prev) => prev.filter((s) => s.id !== id));
  };

  const handleToggleFavorite = (id: string) => {
    setSavedSearches((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, isFavorite: !s.isFavorite } : s
      )
    );
  };

  const handleRenameSearch = () => {
    if (!editingSearch || !newSearchName.trim()) return;

    setSavedSearches((prev) =>
      prev.map((s) =>
        s.id === editingSearch.id ? { ...s, name: newSearchName.trim() } : s
      )
    );
    setEditingSearch(null);
    setNewSearchName("");
  };

  const getFilterDescription = (search: SavedSearch): string => {
    const parts: string[] = [];
    const f = search.filters;

    if (f.status?.length) parts.push(`Statut: ${f.status.join(", ")}`);
    if (f.source_type?.length) parts.push(`Sources: ${f.source_type.join(", ")}`);
    if (f.score_min !== undefined) parts.push(`Score min: ${f.score_min}`);
    if (f.search) parts.push(`Recherche: "${f.search}"`);
    if (f.region) parts.push(`Région: ${f.region}`);

    return parts.length ? parts.join(" • ") : "Aucun filtre";
  };

  const sortedSearches = [...savedSearches].sort((a, b) => {
    if (a.isFavorite !== b.isFavorite) return a.isFavorite ? -1 : 1;
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Bookmark className="h-5 w-5" />
          Recherches sauvegardées
        </CardTitle>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <BookmarkPlus className="h-4 w-4 mr-2" />
              Sauvegarder la recherche actuelle
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Sauvegarder la recherche</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <Input
                placeholder="Nom de la recherche..."
                value={newSearchName}
                onChange={(e) => setNewSearchName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveSearch()}
              />
              <div className="text-sm text-muted-foreground">
                <p className="font-medium mb-2">Filtres actuels :</p>
                <ul className="space-y-1">
                  {filters.status?.length ? (
                    <li>Statut: {filters.status.join(", ")}</li>
                  ) : null}
                  {filters.source_type?.length ? (
                    <li>Sources: {filters.source_type.join(", ")}</li>
                  ) : null}
                  {filters.score_min !== undefined ? (
                    <li>Score min: {filters.score_min}</li>
                  ) : null}
                  {filters.search ? <li>Recherche: "{filters.search}"</li> : null}
                  {!Object.values(filters).some((v) =>
                    Array.isArray(v) ? v.length > 0 : v !== undefined
                  ) && <li className="italic">Aucun filtre actif</li>}
                </ul>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                Annuler
              </Button>
              <Button onClick={handleSaveSearch} disabled={!newSearchName.trim()}>
                Sauvegarder
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {savedSearches.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Bookmark className="h-12 w-12 mx-auto mb-4 opacity-20" />
            <p>Aucune recherche sauvegardée</p>
            <p className="text-sm mt-1">
              Appliquez des filtres puis cliquez sur "Sauvegarder"
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sortedSearches.map((search) => (
              <div
                key={search.id}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <button
                    onClick={() => handleToggleFavorite(search.id)}
                    className="shrink-0"
                  >
                    <Star
                      className={`h-4 w-4 ${
                        search.isFavorite
                          ? "fill-yellow-400 text-yellow-400"
                          : "text-muted-foreground hover:text-yellow-400"
                      }`}
                    />
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{search.name}</span>
                      {search.useCount > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {search.useCount}x
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {getFilterDescription(search)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleApplySearch(search)}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Appliquer
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="icon" variant="ghost">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => {
                          setEditingSearch(search);
                          setNewSearchName(search.name);
                        }}
                      >
                        <Edit className="h-4 w-4 mr-2" />
                        Renommer
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleDeleteSearch(search.id)}
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Supprimer
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Rename Dialog */}
        <Dialog
          open={editingSearch !== null}
          onOpenChange={(open) => !open && setEditingSearch(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Renommer la recherche</DialogTitle>
            </DialogHeader>
            <Input
              value={newSearchName}
              onChange={(e) => setNewSearchName(e.target.value)}
              placeholder="Nouveau nom..."
              onKeyDown={(e) => e.key === "Enter" && handleRenameSearch()}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingSearch(null)}>
                Annuler
              </Button>
              <Button onClick={handleRenameSearch}>Enregistrer</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
