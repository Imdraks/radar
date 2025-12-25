"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import {
  ArrowLeft,
  ExternalLink,
  Mail,
  Phone,
  Calendar,
  Euro,
  MapPin,
  Building,
  Clock,
  Tag,
  FileText,
  CheckCircle,
  Circle,
  Plus,
  Send,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
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
import { opportunitiesApi, dossiersApi } from "@/lib/api";
import { DossierPanel } from "@/components/dossier/DossierPanel";
import { useAuthStore } from "@/store/auth";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatRelativeDate,
  getStatusColor,
  getStatusLabel,
  getCategoryLabel,
  getScoreColor,
  getScoreBgColor,
} from "@/lib/utils";
import type { Opportunity, OpportunityNote, OpportunityTask } from "@/lib/types";

const STATUS_OPTIONS = [
  { value: "new", label: "Nouveau" },
  { value: "to_qualify", label: "À qualifier" },
  { value: "qualified", label: "Qualifié" },
  { value: "in_progress", label: "En cours" },
  { value: "submitted", label: "Soumis" },
  { value: "won", label: "Gagné" },
  { value: "lost", label: "Perdu" },
  { value: "archived", label: "Archivé" },
];

function OpportunityDetailContent() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [noteContent, setNoteContent] = useState("");
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);

  const id = parseInt(params.id as string);

  const { data: opportunity, isLoading } = useQuery<Opportunity>({
    queryKey: ["opportunity", id],
    queryFn: () => opportunitiesApi.getOne(id),
  });

  const { data: notes } = useQuery<OpportunityNote[]>({
    queryKey: ["opportunity", id, "notes"],
    queryFn: () => opportunitiesApi.getNotes(id),
    enabled: !!opportunity,
  });

  const { data: tasks } = useQuery<OpportunityTask[]>({
    queryKey: ["opportunity", id, "tasks"],
    queryFn: () => opportunitiesApi.getTasks(id),
    enabled: !!opportunity,
  });

  // Update status mutation
  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      opportunitiesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunity", id] });
    },
  });

  // Add note mutation
  const addNoteMutation = useMutation({
    mutationFn: (content: string) =>
      opportunitiesApi.addNote(id, { content, is_internal: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunity", id, "notes"] });
      setNoteContent("");
    },
  });

  // Add task mutation
  const addTaskMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      opportunitiesApi.addTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunity", id, "tasks"] });
      setTaskDialogOpen(false);
    },
  });

  // Toggle task mutation
  const toggleTaskMutation = useMutation({
    mutationFn: ({ taskId, is_completed }: { taskId: number; is_completed: boolean }) =>
      opportunitiesApi.updateTask(id, taskId, { is_completed }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunity", id, "tasks"] });
    },
  });

  const handleStatusChange = (status: string) => {
    updateMutation.mutate({ status });
  };

  const handleAddNote = () => {
    if (noteContent.trim()) {
      addNoteMutation.mutate(noteContent);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  if (!opportunity) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Opportunité non trouvée</p>
        <Button className="mt-4" onClick={() => router.push("/opportunities")}>
          Retour à la liste
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Button variant="ghost" onClick={() => router.push("/opportunities")}>
        <ArrowLeft className="h-4 w-4 mr-2" />
        Retour
      </Button>

      {/* Header */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main info */}
        <div className="flex-1">
          <div className="flex items-start gap-4">
            {/* Score */}
            <div
              className={`flex-shrink-0 w-20 h-20 rounded-xl flex flex-col items-center justify-center ${getScoreBgColor(
                opportunity.score
              )}`}
            >
              <span className={`text-3xl font-bold ${getScoreColor(opportunity.score)}`}>
                {opportunity.score?.toFixed(0) || 0}
              </span>
              <span className="text-xs text-muted-foreground">score</span>
            </div>

            <div className="flex-1">
              <h1 className="text-2xl font-bold">{opportunity.title}</h1>
              
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {/* Status dropdown */}
                <Select
                  value={opportunity.status}
                  onValueChange={handleStatusChange}
                >
                  <SelectTrigger className="w-[150px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {opportunity.category && (
                  <Badge variant="outline">
                    <Tag className="h-3 w-3 mr-1" />
                    {getCategoryLabel(opportunity.category)}
                  </Badge>
                )}

                <Badge variant="secondary">
                  {opportunity.source_type.toUpperCase()}
                </Badge>

                {opportunity.url_primary && (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={opportunity.url_primary}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLink className="h-4 w-4 mr-1" />
                      Voir la source
                    </a>
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Quick info cards */}
        <div className="flex flex-wrap gap-4 lg:w-auto">
          {opportunity.budget_amount && (
            <Card className="flex-1 min-w-[150px]">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Euro className="h-4 w-4" />
                  Budget
                </div>
                <p className="text-xl font-bold text-green-600 mt-1">
                  {formatCurrency(opportunity.budget_amount)}
                </p>
              </CardContent>
            </Card>
          )}

          {opportunity.deadline_at && (
            <Card className="flex-1 min-w-[150px]">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Clock className="h-4 w-4" />
                  Deadline
                </div>
                <p className="text-xl font-bold text-orange-600 mt-1">
                  {formatRelativeDate(opportunity.deadline_at)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(opportunity.deadline_at)}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="details" className="space-y-4">
        <TabsList>
          <TabsTrigger value="details">Détails</TabsTrigger>
          <TabsTrigger value="dossier">
            Dossier IA
          </TabsTrigger>
          <TabsTrigger value="notes">
            Notes ({notes?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="tasks">
            Tâches ({tasks?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="score">Score</TabsTrigger>
        </TabsList>

        {/* Details Tab */}
        <TabsContent value="details" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Description */}
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">
                  {opportunity.description || "Aucune description"}
                </p>
              </CardContent>
            </Card>

            {/* Info */}
            <Card>
              <CardHeader>
                <CardTitle>Informations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {opportunity.organization_name && (
                  <div className="flex items-center gap-2">
                    <Building className="h-4 w-4 text-muted-foreground" />
                    <span>{opportunity.organization_name}</span>
                  </div>
                )}
                {opportunity.region && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span>{opportunity.region}</span>
                  </div>
                )}
                {opportunity.event_date_start && (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>
                      Événement: {formatDate(opportunity.event_date_start)}
                      {opportunity.event_date_end &&
                        ` - ${formatDate(opportunity.event_date_end)}`}
                    </span>
                  </div>
                )}
                {opportunity.contact_email && (
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <a
                      href={`mailto:${opportunity.contact_email}`}
                      className="text-primary hover:underline"
                    >
                      {opportunity.contact_email}
                    </a>
                  </div>
                )}
                {opportunity.contact_phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <a
                      href={`tel:${opportunity.contact_phone}`}
                      className="text-primary hover:underline"
                    >
                      {opportunity.contact_phone}
                    </a>
                  </div>
                )}
                {opportunity.contact_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Contact:</span>
                    <span>{opportunity.contact_name}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Raw content */}
          {opportunity.raw_content && (
            <Card>
              <CardHeader>
                <CardTitle>Contenu brut</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[300px]">
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {opportunity.raw_content}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Notes Tab */}
        <TabsContent value="notes" className="space-y-4">

        {/* Dossier IA Tab */}
        <TabsContent value="dossier" className="space-y-4">
          <DossierPanel
            opportunityId={id.toString()}
            opportunityTitle={opportunity.title}
          />
        </TabsContent>

        {/* Notes Tab */}
        <TabsContent value="notes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ajouter une note</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  placeholder="Votre note..."
                  value={noteContent}
                  onChange={(e) => setNoteContent(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddNote()}
                />
                <Button onClick={handleAddNote} disabled={addNoteMutation.isPending}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-3">
            {notes?.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                Aucune note pour le moment
              </p>
            ) : (
              notes?.map((note) => (
                <Card key={note.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium">
                          {note.author?.full_name || note.author?.email}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDateTime(note.created_at)}
                        </p>
                      </div>
                      {note.is_internal && (
                        <Badge variant="secondary">Interne</Badge>
                      )}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap">{note.content}</p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Tasks Tab */}
        <TabsContent value="tasks" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={taskDialogOpen} onOpenChange={setTaskDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Nouvelle tâche
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Nouvelle tâche</DialogTitle>
                </DialogHeader>
                <TaskForm
                  onSubmit={(data) => addTaskMutation.mutate(data)}
                  isLoading={addTaskMutation.isPending}
                />
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-3">
            {tasks?.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                Aucune tâche pour le moment
              </p>
            ) : (
              tasks?.map((task) => (
                <Card key={task.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() =>
                          toggleTaskMutation.mutate({
                            taskId: task.id,
                            is_completed: !task.is_completed,
                          })
                        }
                        className="mt-1"
                      >
                        {task.is_completed ? (
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        ) : (
                          <Circle className="h-5 w-5 text-muted-foreground" />
                        )}
                      </button>
                      <div className="flex-1">
                        <p
                          className={`font-medium ${
                            task.is_completed ? "line-through text-muted-foreground" : ""
                          }`}
                        >
                          {task.title}
                        </p>
                        {task.description && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {task.description}
                          </p>
                        )}
                        {task.due_at && (
                          <p className="text-xs text-orange-600 mt-1">
                            <Clock className="h-3 w-3 inline mr-1" />
                            {formatRelativeDate(task.due_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Score Tab */}
        <TabsContent value="score">
          <Card>
            <CardHeader>
              <CardTitle>Détail du score</CardTitle>
            </CardHeader>
            <CardContent>
              {opportunity.score_breakdown?.length ? (
                <div className="space-y-2">
                  {opportunity.score_breakdown.map((item, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 rounded bg-muted"
                    >
                      <span>{item.label}</span>
                      <span
                        className={`font-medium ${
                          item.points > 0 ? "text-green-600" : "text-red-600"
                        }`}
                      >
                        {item.points > 0 ? "+" : ""}
                        {item.points}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between p-2 rounded bg-primary/10 font-bold">
                    <span>Total</span>
                    <span className={getScoreColor(opportunity.score)}>
                      {opportunity.score?.toFixed(0) || 0}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground">
                  Aucun détail de score disponible
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Historique</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-2 h-2 mt-2 rounded-full bg-primary" />
              <div>
                <p className="font-medium">Opportunité créée</p>
                <p className="text-sm text-muted-foreground">
                  {formatDateTime(opportunity.created_at)}
                </p>
              </div>
            </div>
            {opportunity.ingested_at !== opportunity.created_at && (
              <div className="flex gap-3">
                <div className="w-2 h-2 mt-2 rounded-full bg-blue-500" />
                <div>
                  <p className="font-medium">Ingérée</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDateTime(opportunity.ingested_at)}
                  </p>
                </div>
              </div>
            )}
            {opportunity.updated_at && opportunity.updated_at !== opportunity.created_at && (
              <div className="flex gap-3">
                <div className="w-2 h-2 mt-2 rounded-full bg-yellow-500" />
                <div>
                  <p className="font-medium">Dernière mise à jour</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDateTime(opportunity.updated_at)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TaskForm({
  onSubmit,
  isLoading,
}: {
  onSubmit: (data: Record<string, unknown>) => void;
  isLoading: boolean;
}) {
  const { register, handleSubmit } = useForm();

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Titre</Label>
        <Input id="title" {...register("title", { required: true })} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input id="description" {...register("description")} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="due_at">Date limite</Label>
        <Input id="due_at" type="datetime-local" {...register("due_at")} />
      </div>
      <DialogFooter>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Création..." : "Créer la tâche"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function OpportunityDetailPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <OpportunityDetailContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
