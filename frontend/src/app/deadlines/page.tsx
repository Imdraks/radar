"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Clock,
  Calendar,
  AlertTriangle,
  Bell,
  BellOff,
  Check,
  X,
  ArrowRight,
  RefreshCw,
  Loader2,
  Filter,
} from "lucide-react";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toaster";
import { deadlinesApi } from "@/lib/api";
import { formatRelativeDate, truncate } from "@/lib/utils";
import type { DeadlineAlert, AlertStatus } from "@/lib/types";

// Backend alert type
interface DeadlineAlertResponse {
  id: string;
  opportunity_id: string;
  opportunity_title: string;
  organization?: string;
  alert_type: string;
  scheduled_for: string;
  deadline_at: string;
  status: AlertStatus;
  sent_at?: string;
}

interface DeadlinesResponse {
  alerts: DeadlineAlertResponse[];
  total: number;
}

// Calculate days remaining from deadline
function getDaysRemaining(deadlineAt: string): number {
  const now = new Date();
  const deadline = new Date(deadlineAt);
  const diffTime = deadline.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
}

function getUrgencyColor(days: number): string {
  if (days <= 1) return "bg-red-500";
  if (days <= 3) return "bg-orange-500";
  if (days <= 7) return "bg-yellow-500";
  return "bg-green-500";
}

function getUrgencyBadge(days: number) {
  if (days <= 1) {
    return (
      <Badge variant="destructive" className="animate-pulse">
        ⚡ J-{days}
      </Badge>
    );
  }
  if (days <= 3) {
    return (
      <Badge className="bg-orange-500 text-white">
        🔥 J-{days}
      </Badge>
    );
  }
  if (days <= 7) {
    return (
      <Badge className="bg-yellow-500 text-black">
        ⏰ J-{days}
      </Badge>
    );
  }
  return (
    <Badge variant="secondary">
      📅 J-{days}
    </Badge>
  );
}

function getStatusBadge(status: AlertStatus) {
  switch (status) {
    case "pending":
      return <Badge variant="outline">En attente</Badge>;
    case "sent":
      return <Badge className="bg-blue-500">Envoyée</Badge>;
    case "acknowledged":
      return <Badge className="bg-green-500">Confirmée</Badge>;
    case "dismissed":
      return <Badge variant="secondary">Ignorée</Badge>;
    default:
      return null;
  }
}

