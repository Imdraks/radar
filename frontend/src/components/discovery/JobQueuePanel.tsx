"use client";

import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";

// Types
export interface JobData {
  id: number;
  artist_name?: string;
  input_type: string;
  input_value: string;
  status: string;
  current_step: string;
  progress: number;
  error_code?: string;
  error_message?: string;
  started_at: string;
  completed_at?: string;
}

interface JobQueuePanelProps {
  jobs: JobData[];
  runningCount: number;
  pendingCount: number;
  completedCount: number;
  isLoading?: boolean;
  onRetry?: (jobId: number) => void;
}

// Steps configuration
const STEPS = [
  { key: "MATCH", label: "Identification", icon: "search", percent: 0 },
  { key: "VIBERATE", label: "Viberate", icon: "chart", percent: 25 },
  { key: "SPOTIFY", label: "Spotify", icon: "music", percent: 50 },
  { key: "COMPUTE", label: "Calcul", icon: "zap", percent: 75 },
];

const getStepIndex = (step: string): number => {
  const idx = STEPS.findIndex((s) => s.key === step);
  return idx >= 0 ? idx : 0;
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case "DONE":
    case "COMPLETED":
      return "text-green-600 dark:text-green-400";
    case "RUNNING":
      return "text-blue-600 dark:text-blue-400";
    case "FAILED":
      return "text-red-600 dark:text-red-400";
    case "QUEUED":
    case "PENDING":
      return "text-yellow-600 dark:text-yellow-400";
    default:
      return "text-gray-600";
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "DONE":
    case "COMPLETED":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "RUNNING":
      return <RadarSpinner className="h-4 w-4 text-primary animate-spin" />;
    case "FAILED":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case "QUEUED":
    case "PENDING":
      return <Clock className="h-4 w-4 text-yellow-500" />;
    default:
      return null;
  }
};

const formatTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "À l'instant";
  if (diffMins < 60) return `Il y a ${diffMins}min`;
  if (diffMins < 1440) return `Il y a ${Math.floor(diffMins / 60)}h`;
  return date.toLocaleDateString("fr-FR");
};

function JobItem({
  job,
  onRetry,
}: {
  job: JobData;
  onRetry?: (jobId: number) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(job.status === "FAILED");
  const currentStepIdx = getStepIndex(job.current_step);

  return (
    <div
      className={`border rounded-lg p-3 transition-colors ${
        job.status === "FAILED"
          ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20"
          : job.status === "RUNNING"
          ? "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-700"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        {getStatusIcon(job.status)}
        <span className="font-medium flex-1 truncate">
          {job.artist_name || job.input_value}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatTime(job.started_at)}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Progress bar for running jobs */}
      {job.status === "RUNNING" && (
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>{STEPS[currentStepIdx]?.label || job.current_step}</span>
            <span>{job.progress}%</span>
          </div>
          <Progress value={job.progress} className="h-1.5" />
        </div>
      )}

      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          {/* Step progression */}
          <div className="flex items-center justify-between mb-3">
            {STEPS.map((step, idx) => {
              const isPast = idx < currentStepIdx;
              const isCurrent = idx === currentStepIdx;
              const isFailed = job.status === "FAILED" && isCurrent;

              return (
                <div key={step.key} className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                      isPast
                        ? "bg-green-100 dark:bg-green-900"
                        : isCurrent
                        ? isFailed
                          ? "bg-red-100 dark:bg-red-900"
                          : "bg-blue-100 dark:bg-blue-900 animate-pulse"
                        : "bg-gray-100 dark:bg-gray-800"
                    }`}
                  >
                    {isPast ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      step.icon
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground mt-1">
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Error message */}
          {job.status === "FAILED" && job.error_message && (
            <div className="bg-red-100 dark:bg-red-900/30 rounded p-2 text-sm text-red-800 dark:text-red-200 mb-2">
              <div className="font-medium">Erreur: {job.error_code || "UNKNOWN"}</div>
              <div className="text-xs mt-1">{job.error_message}</div>
            </div>
          )}

          {/* Retry button for failed jobs */}
          {job.status === "FAILED" && onRetry && (
            <Button
              variant="outline"
              size="sm"
              className="w-full mt-2"
              onClick={() => onRetry(job.id)}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Réessayer
            </Button>
          )}

          {/* Metadata */}
          <div className="text-xs text-muted-foreground mt-2">
            <span>Type: {job.input_type}</span>
            {job.completed_at && (
              <span className="ml-3">
                Terminé: {new Date(job.completed_at).toLocaleTimeString("fr-FR")}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function JobQueuePanel({
  jobs,
  runningCount,
  pendingCount,
  completedCount,
  isLoading = false,
  onRetry,
}: JobQueuePanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Separate jobs by status
  const activeJobs = jobs.filter((j) => j.status === "RUNNING" || j.status === "QUEUED" || j.status === "PENDING");
  const recentJobs = jobs.filter(
    (j) => j.status === "DONE" || j.status === "COMPLETED" || j.status === "FAILED"
  );

  return (
    <Card className="w-full">
      <CardHeader
        className="py-3 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <RadarSpinner
              className={`h-4 w-4 ${runningCount > 0 ? "animate-spin text-blue-500" : "text-gray-400"}`}
            />
            File d'enrichissement
          </CardTitle>
          <div className="flex items-center gap-2">
            {runningCount > 0 && (
              <Badge variant="default" className="bg-blue-500">
                {runningCount} en cours
              </Badge>
            )}
            {pendingCount > 0 && (
              <Badge variant="outline">{pendingCount} en attente</Badge>
            )}
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              {isCollapsed ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronUp className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      {!isCollapsed && (
        <CardContent className="pt-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <RadarSpinner className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground text-sm">
              Aucun job en cours. Recherchez un artiste pour démarrer.
            </div>
          ) : (
            <ScrollArea className="h-[300px] pr-4">
              <div className="space-y-2">
                {/* Active jobs first */}
                {activeJobs.map((job) => (
                  <JobItem key={job.id} job={job} onRetry={onRetry} />
                ))}

                {/* Divider if both types */}
                {activeJobs.length > 0 && recentJobs.length > 0 && (
                  <div className="flex items-center gap-2 py-2">
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                    <span className="text-xs text-muted-foreground">
                      Terminés ({completedCount})
                    </span>
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                  </div>
                )}

                {/* Recent completed jobs */}
                {recentJobs.slice(0, 10).map((job) => (
                  <JobItem key={job.id} job={job} onRetry={onRetry} />
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      )}
    </Card>
  );
}
