"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Calendar, ExternalLink, Loader2, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { useToast } from "@/components/ui/toaster";

// Google Calendar API types
interface CalendarConnectionStatus {
  connected: boolean;
  email?: string;
  calendar_id?: string;
  last_sync?: string;
}

interface SyncResult {
  success: boolean;
  events_created: number;
  events_updated: number;
  errors: string[];
}

const STORAGE_KEY = "google_calendar_config";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function GoogleCalendarIntegration() {
  const { addToast } = useToast();
  const searchParams = useSearchParams();
  
  const [status, setStatus] = useState<CalendarConnectionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [autoSync, setAutoSync] = useState(true);
  const [reminderMinutes, setReminderMinutes] = useState(60);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [checkingStatus, setCheckingStatus] = useState(true);

  // Check connection status on mount
  const checkStatus = useCallback(async () => {
    setCheckingStatus(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setStatus({ connected: false });
        return;
      }

      const response = await workspaceFetch(`${API_BASE}/api/v1/calendar/google/status`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data: CalendarConnectionStatus = await response.json();
        setStatus(data);
      } else {
        setStatus({ connected: false });
      }
    } catch (error) {
      console.error("Failed to check calendar status:", error);
      setStatus({ connected: false });
    } finally {
      setCheckingStatus(false);
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Handle OAuth callback params
  useEffect(() => {
    const connected = searchParams.get("connected");
    const error = searchParams.get("error");

    if (connected === "true") {
      addToast({
        title: "Google Calendar connecté !",
        description: "Vous pouvez maintenant synchroniser vos deadlines.",
        type: "success",
      });
      checkStatus();
      // Clean URL
      window.history.replaceState({}, "", "/settings?tab=calendar");
    }

    if (error) {
      addToast({
        title: "Erreur de connexion",
        description: error,
        type: "error",
      });
      // Clean URL
      window.history.replaceState({}, "", "/settings?tab=calendar");
    }
  }, [searchParams, addToast, checkStatus]);

  // Load settings from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const config = JSON.parse(stored);
        setAutoSync(config.autoSync ?? true);
        setReminderMinutes(config.reminderMinutes || 60);
      } catch (e) {
        console.error("Failed to parse calendar config:", e);
      }
    }
  }, []);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        autoSync,
        reminderMinutes,
      })
    );
  }, [autoSync, reminderMinutes]);

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        addToast({
          title: "Non authentifié",
          description: "Veuillez vous connecter d'abord.",
          type: "error",
        });
        return;
      }

      const response = await workspaceFetch(`${API_BASE}/api/v1/calendar/google/init`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to initialize OAuth");
      }

      const data = await response.json();
      
      // Redirect to Google OAuth
      window.location.href = data.auth_url;
    } catch (error) {
      console.error("Failed to connect to Google Calendar:", error);
      addToast({
        title: "Erreur",
        description: "Impossible d'initialiser la connexion Google Calendar.",
        type: "error",
      });
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await workspaceFetch(`${API_BASE}/api/v1/calendar/google/disconnect`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setStatus({ connected: false });
        setSyncResult(null);
        addToast({
          title: "Déconnecté",
          description: "Google Calendar a été déconnecté.",
          type: "info",
        });
      }
    } catch (error) {
      console.error("Failed to disconnect:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncAllDeadlines = async () => {
    setIsSyncing(true);
    setSyncResult(null);
    try {
      const token = localStorage.getItem("token");
      const response = await workspaceFetch(`${API_BASE}/api/v1/calendar/google/sync`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Sync failed");
      }

      const result: SyncResult = await response.json();
      setSyncResult(result);

      if (result.success) {
        addToast({
          title: "Synchronisation réussie !",
          description: `${result.events_created} événements créés.`,
          type: "success",
        });
      } else {
        addToast({
          title: "Synchronisation partielle",
          description: `${result.events_created} événements créés, ${result.errors.length} erreurs.`,
          type: "warning",
        });
      }
    } catch (error) {
      console.error("Failed to sync deadlines:", error);
      addToast({
        title: "Erreur",
        description: "Impossible de synchroniser les deadlines.",
        type: "error",
      });
    } finally {
      setIsSyncing(false);
    }
  };

  if (checkingStatus) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Intégration Google Calendar
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          Intégration Google Calendar
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Connection status */}
        <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
          <div className="flex items-center gap-3">
            <div
              className={`h-10 w-10 rounded-full flex items-center justify-center ${
                status?.connected ? "bg-green-100" : "bg-gray-100"
              }`}
            >
              <Calendar
                className={`h-5 w-5 ${
                  status?.connected ? "text-green-600" : "text-gray-400"
                }`}
              />
            </div>
            <div>
              <p className="font-medium">
                {status?.connected ? "Connecté à Google Calendar" : "Non connecté"}
              </p>
              <p className="text-sm text-muted-foreground">
                {status?.connected && status?.email
                  ? `Compte: ${status.email}`
                  : "Connectez-vous pour synchroniser les deadlines"}
              </p>
            </div>
          </div>
          <Button
            variant={status?.connected ? "outline" : "default"}
            onClick={status?.connected ? handleDisconnect : handleConnect}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            {status?.connected ? "Déconnecter" : "Connecter"}
          </Button>
        </div>

        {status?.connected && (
          <>
            {/* Settings */}
            <div className="space-y-4">
              <h4 className="font-medium">Paramètres</h4>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Synchronisation automatique</p>
                  <p className="text-xs text-muted-foreground">
                    Ajouter automatiquement les deadlines au calendrier
                  </p>
                </div>
                <Switch checked={autoSync} onCheckedChange={setAutoSync} />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Rappel avant deadline</p>
                  <p className="text-xs text-muted-foreground">
                    Recevoir une notification avant l'échéance
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={reminderMinutes}
                    onChange={(e) => setReminderMinutes(parseInt(e.target.value) || 60)}
                    className="w-20"
                    min={5}
                    max={1440}
                  />
                  <span className="text-sm text-muted-foreground">min</span>
                </div>
              </div>
            </div>

            {/* Sync actions */}
            <div className="space-y-3">
              <Button
                onClick={handleSyncAllDeadlines}
                disabled={isSyncing}
                className="w-full"
              >
                {isSyncing ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Synchroniser toutes les deadlines
              </Button>

              {/* Sync result */}
              {syncResult && (
                <div
                  className={`p-3 rounded-lg flex items-start gap-2 ${
                    syncResult.success
                      ? "bg-green-50 text-green-700"
                      : "bg-yellow-50 text-yellow-700"
                  }`}
                >
                  {syncResult.success ? (
                    <CheckCircle className="h-5 w-5 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-5 w-5 mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium">
                      {syncResult.events_created} événements créés
                    </p>
                    {syncResult.errors.length > 0 && (
                      <ul className="text-xs mt-1 space-y-0.5">
                        {syncResult.errors.slice(0, 3).map((err, i) => (
                          <li key={i}>• {err}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Open Google Calendar */}
            <div className="pt-2">
              <a
                href="https://calendar.google.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline flex items-center gap-1"
              >
                Ouvrir Google Calendar
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </>
        )}

        {/* Info */}
        <div className="text-xs text-muted-foreground border-t pt-4">
          <p>
            L'intégration Google Calendar vous permet de synchroniser les deadlines
            des opportunités directement dans votre agenda et de recevoir des rappels.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// Hook for syncing single opportunity to calendar
export function useGoogleCalendar() {
  const { addToast } = useToast();

  const syncToCalendar = async (opportunityId: number | string) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await workspaceFetch(
        `${API_BASE}/api/v1/calendar/google/sync-single/${opportunityId}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Sync failed");
      }

      const result = await response.json();
      
      if (result.success && result.events_created > 0) {
        addToast({
          title: "Ajouté au calendrier",
          description: "La deadline a été synchronisée avec Google Calendar.",
          type: "success",
        });
        return true;
      }

      return false;
    } catch (error: any) {
      console.error("Failed to sync to calendar:", error);
      addToast({
        title: "Erreur",
        description: error.message || "Impossible de synchroniser avec le calendrier.",
        type: "error",
      });
      return false;
    }
  };

  const checkConnection = async (): Promise<boolean> => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return false;

      const response = await workspaceFetch(`${API_BASE}/api/v1/calendar/google/status`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        return data.connected;
      }
      return false;
    } catch {
      return false;
    }
  };

  return { syncToCalendar, checkConnection };
}
