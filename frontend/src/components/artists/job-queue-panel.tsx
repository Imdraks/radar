"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Music2,
  Database,
  RefreshCw,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface Job {
  id: string;
  input_type: string;
  input_value: string;
  artist_id: string | null;
  artist_name: string | null;
  status: string;
  current_step: string | null;
  progress_pct: number;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface JobQueueResponse {
  jobs: Job[];
  running_count: number;
  pending_count: number;
  completed_count: number;
}

// Step mapping for display
const STEPS = [
  { key: "MATCH", label: "Match", icon: Database },
  { key: "VIBERATE", label: "Viberate", icon: Zap },
  { key: "SPOTIFY", label: "Spotify", icon: Music2 },
  { key: "COMPUTE", label: "Compute", icon: CheckCircle2 },
];

function getStepIndex(step: string | null): number {
  if (!step) return -1;
  const idx = STEPS.findIndex(s => step.toUpperCase().includes(s.key));
  return idx >= 0 ? idx : -1;
}

function getStatusConfig(status: string) {
  switch (status) {
    case "DONE":
      return { color: "text-green-600", bg: "bg-green-50", icon: CheckCircle2 };
    case "PARTIAL":
      return { color: "text-amber-600", bg: "bg-amber-50", icon: AlertCircle };
    case "FAILED":
      return { color: "text-red-600", bg: "bg-red-50", icon: XCircle };
    case "RUNNING":
      return { color: "text-blue-600", bg: "bg-blue-50", icon: RadarSpinner };
    case "QUEUED":
      return { color: "text-gray-600", bg: "bg-gray-50", icon: Clock };
    default:
      return { color: "text-gray-600", bg: "bg-gray-50", icon: Clock };
  }
}

function JobSteps({ job }: { job: Job }) {
  const currentIdx = getStepIndex(job.current_step);
  const isDone = job.status === "DONE" || job.status === "PARTIAL";
  const isFailed = job.status === "FAILED";

  return (
    <div className="flex items-center gap-1 mt-2">
      {STEPS.map((step, idx) => {
        const StepIcon = step.icon;
        let status: "done" | "active" | "pending" | "failed" = "pending";
        
        if (isDone) {
          status = "done";
        } else if (isFailed && idx <= currentIdx) {
          status = idx === currentIdx ? "failed" : "done";
        } else if (idx < currentIdx) {
          status = "done";
        } else if (idx === currentIdx) {
          status = "active";
        }

        return (
          <div key={step.key} className="flex items-center">
            <div
              className={cn(
                "flex items-center justify-center w-6 h-6 rounded-full transition-all",
                status === "done" && "bg-green-100 text-green-600",
                status === "active" && "bg-blue-100 text-blue-600",
                status === "pending" && "bg-gray-100 text-gray-400",
                status === "failed" && "bg-red-100 text-red-600"
              )}
            >
              {status === "active" ? (
                <RadarSpinner className="h-3 w-3 animate-spin" />
              ) : status === "done" ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : status === "failed" ? (
                <XCircle className="h-3 w-3" />
              ) : (
                <span className="text-[10px] font-medium">{idx + 1}</span>
              )}
            </div>
            {idx < STEPS.length - 1 && (
              <ChevronRight className={cn(
                "h-3 w-3 mx-0.5",
                (status === "done" || (isDone && idx < 3)) ? "text-green-400" : "text-gray-300"
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function JobCard({ job, onViewDetail }: { job: Job; onViewDetail?: (id: string) => void }) {
  const statusConfig = getStatusConfig(job.status);
  const StatusIcon = statusConfig.icon;

  return (
    <div className={cn(
      "p-3 rounded-lg border transition-all hover:shadow-sm",
      statusConfig.bg
    )}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <StatusIcon className={cn("h-4 w-4", statusConfig.color, job.status === "RUNNING" && "animate-spin")} />
            <span className="font-medium truncate">
              {job.artist_name || job.input_value}
            </span>
          </div>
          
          {job.status === "RUNNING" && (
            <>
              <Progress value={job.progress_pct} className="h-1 mt-2" />
              <JobSteps job={job} />
            </>
          )}

          {job.status === "QUEUED" && (
            <p className="text-xs text-muted-foreground mt-1">En attente...</p>
          )}

          {(job.status === "DONE" || job.status === "PARTIAL") && (
            <p className="text-xs text-muted-foreground mt-1">
              Terminé {formatDistanceToNow(new Date(job.completed_at || job.created_at), { 
                addSuffix: true, 
                locale: fr 
              })}
            </p>
          )}

          {job.status === "FAILED" && (
            <p className="text-xs text-red-600 mt-1">
              {job.error_message || "Erreur lors de l'analyse"}
            </p>
          )}
        </div>

        {(job.status === "DONE" || job.status === "PARTIAL") && job.artist_id && onViewDetail && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onViewDetail(job.artist_id!)}
            className="ml-2"
          >
            Voir
          </Button>
        )}
      </div>
    </div>
  );
}

interface JobQueuePanelProps {
  className?: string;
  onViewDetail?: (artistId: string) => void;
  refetchInterval?: number;
}

export function JobQueuePanel({ 
  className, 
  onViewDetail,
  refetchInterval = 2000,
}: JobQueuePanelProps) {
  const { data, isLoading, refetch } = useQuery<JobQueueResponse>({
    queryKey: ["artist-jobs"],
    queryFn: async () => {
      const response = await api.get("/api/v1/artists/jobs?limit=10");
      return response.data;
    },
    refetchInterval: (query) => {
      // Auto-refresh faster when jobs are running
      const queueData = query.state.data;
      if (queueData && (queueData.running_count > 0 || queueData.pending_count > 0)) {
        return refetchInterval;
      }
      return 10000; // Slow refresh when idle
    },
  });

  if (isLoading) {
    return (
      <Card className={cn("p-4", className)}>
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      </Card>
    );
  }

  if (!data || data.jobs.length === 0) {
    return null; // Don't show panel if no jobs
  }

  const hasActiveJobs = data.running_count > 0 || data.pending_count > 0;

  return (
    <Card className={cn("overflow-hidden", className)}>
      {/* Header */}
      <div className="px-4 py-3 bg-muted/50 border-b flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold">Analyses en cours</h3>
          {hasActiveJobs && (
            <Badge variant="secondary" className="bg-blue-100 text-blue-700">
              {data.running_count + data.pending_count} actives
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          className="h-8 w-8 p-0"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Jobs list */}
      <ScrollArea className="h-[300px]">
        <div className="p-3 space-y-2">
          {data.jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onViewDetail={onViewDetail}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Footer stats */}
      <div className="px-4 py-2 bg-muted/30 border-t text-xs text-muted-foreground flex items-center justify-between">
        <span>{data.completed_count} analyses terminées</span>
        {hasActiveJobs && (
          <span className="flex items-center gap-1">
            <RadarSpinner className="h-3 w-3 animate-spin" />
            Mise à jour automatique
          </span>
        )}
      </div>
    </Card>
  );
}
