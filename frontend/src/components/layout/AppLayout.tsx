'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, LogOut } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { useSubscriptionStore, selectedWorkspace } from '@/store/subscriptionStore';
import { RouteGuard } from '@/components/access/RouteGuard';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { BackgroundTasksIndicator } from '@/components/tasks/BackgroundTasksIndicator';
import { OnboardingProvider, OnboardingTour, OnboardingTrigger, WelcomeModal } from '@/components/onboarding';
import { MobileBottomNav } from './MobileBottomNav';

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { navigation, subscription, isLoading, error, fetchSubscription, setAdmin } = useSubscriptionStore();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const refresh = () => { void fetchSubscription(selectedWorkspace()); };
    refresh();
    window.addEventListener('storage', refresh);
    window.addEventListener('workspace-changed', refresh);
    return () => { window.removeEventListener('storage', refresh); window.removeEventListener('workspace-changed', refresh); };
  }, [fetchSubscription, user?.id]);
  useEffect(() => setAdmin(user?.is_superuser === true), [user, setAdmin]);
  return <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex">
    {open && <button aria-label="Fermer le menu" className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setOpen(false)} />}
    <aside data-onboarding="sidebar" className={`${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-slate-900 border-r overflow-y-auto lg:static lg:shrink-0`}>
      <div className="flex justify-between items-center p-5"><Link href="/today" className="text-xl font-bold">Radar</Link><button className="lg:hidden" aria-label="Fermer le menu" onClick={() => setOpen(false)}><X /></button></div>
      <nav aria-label="Navigation principale" className="p-3 space-y-5">
        {Object.entries(navigation || {}).map(([section, items]) => <div key={section}>
          <p className="px-3 mb-1 text-xs font-semibold uppercase text-gray-500">{section}</p>
          {items.map(item => <Link key={item.path} href={item.path} onClick={() => setOpen(false)} aria-current={pathname === item.path ? 'page' : undefined}
            className={`block px-3 py-2 rounded-md text-sm ${pathname === item.path ? 'bg-purple-100 text-purple-800' : 'hover:bg-gray-100 dark:hover:bg-slate-800'}`}>{item.label}</Link>)}
        </div>)}
        {user?.is_superuser && <Link className="block px-3 py-2" href="/admin">Administration plateforme</Link>}
      </nav>
      <button onClick={() => { useSubscriptionStore.getState().reset(); logout(); }} className="flex gap-2 p-5 text-sm"><LogOut size={16} />Déconnexion</button>
    </aside>
    <div className="flex-1 min-w-0">
      <header className="flex items-center gap-3 border-b p-4 bg-white dark:bg-slate-900"><button className="lg:hidden" aria-label="Ouvrir le menu" onClick={() => setOpen(true)}><Menu /></button><span className="flex-1">{subscription?.workspace_name || 'Radar'}</span><BackgroundTasksIndicator /><NotificationCenter /><OnboardingTrigger /><ThemeToggle /></header>
      <main className="p-4 sm:p-6 pb-24 lg:pb-6 max-w-screen-2xl mx-auto">
        {isLoading ? <p role="status">Chargement des accès…</p> : error ? <div role="alert"><p>{error}</p><button onClick={() => fetchSubscription(selectedWorkspace())} className="underline mt-2">Réessayer</button></div> : <RouteGuard pathname={pathname}>{children}</RouteGuard>}
      </main>
    </div>
    <MobileBottomNav /><OnboardingTour /><WelcomeModal />
  </div>;
}
export function AppLayout({ children }: { children: React.ReactNode }) {
  return <OnboardingProvider><AppLayoutInner>{children}</AppLayoutInner></OnboardingProvider>;
}
export default AppLayout;

export const AppLayoutWithOnboarding = AppLayout;
