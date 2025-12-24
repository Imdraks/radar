"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Search,
  Filter,
  FileText,
  User,
  Building,
  Hash,
  Clock,
  ChevronRight,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { collectionApi, type Brief } from "@/lib/api";
import { BriefCard } from "@/components/collection";
import { formatRelativeDate } from "@/lib/utils";

const OBJECTIVES = [
  { value: "all", label: "Tous les objectifs" },
  { value: "SPONSOR", label: "Sponsor / Partenariat" },
  { value: "BOOKING", label: "Booking artiste" },
  { value: "PRESS", label: "Presse / Média" },
  { value: "VENUE", label: "Lieu / Salle" },
  { value: "SUPPLIER", label: "Prestataires" },
  { value: "GRANT", label: "Subventions" },
];

function BriefsContent() {
  const [search, setSearch] = useState("");
  const [objectiveFilter, setObjectiveFilter] = useState("all");
  
  const { data: briefs, isLoading, error } = useQuery<Brief[]>({
    queryKey: ["briefs", objectiveFilter],
    queryFn: () => collectionApi.getBriefs({
      objective: objectiveFilter !== "all" ? objectiveFilter : undefined,
      limit: 50,
    }),
  });
  
  const filteredBriefs = briefs?.filter(brief => {
    if (search) {
      const searchLower = search.toLowerCase();
      return brief.entity_name?.toLowerCase().includes(searchLower) ||
             brief.overview?.toLowerCase().includes(searchLower);
    }
    return true;
  });
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Dossiers</h1>
          <p className="text-muted-foreground">
            {briefs?.length || 0} dossier(s) générés
          </p>
        </div>
        
        <Link href="/dashboard">
          <Button variant="outline">
            <FileText className="h-4 w-4 mr-2" />
            Nouvelle collecte
          </Button>
        </Link>
      </div>
      
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher un dossier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        
        <Select value={objectiveFilter} onValueChange={setObjectiveFilter}>
          <SelectTrigger className="w-[200px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OBJECTIVES.map((obj) => (
              <SelectItem key={obj.value} value={obj.value}>
                {obj.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      
      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Chargement des dossiers...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-destructive">Erreur lors du chargement</p>
        </div>
      ) : filteredBriefs?.length === 0 ? (
        <Card className="py-12">
          <CardContent className="text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Aucun dossier</h3>
            <p className="text-muted-foreground mb-4">
              {search || objectiveFilter !== "all"
                ? "Aucun dossier ne correspond à vos critères"
                : "Lancez une collecte pour générer des dossiers"}
            </p>
            {!search && objectiveFilter === "all" && (
              <Link href="/dashboard">
                <Button>
                  Lancer une collecte
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredBriefs?.map((brief) => (
            <BriefCard 
              key={brief.id} 
              brief={brief}
              onEntityClick={(entityId) => {
                // Navigate to entity detail page
                window.location.href = `/entities/${entityId}`;
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function BriefsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <BriefsContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
