"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Target,
  Settings,
  Rss,
  Users,
  BarChart3,
  LogOut,
  Menu,
  X,
  Calendar,
  Kanban,
  Music,
  Search,
  GitCompare,
  FileText,
  ChevronRight,
  Bell,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAuthStore } from "@/store/auth";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { NotificationCenter } from "@/components/notifications/NotificationCenter";
import { BackgroundTasksIndicator } from "@/components/tasks/BackgroundTasksIndicator";
import { OnboardingProvider, OnboardingTour, OnboardingTrigger, WelcomeModal } from "@/components/onboarding";

// Navigation structure
const navigation: {
  name: string;
  href: string;
  icon: LucideIcon;
  adminOnly?: boolean;
  isNew?: boolean;
}[] = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Opportunités", href: "/opportunities", icon: Target },
  { name: "Dossiers", href: "/dossiers", icon: FileText, isNew: true },
  { name: "Kanban", href: "/opportunities/kanban", icon: Kanban },
  { name: "Calendrier", href: "/opportunities/calendar", icon: Calendar },
  { name: "Artistes", href: "/artist-history", icon: Music },
  { name: "Découverte", href: "/discovery", icon: Search },
  { name: "Comparaison", href: "/comparison", icon: GitCompare },
  { name: "Sources", href: "/sources", icon: Rss },
  { name: "Scoring", href: "/scoring", icon: BarChart3 },
  { name: "Utilisateurs", href: "/users", icon: Users, adminOnly: true },
  { name: "Paramètres", href: "/settings", icon: Settings },
];

interface AppLayoutProps {
  children: React.ReactNode;
}

function AppLayoutInner({ children }: AppLayoutProps) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isAdmin = user?.role === "admin";

  const filteredNavigation = navigation.filter(
    (item) => !item.adminOnly || isAdmin
  );

  const currentPage = filteredNavigation.find(item => pathname.startsWith(item.href));

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 dark:bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        data-onboarding="sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:z-auto",
          "bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 shadow-sm",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-5 border-b border-gray-200 dark:border-gray-800">
            <Link href="/dashboard" className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#0000FF] dark:bg-blue-600 flex items-center justify-center shadow-md shadow-blue-500/20 dark:shadow-blue-500/30">
                <Target className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
                Radar
              </span>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 py-4">
            <nav className="px-3 space-y-1">
              {filteredNavigation.map((item) => {
                const isActive = pathname === item.href || 
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                      isActive
                        ? "bg-[#0000FF] dark:bg-blue-600 text-white shadow-md shadow-blue-500/25"
                        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white"
                    )}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon className={cn(
                      "h-5 w-5 flex-shrink-0",
                      isActive ? "text-white" : "text-gray-400 dark:text-gray-500"
                    )} />
                    <span className="flex-1">{item.name}</span>
                    {item.isNew && !isActive && (
                      <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide bg-blue-100 dark:bg-blue-900/50 text-[#0000FF] dark:text-blue-400 rounded-full">
                        New
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </ScrollArea>

          {/* User info & Logout */}
          <div className="border-t border-gray-200 dark:border-gray-800 p-4" data-onboarding="user-menu">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-gray-800 mb-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#0000FF] to-blue-400 dark:from-blue-600 dark:to-blue-500 flex items-center justify-center text-white text-sm font-bold shadow-md">
                {user?.full_name?.charAt(0) || user?.email?.charAt(0) || "U"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {user?.full_name || user?.email}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                  {user?.role}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 h-9 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 border-gray-200 dark:border-gray-700"
                onClick={logout}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Déconnexion
              </Button>
              <OnboardingTrigger variant="icon" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between px-6 shadow-sm">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Menu className="h-5 w-5" />
            </Button>
            
            {/* Breadcrumb */}
            <div className="hidden lg:flex items-center gap-2 text-sm">
              <span className="text-gray-400 dark:text-gray-500">Radar</span>
              <ChevronRight className="h-4 w-4 text-gray-300 dark:text-gray-600" />
              <span className="text-gray-900 dark:text-white font-semibold">
                {currentPage?.name || "Dashboard"}
              </span>
            </div>
            
            <span className="lg:hidden text-gray-900 dark:text-white font-bold text-lg">Radar</span>
          </div>
          
          <div className="flex items-center gap-2">
            <BackgroundTasksIndicator />
            <NotificationCenter />
            <ThemeToggle />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-950 p-6">
          {children}
        </main>
      </div>
      
      {/* Onboarding Tour */}
      <OnboardingTour />
      <WelcomeModal />
    </div>
  );
}

// Main export - always includes OnboardingProvider
export function AppLayout({ children }: AppLayoutProps) {
  return (
    <OnboardingProvider>
      <AppLayoutInner>{children}</AppLayoutInner>
    </OnboardingProvider>
  );
}

// Alias for backwards compatibility
export function AppLayoutWithOnboarding({ children }: AppLayoutProps) {
  return <AppLayout>{children}</AppLayout>;
}

export default AppLayout;
