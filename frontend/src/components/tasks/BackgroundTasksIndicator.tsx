"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  FileText,
  ChevronRight,
  Trash2,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useTasksStore, BackgroundTask } from "@/store/tasks";
import { collectionApi } from "@/lib/api";
import { useProgressStream, ProgressData } from "@/lib/useProgressStream";

export function BackgroundTasksIndicator() {
  const router = useRouter();
  const { tasks, updateTask, clearCompletedTasks, getActiveTasks } = useTasksStore();
  const [open, setOpen] = useState(false);
  const [taskMessages, setTaskMessages] = useState<Record<string, string>>({});
  
  const activeTasks = getActiveTasks();
  const hasActiveTasks = activeTasks.length > 0;
  const recentTasks = tasks.slice(0, 10);
  
  // Get task IDs for active tasks
  const activeTaskIds = activeTasks
    .filter(t => t.status === "running")
    .map(t => t.id);
  
  // Handle progress updates from SSE
  const handleProgress = useCallback((data: ProgressData) => {
    const taskId = data.task_id;
    const progress = data.data?.progress ?? 0;
    const message = data.data?.message;
    
    updateTask(taskId, { progress });
    
    if (message) {
      setTaskMessages(prev => ({ ...prev, [taskId]: message }));
    }
  }, [updateTask]);
  
  const handleCompleted = useCallback((data: ProgressData) => {
    const taskId = data.task_id;
    const result = data.data?.result as Record<string, unknown> | undefined;
    
    updateTask(taskId, {
      status: "completed",
      progress: 100,
      completedAt: new Date().toISOString(),
      result: {
        documentCount: result?.new as number,
        contactCount: result?.contacts_found as number,
      },
    });
    
    setTaskMessages(prev => ({ ...prev, [taskId]: data.data?.message || "Terminé" }));
  }, [updateTask]);
  
  const handleFailed = useCallback((data: ProgressData) => {
    const taskId = data.task_id;
    
    updateTask(taskId, {
      status: "failed",
      completedAt: new Date().toISOString(),
      result: {
        error: data.data?.error || "Erreur inconnue",
      },
    });
    
    setTaskMessages(prev => ({ ...prev, [taskId]: data.data?.error || "Échec" }));
  }, [updateTask]);
  
  // Use SSE for real-time progress updates
  useProgressStream({
    taskIds: activeTaskIds,
    onProgress: handleProgress,
    onCompleted: handleCompleted,
    onFailed: handleFailed,
    enabled: activeTaskIds.length > 0,
  });
  
  // Fallback polling for collection tasks (API-based status)
  useEffect(() => {
    if (!hasActiveTasks) return;
    
    const pollInterval = setInterval(async () => {
      for (const task of activeTasks) {
        // Only poll for collection type tasks as fallback
        if (task.type === "collection" && task.status === "running") {
          try {
            const run = await collectionApi.getRun(task.id);
            
            if (run.status === "SUCCESS" || run.status === "PARTIAL") {
              updateTask(task.id, {
                status: "completed",
                completedAt: new Date().toISOString(),
                result: {
                  briefId: run.id,
                  documentCount: run.documents_new || run.documents_updated,
                  contactCount: run.contacts_found,
                },
              });
            } else if (run.status === "FAILED") {
              updateTask(task.id, {
                status: "failed",
                completedAt: new Date().toISOString(),
                result: {
                  error: run.error_summary || "Erreur inconnue",
                },
              });
            } else {
              // Update progress based on sources processed
              const progress = run.sources_success > 0 
                ? Math.min(90, Math.round((run.sources_success / run.source_count) * 100))
                : 10;
              updateTask(task.id, { progress });
            }
          } catch {
            // API polling failed, SSE should handle this
            console.debug("Polling fallback: API not available for task", task.id);
          }
        }
      }
    }, 5000); // Longer interval since SSE is primary
    
    return () => clearInterval(pollInterval);
  }, [activeTasks, hasActiveTasks, updateTask]);
  
  const getStatusIcon = (status: BackgroundTask["status"]) => {
    switch (status) {
      case "pending":
        return <Clock className="h-4 w-4 text-muted-foreground" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };
  
  const getStatusLabel = (status: BackgroundTask["status"]) => {
    switch (status) {
      case "pending":
        return "En attente";
      case "running":
        return "En cours";
      case "completed":
        return "Terminé";
      case "failed":
        return "Échoué";
    }
  };
  
  const handleTaskClick = (task: BackgroundTask) => {
    if (task.status === "completed" && task.result?.briefId) {
      router.push(`/briefs?id=${task.result.briefId}`);
      setOpen(false);
    } else if (task.status === "completed" && task.type === "collection") {
      router.push("/briefs");
      setOpen(false);
    }
  };
  
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return "À l'instant";
    if (diffMins < 60) return `Il y a ${diffMins} min`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    
    return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  };
  
  // Don't render if no tasks ever
  if (tasks.length === 0) {
    return null;
  }
  
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
        >
          {hasActiveTasks ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-blue-500 text-[10px] font-bold text-white flex items-center justify-center">
                {activeTasks.length}
              </span>
            </>
          ) : (
            <FileText className="h-5 w-5 text-muted-foreground" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-3 border-b">
          <h4 className="font-semibold text-sm">Tâches en arrière-plan</h4>
          {tasks.some(t => t.status === "completed" || t.status === "failed") && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={clearCompletedTasks}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Effacer
            </Button>
          )}
        </div>
        
        <ScrollArea className="max-h-[300px]">
          {recentTasks.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              Aucune tâche récente
            </div>
          ) : (
            <div className="divide-y">
              {recentTasks.map((task) => (
                <div
                  key={task.id}
                  className={cn(
                    "p-3 hover:bg-muted/50 transition-colors",
                    (task.status === "completed" && task.result?.briefId) && "cursor-pointer"
                  )}
                  onClick={() => handleTaskClick(task)}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {getStatusIcon(task.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">
                          {task.title}
                        </span>
                        <Badge
                          variant={
                            task.status === "completed" ? "default" :
                            task.status === "failed" ? "destructive" :
                            "secondary"
                          }
                          className="text-[10px] px-1.5 py-0"
                        >
                          {getStatusLabel(task.status)}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <span>{formatTime(task.startedAt)}</span>
                        
                        {task.status === "completed" && task.result && (
                          <>
                            <span>•</span>
                            <span>
                              {task.result.documentCount || 0} docs
                              {task.result.contactCount ? `, ${task.result.contactCount} contacts` : ""}
                            </span>
                          </>
                        )}
                        
                        {task.status === "failed" && task.result?.error && (
                          <>
                            <span>•</span>
                            <span className="text-red-500 truncate">
                              {task.result.error}
                            </span>
                          </>
                        )}
                      </div>
                      
                      {task.status === "running" && task.progress !== undefined && (
                        <div className="mt-2">
                          {/* Progress message from SSE */}
                          {taskMessages[task.id] && (
                            <div className="text-xs text-blue-600 mb-1 truncate">
                              {taskMessages[task.id]}
                            </div>
                          )}
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 transition-all duration-300"
                              style={{ width: `${task.progress}%` }}
                            />
                          </div>
                          <div className="text-[10px] text-muted-foreground mt-0.5 text-right">
                            {task.progress}%
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {task.status === "completed" && task.result?.briefId && (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        
        {hasActiveTasks && (
          <div className="p-2 border-t bg-muted/30">
            <p className="text-xs text-center text-muted-foreground">
              {activeTasks.length} tâche{activeTasks.length > 1 ? "s" : ""} en cours...
            </p>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
