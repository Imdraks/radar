"use client";

import React, { useState, useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import {
  ArrowLeft,
  Folder,
  FileText,
  Plus,
  ExternalLink,
  Clock,
  AlertCircle,
  CheckCircle,
  MoreHorizontal,
  Calendar,
  User,
  AlertTriangle,
  ChevronRight,
  FileSpreadsheet,
  Play,
  Pause,
  Check,
  Edit,
  Trash2,
  Send,
  GripVertical,
  Link,
  RefreshCw,
  Upload,
  FolderOpen,
  X,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  projectDetailApi,
  ProjectDetail,
  ProjectOverview,
  ProjectDeliverable,
  ProjectTask,
  ProjectAsset,
  googleWorkspaceApi,
  projectDriveApi,
  DriveFolderInfo,
} from "@/lib/api";
import { ProductionConnections } from "@/components/production-tools";
import { toast } from "sonner";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";

// ============================================================================
// STATUS BADGES
// ============================================================================

const projectStatusConfig = {
  active: { label: "Actif", color: "bg-green-100 text-green-700 border-green-300" },
  blocked: { label: "Bloqué", color: "bg-red-100 text-red-700 border-red-300" },
  delivered: { label: "Livré", color: "bg-blue-100 text-blue-700 border-blue-300" },
  archived: { label: "Archivé", color: "bg-gray-100 text-gray-700 border-gray-300" },
};

const deliverableStatusConfig = {
  draft: { label: "Brouillon", color: "bg-gray-100 text-gray-700" },
  to_review: { label: "À valider", color: "bg-yellow-100 text-yellow-700" },
  changes_requested: { label: "Modifs", color: "bg-orange-100 text-orange-700" },
  approved: { label: "Validé", color: "bg-green-100 text-green-700" },
  delivered: { label: "Livré", color: "bg-blue-100 text-blue-700" },
};

const taskStatusConfig = {
  todo: { label: "À faire", color: "bg-gray-100 text-gray-700" },
  doing: { label: "En cours", color: "bg-blue-100 text-blue-700" },
  done: { label: "Terminé", color: "bg-green-100 text-green-700" },
};

const priorityConfig = {
  low: { label: "Basse", color: "text-gray-500" },
  medium: { label: "Moyenne", color: "text-yellow-600" },
  high: { label: "Haute", color: "text-red-600" },
};

// ============================================================================
// HEADER COMPONENT
// ============================================================================

function ProjectHeader({
  project,
  onAddTask,
  onAddDeliverable,
  onOpenDrive,
  onCreateBrief,
  isCreatingDrive,
  isCreatingBrief,
}: {
  project: ProjectDetail;
  onAddTask: () => void;
  onAddDeliverable: () => void;
  onOpenDrive: () => void;
  onCreateBrief: () => void;
  isCreatingDrive?: boolean;
  isCreatingBrief?: boolean;
}) {
  const router = useRouter();
  const status = projectStatusConfig[project.status] || projectStatusConfig.active;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6 shadow-sm">
      {/* Top row */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/projects")}
            className="text-gray-500 hover:text-gray-900 -ml-2"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Retour
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              {project.client_name && (
                <span className="text-gray-500">{project.client_name}</span>
              )}
              <Badge className={`${status.color} border`}>{status.label}</Badge>
              {project.is_urgent && (
                <Badge className="bg-red-50 text-red-600 border border-red-200">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Urgent
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onAddTask}
          >
            <Plus className="h-4 w-4 mr-1" />
            Tâche
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onAddDeliverable}
          >
            <Plus className="h-4 w-4 mr-1" />
            Livrable
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenDrive}
            disabled={isCreatingDrive}
          >
            {isCreatingDrive ? (
              <RadarSpinner className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Folder className="h-4 w-4 mr-1" />
            )}
            {project.drive_folder_id ? "Drive" : "Créer Drive"}
          </Button>
          {!project.brief_doc_id && (
            <Button
              size="sm"
              onClick={onCreateBrief}
              disabled={isCreatingBrief}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              {isCreatingBrief ? (
                <RadarSpinner className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <FileText className="h-4 w-4 mr-1" />
              )}
              Créer brief
            </Button>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
        {/* Deadline */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Calendar className="h-4 w-4" />
            Deadline
          </div>
          <div className="text-gray-900 font-medium">
            {project.deadline
              ? format(new Date(project.deadline), "dd MMM yyyy", { locale: fr })
              : "Non définie"}
          </div>
          {project.days_until_deadline !== null && (
            <div className={`text-xs ${project.days_until_deadline <= 3 ? "text-red-500" : "text-gray-400"}`}>
              {project.days_until_deadline > 0
                ? `Dans ${project.days_until_deadline} jours`
                : project.days_until_deadline === 0
                ? "Aujourd'hui"
                : `Dépassée de ${Math.abs(project.days_until_deadline)} jours`}
            </div>
          )}
        </div>

        {/* Owner */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <User className="h-4 w-4" />
            Owner
          </div>
          <div className="text-gray-900 font-medium">
            {project.owner_name || "Non assigné"}
          </div>
        </div>

        {/* Progress */}
        <div className="bg-gray-50 rounded-lg p-3">
          {project.deliverables_total === 0 ? (
            <>
              <div className="text-sm text-gray-500 mb-2">Aucun livrable défini</div>
              <Progress value={0} className="h-2 opacity-50" />
              <Button
                size="sm"
                variant="outline"
                className="mt-2 text-xs w-full border-purple-300 text-purple-600 hover:bg-purple-50"
                onClick={onAddDeliverable}
              >
                <Plus className="h-3 w-3 mr-1" />
                Créer un livrable
              </Button>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between text-gray-500 text-sm mb-1">
                <span>Progression</span>
                <span className={`font-medium ${
                  project.progress_percent === 100 ? 'text-green-600' :
                  project.progress_percent >= 70 ? 'text-orange-500' :
                  project.progress_percent >= 30 ? 'text-blue-600' :
                  'text-gray-600'
                }`}>
                  {project.progress_percent}%
                </span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    project.progress_percent === 100 ? 'bg-green-500' :
                    project.progress_percent >= 70 ? 'bg-orange-500' :
                    project.progress_percent >= 30 ? 'bg-blue-500' :
                    'bg-gray-400'
                  }`}
                  style={{ width: `${project.progress_percent}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {project.deliverables_approved} / {project.deliverables_total} livrables validés
              </div>
            </>
          )}
        </div>

        {/* Tasks */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <CheckCircle className="h-4 w-4" />
            Tâches
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500 text-sm">{project.tasks_todo}</span>
            <span className="text-blue-500 text-sm">{project.tasks_doing}</span>
            <span className="text-green-500 text-sm">{project.tasks_done}</span>
          </div>
          <div className="text-xs text-gray-400">Todo • Doing • Done</div>
        </div>

        {/* Validations */}
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Clock className="h-4 w-4" />
            Validations
          </div>
          <div className={`text-xl font-bold ${project.pending_validations > 0 ? "text-yellow-500" : "text-green-500"}`}>
            {project.pending_validations}
          </div>
          <div className="text-xs text-gray-400">en attente</div>
        </div>
      </div>

      {/* Blocked reason */}
      {project.status === "blocked" && project.blocked_reason && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-red-700 font-medium">Projet bloqué</div>
            <div className="text-red-600 text-sm">{project.blocked_reason}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// OVERVIEW TAB
// ============================================================================

function OverviewTab({
  projectId,
  project,
}: {
  projectId: number;
  project: ProjectDetail;
}) {
  const { data: overview, isLoading } = useQuery({
    queryKey: ["project-overview", projectId],
    queryFn: () => projectDetailApi.getOverview(projectId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left column */}
      <div className="space-y-6">
        {/* Next Action */}
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
              <ChevronRight className="h-5 w-5 text-purple-500" />
              Prochaine action
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview?.next_action_text ? (
              <div>
                <p className="text-gray-900">{overview.next_action_text}</p>
                {overview.next_action_due_date && (
                  <p className="text-sm text-gray-500 mt-1">
                    Pour le {format(new Date(overview.next_action_due_date), "dd MMM yyyy", { locale: fr })}
                  </p>
                )}
              </div>
            ) : (
              <div className="text-gray-400 italic">
                Aucune action définie.{" "}
                <button className="text-purple-500 hover:underline">Définir</button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Today's Tasks */}
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-500" />
              À faire aujourd'hui
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview?.today_tasks && overview.today_tasks.length > 0 ? (
              <div className="space-y-2">
                {overview.today_tasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <span className={priorityConfig[task.priority as keyof typeof priorityConfig]?.color || "text-gray-400"}>●</span>
                      <span className="text-gray-900">{task.title}</span>
                    </div>
                    <Badge className={taskStatusConfig[task.status as keyof typeof taskStatusConfig]?.color || ""}>
                      {taskStatusConfig[task.status as keyof typeof taskStatusConfig]?.label || task.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 italic">Aucune tâche pour aujourd'hui</div>
            )}
          </CardContent>
        </Card>

        {/* Pending Validations */}
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-500" />
              Validations en attente
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview?.pending_validations && overview.pending_validations.length > 0 ? (
              <div className="space-y-2">
                {overview.pending_validations.map((v) => (
                  <div
                    key={v.id}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
                  >
                    <span className="text-gray-900">{v.deliverable_name}</span>
                    <Button size="sm" variant="outline" className="border-yellow-500 text-yellow-600 hover:bg-yellow-50">
                      Valider
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-green-500 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Aucune validation en attente
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Right column - Timeline */}
      <Card className="bg-white border-gray-200 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-gray-500" />
            Activité récente
          </CardTitle>
        </CardHeader>
        <CardContent>
          {overview?.recent_activity && overview.recent_activity.length > 0 ? (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {overview.recent_activity.map((activity) => (
                <div key={activity.id} className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-gray-700">{activity.message}</p>
                    <div className="flex items-center gap-2 text-gray-400 text-xs mt-1">
                      <span>{format(new Date(activity.created_at), "dd MMM HH:mm", { locale: fr })}</span>
                      {activity.created_by_name && <span>• {activity.created_by_name}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-400 italic">Aucune activité récente</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// DELIVERABLES TAB
// ============================================================================

function DeliverablesTab({
  projectId,
  onAddDeliverable,
}: {
  projectId: number;
  onAddDeliverable: () => void;
}) {
  const queryClient = useQueryClient();

  const { data: deliverables = [], isLoading } = useQuery({
    queryKey: ["project-deliverables", projectId],
    queryFn: () => projectDetailApi.getDeliverables(projectId),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ProjectDeliverable> }) =>
      projectDetailApi.updateDeliverable(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-deliverables", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      toast.success("Livrable mis à jour");
    },
  });

  const requestValidationMutation = useMutation({
    mutationFn: (id: number) => projectDetailApi.requestValidation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-deliverables", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      toast.success("Validation demandée");
    },
  });

  const approveMutation = useMutation({
    mutationFn: (id: number) => projectDetailApi.approveDeliverable(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-deliverables", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      toast.success("Livrable validé");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => projectDetailApi.deleteDeliverable(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-deliverables", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      toast.success("Livrable supprimé");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (deliverables.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-xl font-medium text-gray-900 mb-2">Aucun livrable</h3>
        <p className="text-gray-500 mb-4">Créez votre premier livrable pour ce projet</p>
        <Button onClick={onAddDeliverable} className="bg-purple-600 hover:bg-purple-700">
          <Plus className="h-4 w-4 mr-2" />
          Créer un livrable
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={onAddDeliverable} size="sm" className="bg-purple-600 hover:bg-purple-700">
          <Plus className="h-4 w-4 mr-2" />
          Ajouter
        </Button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left p-4 text-gray-600 font-medium">Nom</th>
              <th className="text-left p-4 text-gray-600 font-medium">Type</th>
              <th className="text-left p-4 text-gray-600 font-medium">Statut</th>
              <th className="text-left p-4 text-gray-600 font-medium">Due date</th>
              <th className="text-left p-4 text-gray-600 font-medium">Lien</th>
              <th className="text-right p-4 text-gray-600 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {deliverables.map((d) => {
              const statusConf = deliverableStatusConfig[d.status as keyof typeof deliverableStatusConfig];
              return (
                <tr key={d.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="p-4 text-gray-900 font-medium">{d.name}</td>
                  <td className="p-4 text-gray-500">{d.type || "-"}</td>
                  <td className="p-4">
                    <Badge className={statusConf?.color || "bg-gray-100 text-gray-500"}>
                      {statusConf?.label || d.status}
                    </Badge>
                  </td>
                  <td className="p-4 text-gray-500">
                    {d.due_date
                      ? format(new Date(d.due_date), "dd MMM", { locale: fr })
                      : "-"}
                    {d.days_until_due !== null && d.days_until_due <= 3 && d.days_until_due >= 0 && (
                      <span className="text-red-500 text-xs ml-1">
                        ({d.days_until_due === 0 ? "Aujourd'hui" : `${d.days_until_due}j`})
                      </span>
                    )}
                  </td>
                  <td className="p-4">
                    {d.link || d.drive_file_id ? (
                      <a
                        href={d.link || `https://drive.google.com/file/d/${d.drive_file_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline flex items-center gap-1"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Ouvrir
                      </a>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {d.status === "draft" && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => requestValidationMutation.mutate(d.id)}
                          className="border-yellow-500 text-yellow-600 hover:bg-yellow-50"
                        >
                          <Send className="h-3 w-3 mr-1" />
                          Validation
                        </Button>
                      )}
                      {d.status === "to_review" && (
                        <Button
                          size="sm"
                          onClick={() => approveMutation.mutate(d.id)}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          <Check className="h-3 w-3 mr-1" />
                          Valider
                        </Button>
                      )}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-red-500"
                            onClick={() => deleteMutation.mutate(d.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Supprimer
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================================
// PRODUCTION TAB (KANBAN)
// ============================================================================

function ProductionTab({
  projectId,
  onAddTask,
}: {
  projectId: number;
  onAddTask: () => void;
}) {
  const queryClient = useQueryClient();

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["project-tasks", projectId],
    queryFn: () => projectDetailApi.getTasks(projectId),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ProjectTask> }) =>
      projectDetailApi.updateTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => projectDetailApi.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      toast.success("Tâche supprimée");
    },
  });

  const columns = [
    { id: "todo", label: "À faire", iconName: "play" as const, color: "border-gray-500" },
    { id: "doing", label: "En cours", iconName: "pause" as const, color: "border-blue-500" },
    { id: "done", label: "Terminé", iconName: "check" as const, color: "border-green-500" },
  ];

  const getColumnIcon = (iconName: string) => {
    switch (iconName) {
      case "play": return <Play className="h-4 w-4" />;
      case "pause": return <Pause className="h-4 w-4" />;
      case "check": return <Check className="h-4 w-4" />;
      default: return null;
    }
  };

  const moveTask = (taskId: number, newStatus: string) => {
    updateMutation.mutate({ id: taskId, data: { status: newStatus } });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={onAddTask} size="sm" className="bg-purple-600 hover:bg-purple-700">
          <Plus className="h-4 w-4 mr-2" />
          Ajouter
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {columns.map((column) => {
          const columnTasks = tasks.filter((t) => t.status === column.id);
          return (
            <div
              key={column.id}
              className={`bg-white border-t-4 ${column.color} border-x border-b border-gray-200 rounded-lg p-4 shadow-sm`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-gray-900 font-medium">
                  {getColumnIcon(column.iconName)}
                  {column.label}
                </div>
                <Badge variant="secondary">{columnTasks.length}</Badge>
              </div>

              <div className="space-y-2">
                {columnTasks.map((task) => (
                  <div
                    key={task.id}
                    className="bg-gray-50 border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={priorityConfig[task.priority as keyof typeof priorityConfig]?.color || "text-gray-400"}>●</span>
                          <span className="text-gray-900 font-medium text-sm">{task.title}</span>
                        </div>
                        {task.description && (
                          <p className="text-gray-400 text-xs mt-1 line-clamp-2">{task.description}</p>
                        )}
                        <div className="flex items-center gap-2 mt-2">
                          {task.assignee_name && (
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {task.assignee_name}
                            </span>
                          )}
                          {task.due_date && (
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {format(new Date(task.due_date), "dd MMM", { locale: fr })}
                            </span>
                          )}
                        </div>
                      </div>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {column.id !== "todo" && (
                            <DropdownMenuItem onClick={() => moveTask(task.id, "todo")}>
                              <Play className="h-4 w-4 mr-2" />
                              À faire
                            </DropdownMenuItem>
                          )}
                          {column.id !== "doing" && (
                            <DropdownMenuItem onClick={() => moveTask(task.id, "doing")}>
                              <Pause className="h-4 w-4 mr-2" />
                              En cours
                            </DropdownMenuItem>
                          )}
                          {column.id !== "done" && (
                            <DropdownMenuItem onClick={() => moveTask(task.id, "done")}>
                              <Check className="h-4 w-4 mr-2" />
                              Terminé
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            className="text-red-500"
                            onClick={() => deleteMutation.mutate(task.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Supprimer
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}

                {columnTasks.length === 0 && (
                  <div className="text-center py-8 text-gray-400 text-sm">
                    Aucune tâche
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// ASSETS TAB (Using unified AssetsList component)
// ============================================================================

function AssetsTab({
  projectId,
  project,
}: {
  projectId: number;
  project: ProjectDetail;
}) {
  // Import dynamically to avoid circular deps
  const { AssetsList } = require("@/components/assets");

  const openDriveFolder = () => {
    if (project.drive_folder_id) {
      window.open(`https://drive.google.com/drive/folders/${project.drive_folder_id}`, "_blank");
    }
  };

  return (
    <div className="space-y-6">
      {/* Drive folder button */}
      <Card 
        className={`bg-white border-gray-200 shadow-sm ${project.drive_folder_id ? "cursor-pointer hover:bg-gray-50 transition-colors" : ""}`}
        onClick={project.drive_folder_id ? openDriveFolder : undefined}
      >
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <Folder className="h-8 w-8 text-blue-500" />
              </div>
              <div>
                <h3 className="text-gray-900 font-medium">Dossier Google Drive</h3>
                <p className="text-gray-500 text-sm">
                  {project.drive_folder_id ? "Cliquez pour ouvrir le dossier" : "Aucun dossier configuré"}
                </p>
              </div>
            </div>
            {project.drive_folder_id && (
              <ExternalLink className="h-5 w-5 text-gray-400" />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Brief Doc */}
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <FileText className="h-6 w-6 text-purple-500" />
              <div className="flex-1">
                <h4 className="text-gray-900 font-medium">Brief</h4>
                <p className="text-gray-400 text-xs">Document Google</p>
              </div>
              {project.brief_doc_id ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    window.open(`https://docs.google.com/document/d/${project.brief_doc_id}`, "_blank");
                  }}
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              ) : (
                <Badge variant="outline" className="text-gray-400">Non créé</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Report Sheet */}
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-6 w-6 text-green-500" />
              <div className="flex-1">
                <h4 className="text-gray-900 font-medium">Report</h4>
                <p className="text-gray-400 text-xs">Spreadsheet Google</p>
              </div>
              {project.report_sheet_id ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    window.open(`https://docs.google.com/spreadsheets/d/${project.report_sheet_id}`, "_blank");
                  }}
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              ) : (
                <Badge variant="outline" className="text-gray-400">Non créé</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Unified Assets List - filtered by projectId */}
      <Card className="bg-white border-gray-200 shadow-sm">
        <CardHeader className="pb-0">
          <CardTitle className="text-lg text-gray-900">Liens & Ressources</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <AssetsList
            projectId={projectId}
            showProjectFilter={false}
            showProjectColumn={false}
          />
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = parseInt(params.id as string, 10);
  const queryClient = useQueryClient();

  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [showAddTask, setShowAddTask] = useState(false);
  const [showAddDeliverable, setShowAddDeliverable] = useState(false);
  const [newTask, setNewTask] = useState({ title: "", description: "", priority: "medium", due_date: "" });
  const [newDeliverable, setNewDeliverable] = useState({ name: "", type: "", due_date: "", link: "" });
  
  // File upload state for deliverables
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: project, isLoading, error } = useQuery({
    queryKey: ["project-detail", projectId],
    queryFn: () => projectDetailApi.getDetail(projectId),
    enabled: !isNaN(projectId) && mounted,
  });
  
  // Fetch Drive folders for file upload
  const { data: driveFolders } = useQuery({
    queryKey: ["project-drive-folders", projectId],
    queryFn: () => projectDriveApi.getDriveFolders(projectId),
    enabled: !isNaN(projectId) && mounted && showAddDeliverable,
  });

  const createTaskMutation = useMutation({
    mutationFn: (data: typeof newTask) => {
      // Convert empty strings to null for optional fields
      const payload = {
        title: data.title,
        description: data.description || undefined,
        priority: data.priority,
        due_date: data.due_date || undefined,
      };
      return projectDetailApi.createTask(projectId, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      setShowAddTask(false);
      setNewTask({ title: "", description: "", priority: "medium", due_date: "" });
      toast.success("Tâche créée");
    },
  });

  const createDeliverableMutation = useMutation({
    mutationFn: async (data: typeof newDeliverable) => {
      let finalLink = data.link;
      
      // If a file is selected, upload it first
      if (selectedFile && selectedFolderId) {
        setIsUploading(true);
        setUploadProgress(0);
        try {
          const uploadResult = await googleWorkspaceApi.uploadFileToDrive(
            selectedFile,
            selectedFolderId,
            selectedFile.name,
            (progress) => setUploadProgress(progress)
          );
          finalLink = uploadResult.web_view_link;
        } finally {
          setIsUploading(false);
        }
      }
      
      // Convert empty strings to undefined for optional fields
      const payload = {
        name: data.name,
        type: data.type || undefined,
        due_date: data.due_date || undefined,
        link: finalLink || undefined,
      };
      return projectDetailApi.createDeliverable(projectId, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-deliverables", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      setShowAddDeliverable(false);
      setNewDeliverable({ name: "", type: "", due_date: "", link: "" });
      setSelectedFile(null);
      setSelectedFolderId("");
      setUploadProgress(0);
      toast.success("Livrable créé");
    },
    onError: (error: any) => {
      if (error?.response?.status === 401) {
        toast.error("Connectez votre compte Google pour uploader des fichiers");
      } else {
        toast.error("Erreur lors de la création du livrable");
      }
    },
  });

  const [isCreatingDrive, setIsCreatingDrive] = useState(false);
  const [isCreatingBrief, setIsCreatingBrief] = useState(false);

  const openDrive = useCallback(async () => {
    // Prevent multiple clicks
    if (isCreatingDrive) return;
    
    if (project?.drive_folder_id) {
      window.open(`https://drive.google.com/drive/folders/${project.drive_folder_id}`, "_blank");
    } else {
      // Create Drive folder
      setIsCreatingDrive(true);
      try {
        const result = await googleWorkspaceApi.createProjectFolder(projectId, project?.name);
        window.open(result.url, "_blank");
        queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
        toast.success("Dossier Drive créé !");
      } catch (error: any) {
        if (error?.response?.status === 401) {
          // Need to connect Google
          toast.error("Connectez votre compte Google dans les paramètres");
        } else {
          toast.error("Erreur lors de la création du dossier");
        }
      } finally {
        setIsCreatingDrive(false);
      }
    }
  }, [project, projectId, queryClient, isCreatingDrive]);

  const createBrief = useCallback(async () => {
    // Prevent multiple clicks
    if (isCreatingBrief) return;
    
    if (project?.brief_doc_id) {
      window.open(`https://docs.google.com/document/d/${project.brief_doc_id}`, "_blank");
      return;
    }
    
    setIsCreatingBrief(true);
    try {
      const result = await googleWorkspaceApi.createProjectBrief(projectId, `Brief - ${project?.name}`);
      window.open(result.url, "_blank");
      queryClient.invalidateQueries({ queryKey: ["project-detail", projectId] });
      toast.success("Brief créé !");
    } catch (error: any) {
      if (error?.response?.status === 401) {
        toast.error("Connectez votre compte Google dans les paramètres");
      } else {
        toast.error("Erreur lors de la création du brief");
      }
    } finally {
      setIsCreatingBrief(false);
    }
  }, [project, projectId, queryClient, isCreatingBrief]);

  if (!mounted || isLoading) {
    return (
      <ProtectedRoute>
        <AppLayoutWithOnboarding>
          <div className="flex items-center justify-center h-96">
            <RadarSpinner className="h-12 w-12 animate-spin text-primary" />
          </div>
        </AppLayoutWithOnboarding>
      </ProtectedRoute>
    );
  }

  if (error || !project) {
    return (
      <ProtectedRoute>
        <AppLayoutWithOnboarding>
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Projet non trouvé</h1>
              <p className="text-gray-500">Le projet demandé n'existe pas ou a été supprimé.</p>
            </div>
          </div>
        </AppLayoutWithOnboarding>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <div className="p-6">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <ProjectHeader
              project={project}
              onAddTask={() => setShowAddTask(true)}
              onAddDeliverable={() => setShowAddDeliverable(true)}
              onOpenDrive={openDrive}
              onCreateBrief={createBrief}
              isCreatingDrive={isCreatingDrive}
              isCreatingBrief={isCreatingBrief}
            />

            <ProductionConnections projectId={project.id} />

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className="bg-gray-100 border border-gray-200">
                <TabsTrigger value="overview" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
                  Vue d'ensemble
                </TabsTrigger>
                <TabsTrigger value="deliverables" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
                  Livrables
                </TabsTrigger>
                <TabsTrigger value="production" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
                  Production
                </TabsTrigger>
                <TabsTrigger value="assets" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
                  Assets
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview">
                <OverviewTab projectId={projectId} project={project} />
              </TabsContent>

              <TabsContent value="deliverables">
                <DeliverablesTab projectId={projectId} onAddDeliverable={() => setShowAddDeliverable(true)} />
              </TabsContent>

              <TabsContent value="production">
                <ProductionTab projectId={projectId} onAddTask={() => setShowAddTask(true)} />
              </TabsContent>

              <TabsContent value="assets">
                <AssetsTab projectId={projectId} project={project} />
              </TabsContent>
            </Tabs>
          </div>

          {/* Add Task Dialog */}
          <Dialog open={showAddTask} onOpenChange={setShowAddTask}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Nouvelle tâche</DialogTitle>
                <DialogDescription>Créez une nouvelle tâche pour ce projet</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>Titre</Label>
                  <Input
                    value={newTask.title}
                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                    placeholder="Ex: Finaliser la maquette"
                  />
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    value={newTask.description}
                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                    placeholder="Détails de la tâche..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Priorité</Label>
                    <Select
                      value={newTask.priority}
                      onValueChange={(v) => setNewTask({ ...newTask, priority: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Basse</SelectItem>
                    <SelectItem value="medium">Moyenne</SelectItem>
                    <SelectItem value="high">Haute</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Due date</Label>
                <Input
                  type="date"
                  value={newTask.due_date}
                  onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddTask(false)}>
              Annuler
            </Button>
            <Button
              onClick={() => createTaskMutation.mutate(newTask)}
              disabled={!newTask.title}
              className="bg-purple-600 hover:bg-purple-700"
            >
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

          {/* Add Deliverable Dialog */}
          <Dialog open={showAddDeliverable} onOpenChange={(open) => {
            setShowAddDeliverable(open);
            if (!open) {
              setSelectedFile(null);
              setSelectedFolderId("");
              setUploadProgress(0);
            }
          }}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Nouveau livrable</DialogTitle>
                <DialogDescription>Ajoutez un nouveau livrable au projet</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>Nom</Label>
                  <Input
                    value={newDeliverable.name}
                    onChange={(e) => setNewDeliverable({ ...newDeliverable, name: e.target.value })}
                    placeholder="Ex: Vidéo teaser"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Type</Label>
                    <Select
                      value={newDeliverable.type}
                      onValueChange={(v) => setNewDeliverable({ ...newDeliverable, type: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="video">Vidéo</SelectItem>
                        <SelectItem value="design">Design</SelectItem>
                        <SelectItem value="document">Document</SelectItem>
                        <SelectItem value="photo">Photo</SelectItem>
                        <SelectItem value="other">Autre</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Due date</Label>
                    <Input
                      type="date"
                      value={newDeliverable.due_date}
                      onChange={(e) => setNewDeliverable({ ...newDeliverable, due_date: e.target.value })}
                    />
                  </div>
                </div>
                
                {/* File Upload Section */}
                <div className="space-y-3 pt-2 border-t">
                  <Label className="flex items-center gap-2">
                    <Upload className="h-4 w-4" />
                    Uploader un fichier vers Google Drive
                  </Label>
                  
                  {/* Check if any drive folder is available (subfolders OR root folder) */}
                  {(driveFolders?.folders?.some(f => f.folder_id) || driveFolders?.drive_folder_id) ? (
                    <>
                      {/* Folder Selection */}
                      <div>
                        <Label className="text-sm text-gray-500">Dossier de destination</Label>
                        <Select
                          value={selectedFolderId}
                          onValueChange={setSelectedFolderId}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Choisir un dossier..." />
                          </SelectTrigger>
                          <SelectContent>
                            {/* Root folder as fallback if no subfolders */}
                            {driveFolders?.drive_folder_id && (
                              <SelectItem value={driveFolders.drive_folder_id}>
                                <div className="flex items-center gap-2">
                                  <Folder className="h-4 w-4 text-blue-500" />
                                  📁 Dossier racine du projet
                                </div>
                              </SelectItem>
                            )}
                            {driveFolders?.folders
                              ?.filter(f => f.folder_id)
                              .map(folder => (
                                <SelectItem key={folder.key} value={folder.folder_id!}>
                                  <div className="flex items-center gap-2">
                                    <FolderOpen className="h-4 w-4 text-yellow-500" />
                                    {folder.label}
                                  </div>
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      {/* File Input */}
                      {selectedFolderId && (
                        <div>
                          {selectedFile ? (
                            <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                              <FileText className="h-5 w-5 text-purple-600 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                                <p className="text-xs text-gray-500">
                                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                                </p>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedFile(null)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          ) : (
                            <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                              <div className="flex flex-col items-center justify-center">
                                <Upload className="h-6 w-6 text-gray-400 mb-1" />
                                <p className="text-sm text-gray-500">Cliquez pour sélectionner un fichier</p>
                              </div>
                              <input
                                type="file"
                                className="hidden"
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (file) {
                                    setSelectedFile(file);
                                    // Auto-fill name if empty
                                    if (!newDeliverable.name) {
                                      setNewDeliverable(prev => ({
                                        ...prev,
                                        name: file.name.replace(/\.[^/.]+$/, "")
                                      }));
                                    }
                                  }
                                }}
                              />
                            </label>
                          )}
                        </div>
                      )}
                      
                      {/* Upload Progress */}
                      {isUploading && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600">Upload en cours...</span>
                            <span className="font-medium">{uploadProgress}%</span>
                          </div>
                          <Progress value={uploadProgress} className="h-2" />
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg space-y-2">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 flex-shrink-0" />
                        Aucun dossier Drive disponible.
                      </div>
                      <p className="text-xs text-amber-500">
                        Cliquez sur le bouton <strong>"Drive"</strong> en haut de la page pour créer la structure de dossiers du projet.
                      </p>
                    </div>
                  )}
                </div>
                
                {/* OR manual link */}
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-gray-500">Ou ajouter un lien</span>
                  </div>
                </div>
                
                <div>
                  <Label>Lien externe (optionnel)</Label>
                  <Input
                    value={newDeliverable.link}
                    onChange={(e) => setNewDeliverable({ ...newDeliverable, link: e.target.value })}
                    placeholder="https://..."
                    disabled={!!selectedFile}
                  />
                  {selectedFile && (
                    <p className="text-xs text-gray-500 mt-1">
                      Le lien sera généré automatiquement après l'upload
                    </p>
                  )}
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowAddDeliverable(false)} disabled={isUploading}>
                  Annuler
                </Button>
                <Button
                  onClick={() => createDeliverableMutation.mutate(newDeliverable)}
                  disabled={!newDeliverable.name || isUploading || createDeliverableMutation.isPending || !!(selectedFile && !selectedFolderId)}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  {isUploading ? (
                    <>
                      <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                      Upload...
                    </>
                  ) : createDeliverableMutation.isPending ? (
                    <>
                      <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                      Création...
                    </>
                  ) : (
                    "Créer"
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
