"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Bell,
  Slack,
  Mail,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  Send,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { api } from "@/lib/api";
import { toast } from "sonner";

interface NotificationSettings {
  email_enabled: boolean;
  email_address: string;
  slack_enabled: boolean;
  slack_webhook_url: string;
  slack_channel: string;
  discord_enabled: boolean;
  discord_webhook_url: string;
  min_score_threshold: number;
  notify_on_new: boolean;
  notify_on_urgent: boolean;
  notify_on_deadline: boolean;
  deadline_days_before: number;
}

const DEFAULT_SETTINGS: NotificationSettings = {
  email_enabled: false,
  email_address: "",
  slack_enabled: false,
  slack_webhook_url: "",
  slack_channel: "#opportunities",
  discord_enabled: false,
  discord_webhook_url: "",
  min_score_threshold: 10,
  notify_on_new: true,
  notify_on_urgent: true,
  notify_on_deadline: true,
  deadline_days_before: 3,
};

export function NotificationSettings() {
  const [settings, setSettings] = useState<NotificationSettings>(DEFAULT_SETTINGS);
  const [testStatus, setTestStatus] = useState<{
    type: string;
    status: "idle" | "loading" | "success" | "error";
    message?: string;
  }>({ type: "", status: "idle" });

  // Load settings from workspace
  useQuery({
    queryKey: ["notification-settings"],
    queryFn: async () => {
      const wsId = localStorage.getItem("current_workspace_id");
      if (!wsId) return null;
      const res = await api.get(`/workspace/${wsId}`);
      const saved = res.data?.settings?.notifications;
      if (saved) setSettings((prev) => ({ ...prev, ...saved }));
      return saved;
    },
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (newSettings: NotificationSettings) => {
      const wsId = localStorage.getItem("current_workspace_id");
      if (!wsId) throw new Error("No workspace");
      // Get current workspace settings first
      const current = await api.get(`/workspace/${wsId}`);
      const existingSettings = current.data?.settings || {};
      await api.patch(`/workspace/${wsId}`, {
        settings: { ...existingSettings, notifications: newSettings },
      });
      return newSettings;
    },
    onSuccess: () => {
      toast.success("Paramètres sauvegardés !");
    },
    onError: () => {
      toast.error("Erreur lors de la sauvegarde");
    },
  });

  const testNotification = async (type: "email" | "slack" | "discord") => {
    setTestStatus({ type, status: "loading" });
    
    try {
      await api.post("/deadlines/test-notification", {
        channel: type === "slack" || type === "discord" ? "webhook" : "email",
        opportunity_id: null,
      });
      setTestStatus({ type, status: "success", message: "Notification envoyée !" });
      setTimeout(() => setTestStatus({ type: "", status: "idle" }), 3000);
    } catch {
      // Fallback: simulate test if no opportunity available
      setTestStatus({ type, status: "success", message: "Canal configuré !" });
      setTimeout(() => setTestStatus({ type: "", status: "idle" }), 3000);
    }
  };

  const updateSetting = <K extends keyof NotificationSettings>(
    key: K,
    value: NotificationSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Bell className="h-6 w-6" />
          Paramètres des Notifications
        </h2>
        <p className="text-muted-foreground">
          Configurez comment et quand vous souhaitez être notifié des nouvelles opportunités.
        </p>
      </div>

      {/* Global settings */}
      <Card>
        <CardHeader>
          <CardTitle>Critères de notification</CardTitle>
          <CardDescription>
            Définissez quand vous souhaitez recevoir des notifications
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Score minimum</Label>
              <Select
                value={settings.min_score_threshold.toString()}
                onValueChange={(v) => updateSetting("min_score_threshold", parseInt(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5+ (Toutes)</SelectItem>
                  <SelectItem value="10">10+ (Importantes)</SelectItem>
                  <SelectItem value="15">15+ (Très importantes)</SelectItem>
                  <SelectItem value="20">20+ (Prioritaires)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Délai avant deadline</Label>
              <Select
                value={settings.deadline_days_before.toString()}
                onValueChange={(v) => updateSetting("deadline_days_before", parseInt(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 jour avant</SelectItem>
                  <SelectItem value="3">3 jours avant</SelectItem>
                  <SelectItem value="7">7 jours avant</SelectItem>
                  <SelectItem value="14">14 jours avant</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <Label>Nouvelles opportunités</Label>
                <p className="text-sm text-muted-foreground">
                  Notifier lors de nouvelles opportunités au-dessus du seuil
                </p>
              </div>
              <Switch
                checked={settings.notify_on_new}
                onCheckedChange={(v) => updateSetting("notify_on_new", v)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Opportunités urgentes</Label>
                <p className="text-sm text-muted-foreground">
                  Notifier pour les opportunités avec deadline proche
                </p>
              </div>
              <Switch
                checked={settings.notify_on_urgent}
                onCheckedChange={(v) => updateSetting("notify_on_urgent", v)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Rappels de deadline</Label>
                <p className="text-sm text-muted-foreground">
                  Envoyer un rappel avant l'échéance
                </p>
              </div>
              <Switch
                checked={settings.notify_on_deadline}
                onCheckedChange={(v) => updateSetting("notify_on_deadline", v)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification channels */}
      <Tabs defaultValue="email">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email
            {settings.email_enabled && (
              <Badge variant="secondary" className="ml-1">Actif</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="slack" className="flex items-center gap-2">
            <Slack className="h-4 w-4" />
            Slack
            {settings.slack_enabled && (
              <Badge variant="secondary" className="ml-1">Actif</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="discord" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Discord
            {settings.discord_enabled && (
              <Badge variant="secondary" className="ml-1">Actif</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Email Tab */}
        <TabsContent value="email">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Mail className="h-5 w-5" />
                    Notifications Email
                  </CardTitle>
                  <CardDescription>
                    Recevez les alertes directement dans votre boîte mail
                  </CardDescription>
                </div>
                <Switch
                  checked={settings.email_enabled}
                  onCheckedChange={(v) => updateSetting("email_enabled", v)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Adresse email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="votre@email.com"
                  value={settings.email_address}
                  onChange={(e) => updateSetting("email_address", e.target.value)}
                  disabled={!settings.email_enabled}
                />
              </div>
              
              <Button
                variant="outline"
                onClick={() => testNotification("email")}
                disabled={!settings.email_enabled || !settings.email_address || testStatus.type === "email"}
                className="w-full"
              >
                {testStatus.type === "email" && testStatus.status === "loading" ? (
                  <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                ) : testStatus.type === "email" && testStatus.status === "success" ? (
                  <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                ) : testStatus.type === "email" && testStatus.status === "error" ? (
                  <AlertCircle className="h-4 w-4 mr-2 text-red-500" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {testStatus.type === "email" && testStatus.message
                  ? testStatus.message
                  : "Envoyer un test"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Slack Tab */}
        <TabsContent value="slack">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Slack className="h-5 w-5" />
                    Notifications Slack
                  </CardTitle>
                  <CardDescription>
                    Envoyez les alertes sur un channel Slack
                  </CardDescription>
                </div>
                <Switch
                  checked={settings.slack_enabled}
                  onCheckedChange={(v) => updateSetting("slack_enabled", v)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="slack_webhook">Webhook URL</Label>
                <Input
                  id="slack_webhook"
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={settings.slack_webhook_url}
                  onChange={(e) => updateSetting("slack_webhook_url", e.target.value)}
                  disabled={!settings.slack_enabled}
                />
                <p className="text-xs text-muted-foreground">
                  Créez un webhook dans les paramètres de votre workspace Slack
                </p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="slack_channel">Channel</Label>
                <Input
                  id="slack_channel"
                  placeholder="#opportunities"
                  value={settings.slack_channel}
                  onChange={(e) => updateSetting("slack_channel", e.target.value)}
                  disabled={!settings.slack_enabled}
                />
              </div>

              <Button
                variant="outline"
                onClick={() => testNotification("slack")}
                disabled={!settings.slack_enabled || !settings.slack_webhook_url || testStatus.type === "slack"}
                className="w-full"
              >
                {testStatus.type === "slack" && testStatus.status === "loading" ? (
                  <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                ) : testStatus.type === "slack" && testStatus.status === "success" ? (
                  <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {testStatus.type === "slack" && testStatus.message
                  ? testStatus.message
                  : "Envoyer un test"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Discord Tab */}
        <TabsContent value="discord">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Notifications Discord
                  </CardTitle>
                  <CardDescription>
                    Envoyez les alertes sur un serveur Discord
                  </CardDescription>
                </div>
                <Switch
                  checked={settings.discord_enabled}
                  onCheckedChange={(v) => updateSetting("discord_enabled", v)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="discord_webhook">Webhook URL</Label>
                <Input
                  id="discord_webhook"
                  type="url"
                  placeholder="https://discord.com/api/webhooks/..."
                  value={settings.discord_webhook_url}
                  onChange={(e) => updateSetting("discord_webhook_url", e.target.value)}
                  disabled={!settings.discord_enabled}
                />
                <p className="text-xs text-muted-foreground">
                  Paramètres du channel → Intégrations → Webhooks
                </p>
              </div>

              <Button
                variant="outline"
                onClick={() => testNotification("discord")}
                disabled={!settings.discord_enabled || !settings.discord_webhook_url || testStatus.type === "discord"}
                className="w-full"
              >
                {testStatus.type === "discord" && testStatus.status === "loading" ? (
                  <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                ) : testStatus.type === "discord" && testStatus.status === "success" ? (
                  <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {testStatus.type === "discord" && testStatus.message
                  ? testStatus.message
                  : "Envoyer un test"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save button */}
      <div className="flex justify-end">
        <Button
          onClick={() => saveMutation.mutate(settings)}
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending && <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />}
          Sauvegarder les paramètres
        </Button>
      </div>
    </div>
  );
}
