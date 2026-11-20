"use client";

import { RadarSpinner } from '@/components/ui/radar-loader';
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import {
  Plus,
  Rss,
  Globe,
  Mail,
  Code,
  MoreVertical,
  Pencil,
  Trash,
  Play,
  RefreshCw,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { sourcesApi, ingestionApi } from "@/lib/api";
import { formatDateTime, formatRelativeDate } from "@/lib/utils";
import type { SourceConfig, SourceType } from "@/lib/types";

const SOURCE_TYPE_ICONS = {
  rss: Rss,
  html: Globe,
  email: Mail,
  api: Code,
};

function SourcesContent() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<SourceConfig | null>(null);

  const { data: sources, isLoading } = useQuery<SourceConfig[]>({
    queryKey: ["sources"],
    queryFn: () => sourcesApi.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<SourceConfig>) => sourcesApi.create(data as Record<string, unknown>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setDialogOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<SourceConfig> }) =>
      sourcesApi.update(id, data as Record<string, unknown>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setDialogOpen(false);
      setEditingSource(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => sourcesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });

  const triggerMutation = useMutation({
    mutationFn: (id: number) => ingestionApi.trigger(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => sourcesApi.test(id),
  });

  const handleSubmit = (data: Partial<SourceConfig>) => {
    if (editingSource) {
      updateMutation.mutate({ id: editingSource.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (source: SourceConfig) => {
    setEditingSource(source);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingSource(null);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setEditingSource(null);
    }
    setDialogOpen(open);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Sources</h1>
          <p className="text-muted-foreground">
            Gérez vos sources de collecte d&apos;opportunités
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={handleOpenChange}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouvelle source
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {editingSource ? "Modifier la source" : "Nouvelle source"}
              </DialogTitle>
            </DialogHeader>
            <SourceForm
              source={editingSource}
              onSubmit={handleSubmit}
              isLoading={createMutation.isPending || updateMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Sources list */}
      {isLoading ? (
        <div className="text-center py-12">
          <RadarSpinner className="h-12 w-12 text-primary mx-auto" />
        </div>
      ) : sources?.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Aucune source configurée
        </div>
      ) : (
        <div className="grid gap-4">
          {sources?.map((source) => {
            const Icon = SOURCE_TYPE_ICONS[source.source_type] || Globe;
            return (
              <Card key={source.id}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold">{source.name}</h3>
                          <p className="text-sm text-muted-foreground">
                            {source.description || source.url || source.email_folder}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={source.is_active ? "default" : "secondary"}>
                            {source.is_active ? "Actif" : "Inactif"}
                          </Badge>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleEdit(source)}>
                                <Pencil className="h-4 w-4 mr-2" />
                                Modifier
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => triggerMutation.mutate(source.id)}
                              >
                                <Play className="h-4 w-4 mr-2" />
                                Lancer la collecte
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => testMutation.mutate(source.id)}
                              >
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Tester
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => deleteMutation.mutate(source.id)}
                              >
                                <Trash className="h-4 w-4 mr-2" />
                                Supprimer
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <Badge variant="outline">
                          {source.source_type.toUpperCase()}
                        </Badge>
                        <span>Intervalle: {source.poll_interval_minutes} min</span>
                        {source.last_polled_at && (
                          <span>
                            Dernière collecte: {formatRelativeDate(source.last_polled_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SourceForm({
  source,
  onSubmit,
  isLoading,
}: {
  source: SourceConfig | null;
  onSubmit: (data: Partial<SourceConfig>) => void;
  isLoading: boolean;
}) {
  const { register, handleSubmit, watch, setValue } = useForm<Partial<SourceConfig>>({
    defaultValues: source || {
      name: "",
      source_type: "rss",
      description: "",
      url: "",
      email_folder: "INBOX",
      poll_interval_minutes: 60,
      is_active: true,
    },
  });

  const sourceType = watch("source_type");

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Nom</Label>
          <Input id="name" {...register("name", { required: true })} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="source_type">Type</Label>
          <Select
            value={sourceType}
            onValueChange={(v) => setValue("source_type", v as SourceType)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="rss">RSS</SelectItem>
              <SelectItem value="html">HTML</SelectItem>
              <SelectItem value="api">API</SelectItem>
              <SelectItem value="email">Email</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input id="description" {...register("description")} />
      </div>

      {sourceType !== "email" && (
        <div className="space-y-2">
          <Label htmlFor="url">URL</Label>
          <Input id="url" type="url" {...register("url")} />
        </div>
      )}

      {sourceType === "email" && (
        <div className="space-y-2">
          <Label htmlFor="email_folder">Dossier email</Label>
          <Input id="email_folder" {...register("email_folder")} />
        </div>
      )}

      {sourceType === "html" && (
        <div className="space-y-4 border rounded-lg p-4">
          <h4 className="font-medium">Sélecteurs CSS</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Liste</Label>
              <Input {...register("css_selector_list")} placeholder=".opportunities" />
            </div>
            <div className="space-y-2">
              <Label>Item</Label>
              <Input {...register("css_selector_item")} placeholder=".opportunity-item" />
            </div>
            <div className="space-y-2">
              <Label>Titre</Label>
              <Input {...register("css_selector_title")} placeholder="h2, .title" />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input {...register("css_selector_description")} placeholder="p, .description" />
            </div>
            <div className="space-y-2">
              <Label>Lien</Label>
              <Input {...register("css_selector_link")} placeholder="a" />
            </div>
            <div className="space-y-2">
              <Label>Date</Label>
              <Input {...register("css_selector_date")} placeholder=".date, time" />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="poll_interval_minutes">Intervalle (minutes)</Label>
          <Input
            id="poll_interval_minutes"
            type="number"
            min={1}
            {...register("poll_interval_minutes", { valueAsNumber: true })}
          />
        </div>
        <div className="flex items-center gap-2 pt-8">
          <Switch
            id="is_active"
            checked={watch("is_active")}
            onCheckedChange={(v) => setValue("is_active", v)}
          />
          <Label htmlFor="is_active">Source active</Label>
        </div>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Enregistrement..." : source ? "Modifier" : "Créer"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function SourcesPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <SourcesContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
