"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Sparkles,
  Calendar,
  Star,
  Target,
  Clock,
  DollarSign,
  ArrowRight,
  RefreshCw,
  Loader2,
  ChevronDown,
} from "lucide-react";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toaster";
import { shortlistsApi, profilesApi } from "@/lib/api";
import { formatRelativeDate, truncate, getScoreColor } from "@/lib/utils";
import type { DailyShortlist, Profile, ShortlistItem } from "@/lib/types";

function ShortlistContent() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [selectedProfileId, setSelectedProfileId] = useState<number | undefined>();

  // Fetch profiles
  const { data: profiles } = useQuery<Profile[]>({
    queryKey: ["profiles"],
    queryFn: profilesApi.getAll,
  });

  // Fetch today's shortlist (only when profile is selected)
  const { data: todayShortlist, isLoading: shortlistLoading } = useQuery<DailyShortlist | null>({
    queryKey: ["shortlists", "today", selectedProfileId],
    queryFn: () => shortlistsApi.getToday(selectedProfileId),
    enabled: !!selectedProfileId,
  });

  // Fetch historical shortlists (only when profile is selected)
  const { data: historicalShortlists, isLoading: historyLoading } = useQuery<DailyShortlist[]>({
    queryKey: ["shortlists", "history", selectedProfileId],
    queryFn: () => shortlistsApi.getAll({ 
      profile_id: selectedProfileId, 
      limit: 7 
    }),
    enabled: !!selectedProfileId,
  });

  // Generate shortlist mutation
  const generateMutation = useMutation({
    mutationFn: () => shortlistsApi.generate(selectedProfileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shortlists"] });
      addToast({
        title: "Shortlist générée",
        description: "La shortlist quotidienne a été recalculée",
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de générer la shortlist",
        type: "error",
      });
    },
  });

  const renderReasonBadge = (reason: string, index: number) => (
    <Badge
      key={index}
      variant="secondary"
      className="flex items-center gap-1 text-xs"
    >
      {reason}
    </Badge>
  );

  const renderShortlistItem = (item: ShortlistItem, index: number) => (
    <Card key={item.opportunity_id} className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Rank badge */}
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${
              index === 0 ? "bg-yellow-500" :
              index === 1 ? "bg-gray-400" :
              index === 2 ? "bg-amber-600" :
              "bg-slate-500"
            }`}>
              {index + 1}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Link
                href={`/leads/${item.opportunity_id}`}
                className="font-semibold text-lg hover:text-primary truncate"
              >
                {item.title}
              </Link>
            </div>

            <div className="text-sm text-muted-foreground mb-2">
              {item.organization && (
                <span>{item.organization}</span>
              )}
              {item.deadline_at && (
                <span className="ml-2">
                  <Clock className="h-3 w-3 inline mr-1" />
                  {new Date(item.deadline_at).toLocaleDateString("fr-FR")}
                </span>
              )}
            </div>

            {/* Reasons */}
            <div className="flex flex-wrap gap-1.5">
              {item.reasons.map((reason, i) => renderReasonBadge(reason, i))}
            </div>
          </div>

          {/* Fit Score */}
          <div className="flex-shrink-0 text-right">
            <div className="flex items-center gap-1 mb-1">
              <Star className="h-4 w-4 text-yellow-500" />
              <span className="font-bold text-lg">{item.fit_score}%</span>
            </div>
            <Progress 
              value={item.fit_score} 
              className={`h-2 w-20 ${getScoreColor(item.fit_score)}`}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-yellow-500" />
            Daily Picks
          </h1>
          <p className="text-muted-foreground">
            Vos meilleures opportunités du jour, sélectionnées par l&apos;IA
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Profile selector */}
          <Select
            value={selectedProfileId?.toString() || "all"}
            onValueChange={(value) => 
              setSelectedProfileId(value === "all" ? undefined : parseInt(value))
            }
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Tous les profils" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les profils</SelectItem>
              {Array.isArray(profiles) && profiles.map((profile) => (
                <SelectItem key={profile.id} value={profile.id.toString()}>
                  {profile.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending || !selectedProfileId}
          >
            {generateMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Régénérer
          </Button>
        </div>
      </div>

      {/* Today's Shortlist */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Aujourd&apos;hui
          </CardTitle>
          <CardDescription>
            {todayShortlist?.items_count || 0} opportunités sélectionnées
          </CardDescription>
        </CardHeader>
        <CardContent>
          {shortlistLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : todayShortlist && todayShortlist.items.length > 0 ? (
            <div className="space-y-4">
              {todayShortlist.items.map((item, index) => 
                renderShortlistItem(item, index)
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Sparkles className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>
                {selectedProfileId 
                  ? "Aucune shortlist pour aujourd'hui" 
                  : "Sélectionnez un profil pour voir la shortlist"}
              </p>
              {selectedProfileId && (
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                >
                  {generateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : null}
                  Générer maintenant
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Historical Shortlists */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Historique
          </CardTitle>
          <CardDescription>
            Shortlists des 7 derniers jours
          </CardDescription>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : historicalShortlists && historicalShortlists.length > 0 ? (
            <div className="space-y-3">
              {historicalShortlists.slice(1).map((shortlist) => (
                <div
                  key={shortlist.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">
                      {new Date(shortlist.date).toLocaleDateString("fr-FR", {
                        weekday: "long",
                        day: "numeric",
                        month: "long",
                      })}
                    </span>
                    {shortlist.profile_name && (
                      <Badge variant="outline">{shortlist.profile_name}</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">{shortlist.items_count} picks</Badge>
                    <Link href={`/shortlist/${shortlist.id}`}>
                      <Button size="sm" variant="ghost">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-4 text-muted-foreground">
              Pas encore d&apos;historique
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ShortlistPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <ShortlistContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
