"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Calendar, ChevronLeft, ChevronRight, ExternalLink, Loader2, CheckCircle } from "lucide-react";

// Google Calendar API types
interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: { dateTime?: string; date?: string };
  end: { dateTime?: string; date?: string };
  htmlLink: string;
}

interface Opportunity {
  id: string;
  title: string;
  organization?: string;
  deadline_at?: string;
  description?: string;
}

const STORAGE_KEY = "google_calendar_config";
const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export function GoogleCalendarIntegration() {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoSync, setAutoSync] = useState(true);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [selectedCalendar, setSelectedCalendar] = useState("primary");
  const [reminderMinutes, setReminderMinutes] = useState(60);

  // Load config from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const config = JSON.parse(stored);
        setIsConnected(config.isConnected || false);
        setAutoSync(config.autoSync ?? true);
        setSelectedCalendar(config.selectedCalendar || "primary");
        setReminderMinutes(config.reminderMinutes || 60);
      } catch (e) {
        console.error("Failed to parse calendar config:", e);
      }
    }
  }, []);

  // Save config to localStorage
  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        isConnected,
        autoSync,
        selectedCalendar,
        reminderMinutes,
      })
    );
  }, [isConnected, autoSync, selectedCalendar, reminderMinutes]);

  const handleConnect = async () => {
    setIsLoading(true);

    // In a real implementation, this would use Google OAuth
    // For demo, we simulate the connection
    try {
      // Simulate OAuth flow
      await new Promise((resolve) => setTimeout(resolve, 1500));
      
      setIsConnected(true);
      
      // Load some sample events
      setEvents([
        {
          id: "1",
          summary: "Deadline: Appel d'offres Festival",
          start: { dateTime: new Date(Date.now() + 86400000 * 3).toISOString() },
          end: { dateTime: new Date(Date.now() + 86400000 * 3 + 3600000).toISOString() },
          htmlLink: "https://calendar.google.com",
        },
        {
          id: "2",
          summary: "Deadline: Concert Mairie Paris",
          start: { dateTime: new Date(Date.now() + 86400000 * 7).toISOString() },
          end: { dateTime: new Date(Date.now() + 86400000 * 7 + 3600000).toISOString() },
          htmlLink: "https://calendar.google.com",
        },
      ]);
    } catch (error) {
      console.error("Failed to connect to Google Calendar:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    setIsConnected(false);
    setEvents([]);
  };

  const handleSyncOpportunity = async (opportunity: Opportunity) => {
    if (!isConnected || !opportunity.deadline_at) return;

    setIsLoading(true);
    try {
      // Simulate creating calendar event
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const newEvent: CalendarEvent = {
        id: opportunity.id,
        summary: `Deadline: ${opportunity.title}`,
        description: `Organisation: ${opportunity.organization || "N/A"}`,
        start: { dateTime: opportunity.deadline_at },
        end: {
          dateTime: new Date(
            new Date(opportunity.deadline_at).getTime() + 3600000
          ).toISOString(),
        },
        htmlLink: "https://calendar.google.com",
      };

      setEvents((prev) => [...prev.filter((e) => e.id !== opportunity.id), newEvent]);
      setSyncSuccess(true);
      setTimeout(() => setSyncSuccess(false), 3000);
    } catch (error) {
      console.error("Failed to sync opportunity:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncAllDeadlines = async () => {
    setIsLoading(true);
    try {
      // Simulate syncing all deadlines
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setSyncSuccess(true);
      setTimeout(() => setSyncSuccess(false), 3000);
    } catch (error) {
      console.error("Failed to sync all deadlines:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatEventDate = (event: CalendarEvent) => {
    const dateStr = event.start.dateTime || event.start.date;
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      weekday: "long",
      day: "numeric",
      month: "long",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

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
                isConnected ? "bg-green-100" : "bg-gray-100"
              }`}
            >
              <Calendar
                className={`h-5 w-5 ${
                  isConnected ? "text-green-600" : "text-gray-400"
                }`}
              />
            </div>
            <div>
              <p className="font-medium">
                {isConnected ? "Connecté à Google Calendar" : "Non connecté"}
              </p>
              <p className="text-sm text-muted-foreground">
                {isConnected
                  ? `Calendrier: ${selectedCalendar}`
                  : "Connectez-vous pour synchroniser les deadlines"}
              </p>
            </div>
          </div>
          <Button
            variant={isConnected ? "outline" : "default"}
            onClick={isConnected ? handleDisconnect : handleConnect}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            {isConnected ? "Déconnecter" : "Connecter"}
          </Button>
        </div>

        {isConnected && (
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
            <div className="flex gap-2">
              <Button
                onClick={handleSyncAllDeadlines}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : syncSuccess ? (
                  <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                ) : (
                  <Calendar className="h-4 w-4 mr-2" />
                )}
                {syncSuccess ? "Synchronisé !" : "Synchroniser toutes les deadlines"}
              </Button>
            </div>

            {/* Upcoming events */}
            <div className="space-y-2">
              <h4 className="font-medium">Événements à venir</h4>
              {events.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  Aucun événement synchronisé
                </p>
              ) : (
                <div className="space-y-2">
                  {events.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-sm">{event.summary}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatEventDate(event)}
                        </p>
                      </div>
                      <a
                        href={event.htmlLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                  ))}
                </div>
              )}
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

// Hook for syncing opportunities to calendar
export function useGoogleCalendar() {
  const syncToCalendar = async (opportunity: Opportunity) => {
    // TODO: Implement Google Calendar API integration
    // For now, this is a placeholder
  };

  return { syncToCalendar };
}
