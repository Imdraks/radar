"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { ToastProvider } from "@/components/ui/toaster";
import { useMemo } from "react";
import { useAuthStore } from "@/store/auth";
import { useSubscriptionStore } from "@/store/subscriptionStore";
import dynamic from "next/dynamic";

// Lazy load devtools only in development
const ReactQueryDevtools = dynamic(
  () => import("@tanstack/react-query-devtools").then((mod) => mod.ReactQueryDevtools),
  { ssr: false }
);

export function Providers({ children }: { children: React.ReactNode }) {
  const userId = useAuthStore(s => s.user?.id);
  const loadedWorkspaceId = useSubscriptionStore(s => s.subscription?.workspace_id);
  // Subscription refresh clears its payload temporarily; preserve the selected
  // workspace identity so the application is not remounted in a loading loop.
  const selectedWorkspaceId = typeof window !== "undefined" ? Number(localStorage.getItem('current_workspace_id')) || undefined : undefined;
  const workspaceId = loadedWorkspaceId ?? selectedWorkspaceId;
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Increase stale time to reduce refetches
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 30 * 60 * 1000, // 30 minutes cache
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
            retry: 1, // Only retry once
            retryDelay: 1000,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
    [userId, workspaceId]
  );

  return (
    <QueryClientProvider key={`${userId ?? "anonymous"}:${workspaceId ?? "none"}`} client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="light"
        enableSystem={false}
        disableTransitionOnChange
      >
        <TooltipProvider delayDuration={300}>
          <ToastProvider>
            {children}
          </ToastProvider>
        </TooltipProvider>
      </ThemeProvider>
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
      )}
    </QueryClientProvider>
  );
}
