"use client";

import { useQuery } from "@tanstack/react-query";
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
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { OpportunityFilters } from "@/components/filters";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { opportunitiesApi } from "@/lib/api";
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

function OpportunitiesContent() {
  const { filters, page, perPage, setPage, setPerPage } = useFiltersStore();

  const { data, isLoading, error } = useQuery<PaginatedResponse<Opportunity>>({
    queryKey: ["opportunities", filters, page, perPage],
    queryFn: () =>
      opportunitiesApi.getAll({
        ...filters,
        status: filters.status?.join(","),
        category: filters.category?.join(","),
        source_type: filters.source_type?.join(","),
        page,
        per_page: perPage,
      }),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Opportunités</h1>
        <p className="text-muted-foreground">
          {data?.total || 0} opportunités trouvées
        </p>
      </div>

      {/* Filters */}
      <OpportunityFilters />

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Chargement...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12 text-destructive">
          Erreur lors du chargement des opportunités
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Aucune opportunité ne correspond à vos critères
        </div>
      ) : (
        <>
          <div className="grid gap-4">
            {data?.items.map((opportunity) => (
              <OpportunityCard key={opportunity.id} opportunity={opportunity} />
            ))}
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between">
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

function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const handleExternalClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (opportunity.url_primary) {
      window.open(opportunity.url_primary, '_blank', 'noopener,noreferrer');
    }
  };

  // Nettoyer le HTML de la description
  const cleanDescription = (html: string | undefined): string => {
    if (!html) return "";
    // Supprimer les balises HTML
    const text = html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    return text;
  };

  // Vérifier si une date est valide (après 1900)
  const isValidDate = (dateStr: string | null | undefined): boolean => {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    return date.getFullYear() > 1900;
  };

  return (
    <Link href={`/opportunities/${opportunity.id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer">
        <CardContent className="p-4">
          <div className="flex gap-4">
            {/* Score */}
            <div
              className={`flex-shrink-0 w-16 h-16 rounded-lg flex flex-col items-center justify-center ${getScoreBgColor(
                opportunity.score
              )}`}
            >
              <span className={`text-2xl font-bold ${getScoreColor(opportunity.score)}`}>
                {opportunity.score?.toFixed(0) || 0}
              </span>
              <span className="text-xs text-muted-foreground">score</span>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg truncate">
                    {opportunity.title}
                  </h3>
                  <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                    {truncate(cleanDescription(opportunity.description), 200)}
                  </p>
                </div>

                {/* External link */}
                {opportunity.url_primary && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleExternalClick}
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                )}
              </div>

              {/* Badges */}
              <div className="flex flex-wrap items-center gap-2 mt-3">
                <Badge className={getStatusColor(opportunity.status)}>
                  {getStatusLabel(opportunity.status)}
                </Badge>
                {opportunity.category && (
                  <Badge variant="outline">
                    <Tag className="h-3 w-3 mr-1" />
                    {getCategoryLabel(opportunity.category)}
                  </Badge>
                )}
                {opportunity.source_type && (
                  <Badge variant="secondary">
                    {opportunity.source_type.toUpperCase()}
                  </Badge>
                )}
              </div>

              {/* Meta info */}
              <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-muted-foreground">
                {opportunity.organization_name && (
                  <span className="flex items-center gap-1">
                    <Building className="h-4 w-4" />
                    {opportunity.organization_name}
                  </span>
                )}
                {opportunity.region && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {opportunity.region}
                  </span>
                )}
                {(opportunity.budget_hint || opportunity.budget_amount) && (
                  <span className="flex items-center gap-1 text-green-600 font-medium">
                    <Euro className="h-4 w-4" />
                    {opportunity.budget_hint || formatCurrency(opportunity.budget_amount)}
                  </span>
                )}
                {isValidDate(opportunity.deadline_at) && (
                  <span className="flex items-center gap-1 text-orange-600">
                    <Clock className="h-4 w-4" />
                    {formatRelativeDate(opportunity.deadline_at)}
                  </span>
                )}
              </div>

              {/* Contact */}
              {(opportunity.contact_email || opportunity.contact_phone) && (
                <div className="flex items-center gap-3 mt-2 text-sm">
                  {opportunity.contact_email && (
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Mail className="h-3 w-3" />
                      {opportunity.contact_email}
                    </span>
                  )}
                  {opportunity.contact_phone && (
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      {opportunity.contact_phone}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function OpportunitiesPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <OpportunitiesContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
