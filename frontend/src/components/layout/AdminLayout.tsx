'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { 
  Building2,
  Users,
  FolderOpen,
  Activity,
  Settings,
  Shield,
  Mail,
  Loader2,
  LogOut,
  LayoutDashboard,
  Rss,
  HeartPulse,
  Sliders,
  BarChart3,
  Brain,
  Menu,
  X,
  ChevronDown,
  Bell,
  Moon,
  Sun,
} from 'lucide-react';
import { Button } from "@/components/ui/button";
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';
import { RadarLogo } from '@/components/brand/RadarBrand';

interface AdminLayoutProps {
  children: React.ReactNode;
}

const adminNavigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Workspaces', href: '/workspaces', icon: Building2 },
  { name: 'Utilisateurs', href: '/users', icon: Users },
  { name: 'Logs Activité', href: '/admin/activity', icon: Activity },
];

const toolsNavigation = [
  { name: 'Sources', href: '/sources', icon: Rss },
  { name: 'Source Health', href: '/source-health', icon: HeartPulse },
];

const bottomNavigation = [
  { name: 'Paramètres', href: '/settings', icon: Settings },
];

export function AdminLayout({ children }: AdminLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toolsExpanded, setToolsExpanded] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Check if user is admin
    if (user && user.role !== 'admin') {
      router.push('/today');
    }
  }, [user, router]);

  useEffect(() => {
    // Load dark mode preference
    const isDark = localStorage.getItem('theme') === 'dark';
    setDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('theme', newMode ? 'dark' : 'light');
    document.documentElement.classList.toggle('dark', newMode);
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (!user || user.role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-slate-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 lg:translate-x-0 lg:static",
          "bg-neutral-950 text-white",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 py-5 border-b border-neutral-800">
            <div><RadarLogo inverted /><p className="mt-2 text-xs text-muted-foreground">Administration plateforme</p></div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
            {/* Main Admin Navigation */}
            {adminNavigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-violet-600 text-white"
                      : "text-gray-300 hover:bg-neutral-800 hover:text-white"
                  )}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}

            {/* Divider */}
            <div className="my-4 border-t border-gray-800" />

            {/* Tools Section */}
            <button
              onClick={() => setToolsExpanded(!toolsExpanded)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-neutral-800 hover:text-white transition-colors"
            >
              <Settings className="h-5 w-5" />
              <span className="flex-1 text-left">Outils Techniques</span>
              <ChevronDown className={cn(
                "h-4 w-4 transition-transform",
                toolsExpanded ? "rotate-180" : ""
              )} />
            </button>

            {toolsExpanded && (
              <div className="ml-4 space-y-1 border-l border-neutral-800 pl-4">
                {toolsNavigation.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                        isActive
                        ? "bg-neutral-800 text-white"
                        : "text-gray-400 hover:bg-neutral-800 hover:text-gray-200"
                      )}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            )}

            {/* Divider */}
            <div className="my-4 border-t border-neutral-800" />

            {/* Bottom Navigation */}
            {bottomNavigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-neutral-800 text-white"
                      : "text-gray-300 hover:bg-neutral-800 hover:text-white"
                  )}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User Section */}
          <div className="px-4 py-4 border-t border-neutral-800">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="h-9 w-9 rounded-full bg-violet-600 flex items-center justify-center text-sm font-medium">
                {user.full_name?.charAt(0) || 'A'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user.full_name}</p>
                <p className="text-xs text-gray-400 truncate">{user.email}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              className="w-full mt-2 text-gray-400 hover:text-white hover:bg-neutral-800"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Déconnexion
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-700/50 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-neutral-800"
              >
                <Menu className="h-5 w-5" />
              </button>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {adminNavigation.find(n => pathname === n.href)?.name || 
                 toolsNavigation.find(n => pathname === n.href)?.name ||
                 'Administration'}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" onClick={toggleDarkMode}>
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </Button>
              <Button variant="ghost" size="icon">
                <Bell className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 dark:bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
