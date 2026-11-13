"use client";

import { useEffect, useCallback, useRef, useState } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";

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

export function useProgressStream({taskIds,onProgress,onCompleted,onFailed,enabled=true}: UseProgressStreamOptions) {
  const [isConnected,setIsConnected] = useState(false);
  const [lastProgress,setLastProgress] = useState<Record<string,ProgressData>>({});
  const controller = useRef<AbortController | null>(null);
  const callbacks = useRef({onProgress,onCompleted,onFailed});
  callbacks.current = {onProgress,onCompleted,onFailed};
  const selection = taskIds.join(",");
  const disconnect = useCallback(() => {controller.current?.abort();controller.current=null;setIsConnected(false);},[]);
  const connect = useCallback(() => {
    disconnect();
    if (!enabled || !selection) return;
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const abort = new AbortController();controller.current=abort;
    const params = new URLSearchParams({task_ids:selection});
    const workspace = localStorage.getItem("current_workspace_id");
    if (workspace) params.set("workspace_id",workspace);
    const pending = new Set(selection.split(","));
    void fetchEventSource(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/progress/stream?${params}`, {
      headers:{Authorization:`Bearer ${token}`},signal:abort.signal,openWhenHidden:true,
      async onopen(response) {
        if (!response.ok || !response.headers.get("content-type")?.includes("text/event-stream")) {
          throw new Error("Progress stream unavailable");
        }
        setIsConnected(true);
      },
      onmessage(event) {
        if (["connected","heartbeat"].includes(event.event) || !event.data) return;
        if (event.event === "error") throw new Error("Progress stream unavailable");
        const data = JSON.parse(event.data) as ProgressData;
        if (!pending.has(data.task_id)) return;
        setLastProgress(previous => ({...previous,[data.task_id]:data}));
        if (event.event === "completed" || event.event === "failed") {
          pending.delete(data.task_id);
          if (event.event === "completed") callbacks.current.onCompleted?.(data);
          else callbacks.current.onFailed?.(data);
          if (!pending.size) {abort.abort();setIsConnected(false);}
        } else callbacks.current.onProgress?.(data);
      },
      onclose(){setIsConnected(false);},
      onerror(error){setIsConnected(false);throw error;},
    }).catch(() => {if (!abort.signal.aborted) setIsConnected(false);});
  },[disconnect,enabled,selection]);
  useEffect(() => {connect();return disconnect;},[connect,disconnect]);
  return {isConnected,lastProgress,disconnect,reconnect:connect};
}
export type { ProgressData };