function DeadlineAlertCard({ alert }: { alert: DeadlineAlertResponse }) {
  const days_remaining = getDaysRemaining(alert.deadline_at);

  return (
    <Card className={`border-l-4 ${getUrgencyColor(days_remaining)} hover:shadow-md transition-shadow`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Urgency indicator */}
          <div className="flex-shrink-0">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold ${getUrgencyColor(days_remaining)}`}>
              J-{days_remaining}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Link
                href={`/leads/${alert.opportunity_id}`}
                className="font-semibold text-lg hover:text-primary truncate"
              >
                {truncate(alert.opportunity_title, 60)}
              </Link>
              {getUrgencyBadge(days_remaining)}
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground mb-2">
              {alert.organization && (
                <span>🏢 {alert.organization}</span>
              )}
              {alert.deadline_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(alert.deadline_at).toLocaleDateString("fr-FR", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })}
                </span>
              )}
            </div>

            {/* Alert status */}
            <div className="flex gap-2">
              <div className="flex items-center gap-1">
                <Bell className="h-3 w-3" />
                <span className="text-xs">{alert.alert_type}</span>
                {getStatusBadge(alert.status)}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex-shrink-0">
            <Link href={`/leads/${alert.opportunity_id}`}>
              <Button size="sm" variant="outline">
                Voir
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DeadlinesContent() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState("upcoming");

  // Fetch upcoming deadlines
  const { data: upcomingDeadlines, isLoading: upcomingLoading } = useQuery<DeadlinesResponse>({
    queryKey: ["deadlines", "upcoming"],
    queryFn: () => deadlinesApi.getUpcoming(30),
  });

  // Fetch past deadlines
  const { data: pastDeadlines, isLoading: pastLoading } = useQuery<DeadlinesResponse>({
    queryKey: ["deadlines", "past"],
    queryFn: () => deadlinesApi.getPast(30),
    enabled: activeTab === "past",
  });

  // Schedule alerts mutation
  const scheduleMutation = useMutation({
    mutationFn: deadlinesApi.scheduleAll,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
      addToast({
        title: "Alertes planifiées",
        description: `${data.created} nouvelles alertes créées`,
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de planifier les alertes",
        type: "error",
      });
    },
  });

  // Group alerts by urgency (calculate days remaining from deadline)
  const alerts = upcomingDeadlines?.alerts ?? [];
  const groupedAlerts = {
    urgent: alerts.filter((a) => getDaysRemaining(a.deadline_at) <= 3),
    soon: alerts.filter((a) => {
      const days = getDaysRemaining(a.deadline_at);
      return days > 3 && days <= 7;
    }),
    later: alerts.filter((a) => getDaysRemaining(a.deadline_at) > 7),
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Clock className="h-8 w-8 text-orange-500" />
            Deadline Guard
          </h1>
          <p className="text-muted-foreground">
            Ne manquez jamais une échéance importante
          </p>
        </div>

        <Button
          onClick={() => scheduleMutation.mutate()}
          disabled={scheduleMutation.isPending}
        >
          {scheduleMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Bell className="h-4 w-4 mr-2" />
          )}
          Planifier alertes
        </Button>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-100">
                <AlertTriangle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{groupedAlerts.urgent.length}</p>
                <p className="text-sm text-muted-foreground">Urgentes (J-3)</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-100">
                <Clock className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{groupedAlerts.soon.length}</p>
                <p className="text-sm text-muted-foreground">Cette semaine</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100">
                <Calendar className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{groupedAlerts.later.length}</p>
                <p className="text-sm text-muted-foreground">À venir</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Bell className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{upcomingDeadlines?.total || 0}</p>
                <p className="text-sm text-muted-foreground">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="upcoming" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            À venir
          </TabsTrigger>
          <TabsTrigger value="past" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Passées
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="space-y-6">
          {upcomingLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              {/* Urgent section */}
              {groupedAlerts.urgent.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    Urgent (J-3 ou moins)
                  </h2>
                  <div className="space-y-3">
                    {groupedAlerts.urgent.map((alert) => (
                      <DeadlineAlertCard key={alert.id} alert={alert} />
                    ))}
                  </div>
                </div>
              )}

              {/* This week section */}
              {groupedAlerts.soon.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Clock className="h-5 w-5 text-orange-500" />
                    Cette semaine
                  </h2>
                  <div className="space-y-3">
                    {groupedAlerts.soon.map((alert) => (
                      <DeadlineAlertCard key={alert.id} alert={alert} />
                    ))}
                  </div>
                </div>
              )}

              {/* Later section */}
              {groupedAlerts.later.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-green-500" />
                    Plus tard
                  </h2>
                  <div className="space-y-3">
                    {groupedAlerts.later.map((alert) => (
                      <DeadlineAlertCard key={alert.id} alert={alert} />
                    ))}
                  </div>
                </div>
              )}

              {/* Empty state */}
              {alerts.length === 0 && (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Calendar className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                    <h3 className="font-semibold text-lg mb-2">Aucune deadline à venir</h3>
                    <p className="text-muted-foreground">
                      Toutes les opportunités sont à jour !
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        <TabsContent value="past">
          {pastLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : pastDeadlines?.alerts && pastDeadlines.alerts.length > 0 ? (
            <div className="space-y-3">
              {pastDeadlines.alerts.map((alert) => (
                <Card key={alert.id} className="opacity-75">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <X className="h-5 w-5 text-red-500" />
                        <div>
                          <Link
                            href={`/leads/${alert.opportunity_id}`}
                            className="font-medium hover:text-primary"
                          >
                            {truncate(alert.opportunity_title, 50)}
                          </Link>
                          <p className="text-sm text-muted-foreground">
                            Expirée il y a {Math.abs(getDaysRemaining(alert.deadline_at))} jours
                          </p>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-red-500">
                        Expirée
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Check className="h-12 w-12 mx-auto mb-4 text-green-500 opacity-50" />
                <h3 className="font-semibold text-lg mb-2">Aucune deadline passée</h3>
                <p className="text-muted-foreground">
                  Félicitations, vous êtes à jour !
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function DeadlinesPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <DeadlinesContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
