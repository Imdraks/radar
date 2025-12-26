"use client";

import { useEffect, useCallback, useRef, useState } from "react";

interface ProgressData {
  task_id: string;
  type: "start" | "step" | "progress" | "source" | "log" | "completed" | "failed" | "heartbeat";
  timestamp?: string;
  data: {
    message?: string;
    progress?: number;
    current_step?: number;
    total_steps?: number;
    items_processed?: number;
    items_total?: number;
    source_name?: string;
    source_index?: number;
    total_sources?: number;
    status?: string;
    error?: string;
    result?: Record<string, unknown>;
    elapsed_seconds?: number;
  };
}

interface UseProgressStreamOptions {
  taskIds: string[];
  onProgress?: (data: ProgressData) => void;
  onCompleted?: (data: ProgressData) => void;
  onFailed?: (data: ProgressData) => void;
  enabled?: boolean;
}

export function useProgressStream({
  taskIds,
  onProgress,
  onCompleted,
  onFailed,
  enabled = true,
}: UseProgressStreamOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastProgress, setLastProgress] = useState<Record<string, ProgressData>>({});
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!enabled || taskIds.length === 0) return;

    // Get token from localStorage (same key as api.ts)
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) {
      // Token not found yet, might still be loading - don't spam console
      return;
    }

    // Build URL
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "";
    const url = `${baseUrl}/api/v1/progress/stream?token=${token}&task_ids=${taskIds.join(",")}`;

    try {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log("Progress stream connected");
        setIsConnected(true);
      };

      eventSource.onerror = (error) => {
        console.error("Progress stream error:", error);
        setIsConnected(false);

        // Reconnect after 5 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, 5000);
        }
      };

      // Handle different event types
      eventSource.addEventListener("connected", (event) => {
        console.log("Progress stream connected:", event.data);
      });

      eventSource.addEventListener("start", (event) => {
        const data = JSON.parse(event.data) as ProgressData;
        setLastProgress((prev) => ({ ...prev, [data.task_id]: data }));
        onProgress?.(data);
      });

      eventSource.addEventListener("step", (event) => {
        const data = JSON.parse(event.data) as ProgressData;
        setLastProgress((prev) => ({ ...prev, [data.task_id]: data }));
        onProgress?.(data);
      });

      eventSource.addEventListener("progress", (event) => {
        const data = JSON.parse(event.data) as ProgressData;
        setLastProgress((prev) => ({ ...prev, [data.task_id]: data }));
        onProgress?.(data);
      });

      eventSource.addEventListener("source", (event) => {
        const data = JSON.parse(event.data) as ProgressData;
        setLastProgress((prev) => ({ ...prev, [data.task_id]: data }));
        onProgress?.(data);
      });

      eventSource.addEventListener("completed", (event) => {
        const data = JSON.parse(event.data) as ProgressData;
        setLastProgress((prev) => ({ ...prev, [data.task_id]: data }));
        onCompleted?.(data);
        // Close connection for this task
        eventSource.close();
        setIsConnected(false);
      });

      eventSource.addEventListener("failed", (event) => {
        const data = JSON.parse(event.data) as ProgressData;
        setLastProgress((prev) => ({ ...prev, [data.task_id]: data }));
        onFailed?.(data);
        // Close connection for this task
        eventSource.close();
        setIsConnected(false);
      });

      eventSource.addEventListener("heartbeat", () => {
        // Heartbeat received, connection is alive
      });

    } catch (error) {
      console.error("Failed to create EventSource:", error);
    }
  }, [enabled, taskIds, onProgress, onCompleted, onFailed]);

  // Connect when taskIds change
  useEffect(() => {
    if (enabled && taskIds.length > 0) {
      connect();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [enabled, taskIds.join(","), connect]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  return {
    isConnected,
    lastProgress,
    disconnect,
    reconnect: connect,
  };
}

export type { ProgressData };
