"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { ToastProvider } from "@/components/ui/toaster";
import { useMemo } from "react";
import { useAuthStore } from "@/store/auth";
import { useSubscriptionStore } from "@/store/subscriptionStore";
import dynamic from "next/dynamic";
import { MotionConfig } from "framer-motion";
import { SiteMotion } from "@/components/ui/site-motion";
import { usePathname } from "next/navigation";

const PUBLIC_PATHS = new Set([
  '/', '/pricing', '/contact', '/mcp', '/legal', '/privacy', '/terms',
  '/review', '/sales-terms', '/cookies', '/data-processing', '/subprocessors',
  '/reversibility', '/accessibility', '/contracts', '/retention',
]);

// Lazy load devtools only in development
const ReactQueryDevtools = dynamic(
  () => import("@tanstack/react-query-devtools").then((mod) => mod.ReactQueryDevtools),
  { ssr: false }
);

export function Providers({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const publicPage = PUBLIC_PATHS.has(pathname) || pathname === '/doc' || pathname.startsWith('/doc/');
  const userId = useAuthStore(s => s.user?.id);
  const loadedWorkspaceId = useSubscriptionStore(s => s.subscription?.workspace_id);
  // Subscription refresh clears its payload temporarily; preserve the selected
  // workspace identity so the application is not remounted in a loading loop.
  const selectedWorkspaceId = typeof window !== "undefined" ? Number(localStorage.getItem('current_workspace_id')) || undefined : undefined;
  const workspaceId = loadedWorkspaceId ?? selectedWorkspaceId;
  // A bearer review is independent of account/workspace hydration. Remounting it
  // after it has consumed and removed its URL fragment would lose the grant.
  const externalReview = pathname === '/review';
  const queryUserId = externalReview ? 'external-review' : userId;
  const queryWorkspaceId = externalReview ? undefined : workspaceId;
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
    [queryUserId, queryWorkspaceId]
  );

  return (
    <QueryClientProvider key={`${queryUserId ?? "anonymous"}:${queryWorkspaceId ?? "none"}`} client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="light"
        enableSystem
        forcedTheme={publicPage ? 'light' : undefined}
        disableTransitionOnChange
      >
        <TooltipProvider delayDuration={300}>
          <ToastProvider>
            <MotionConfig reducedMotion="user">
              <SiteMotion />
              {children}
            </MotionConfig>
          </ToastProvider>
        </TooltipProvider>
      </ThemeProvider>
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
      )}
    </QueryClientProvider>
  );
}
