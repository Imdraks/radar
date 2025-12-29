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
import { LeadFilters } from "@/components/filters";
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

function LeadsContent() {
  const { filters, page, perPage, setPage, setPerPage } = useFiltersStore();

  const { data, isLoading, error } = useQuery<PaginatedResponse<Opportunity>>({
    queryKey: ["leads", filters, page, perPage],
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
        <h1 className="text-3xl font-bold">Leads</h1>
        <p className="text-muted-foreground">
          {data?.total || 0} leads trouvés
        </p>
      </div>

      {/* Filters */}
      <LeadFilters />

      {/* Results */}
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
          <div className="grid gap-4">
            {data?.items.map((lead) => (
              <LeadCard key={lead.id} lead={lead} />
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

function LeadCard({ lead }: { lead: Opportunity }) {
  const handleExternalClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (lead.url_primary) {
      window.open(lead.url_primary, '_blank', 'noopener,noreferrer');
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
    <Link href={`/leads/${lead.id}`}>
      <Card className="hover:border-primary/50 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer touch-active group">
        <CardContent className="p-3 sm:p-4">
          <div className="flex gap-3 sm:gap-4">
            {/* Score */}
            <div
              className={`flex-shrink-0 w-12 h-12 sm:w-16 sm:h-16 rounded-xl flex flex-col items-center justify-center transition-transform group-hover:scale-105 ${getScoreBgColor(
                lead.score
              )}`}
            >
              <span className={`text-lg sm:text-2xl font-bold ${getScoreColor(lead.score)}`}>
                {lead.score?.toFixed(0) || 0}
              </span>
              <span className="text-[10px] sm:text-xs text-muted-foreground">score</span>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-base sm:text-lg truncate group-hover:text-primary transition-colors">
                    {lead.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-muted-foreground line-clamp-2 mt-1">
                    {truncate(cleanDescription(lead.description), 200)}
                  </p>
                </div>

                {/* External link */}
                {lead.url_primary && (
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
              </div>

              {/* Meta info */}
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
              </div>

              {/* Contact - hidden on mobile */}
              {(lead.contact_email || lead.contact_phone) && (
                <div className="hidden sm:flex items-center gap-3 mt-2 text-sm">
                  {lead.contact_email && (
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Mail className="h-3 w-3" />
                      {lead.contact_email}
                    </span>
                  )}
                  {lead.contact_phone && (
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      {lead.contact_phone}
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

export default function LeadsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <LeadsContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
