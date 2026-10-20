'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, LogOut, Radar, ChevronRight, Building2, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { useSubscriptionStore, selectedWorkspace } from '@/store/subscriptionStore';
import { RouteGuard } from '@/components/access/RouteGuard';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle, SheetDescription, SheetTrigger } from '@/components/ui/sheet';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { BackgroundTasksIndicator } from '@/components/tasks/BackgroundTasksIndicator';
import { OnboardingProvider, OnboardingTour, OnboardingTrigger, WelcomeModal } from '@/components/onboarding';
import { MobileBottomNav } from './MobileBottomNav';
import { NavigationIcon } from './navigation-icons';

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { navigation, subscription, isLoading, error, fetchSubscription, setAdmin } = useSubscriptionStore();
  const [open, setOpen] = useState(false);
  const activeItem = Object.values(navigation || {}).flat().sort((a, b) => b.path.length - a.path.length)
    .find(item => pathname === item.path || pathname.startsWith(item.path + '/'));
  const activeSection = Object.entries(navigation || {}).find(([, items]) => items.some(item => item.path === activeItem?.path))?.[0];
  const initials = (user?.full_name || user?.email || 'R').split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  useEffect(() => {
    const refresh = () => { void fetchSubscription(selectedWorkspace()); };
    refresh();
    window.addEventListener('storage', refresh);
    window.addEventListener('workspace-changed', refresh);
    return () => { window.removeEventListener('storage', refresh); window.removeEventListener('workspace-changed', refresh); };
  }, [fetchSubscription, user?.id]);
  useEffect(() => setAdmin(user?.is_superuser === true), [user, setAdmin]);
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 1024px)');
    const closeOnDesktop = () => { if (desktop.matches) setOpen(false); };
    desktop.addEventListener('change', closeOnDesktop);
    return () => desktop.removeEventListener('change', closeOnDesktop);
  }, []);

  const sidebar = <div className="radar-sidebar flex h-full flex-col">
    <Link href="/today" onClick={() => setOpen(false)} className="flex shrink-0 items-center gap-3 px-6 py-6 text-foreground hover:no-underline">
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-white shadow-lg shadow-primary/20"><Radar size={26} strokeWidth={1.7} /></span>
      <span><span className="block text-[24px] font-semibold leading-tight tracking-tight">radar<span className="text-primary">.</span></span><span className="mt-0.5 block text-[11px] text-muted-foreground">Votre espace agence</span></span>
    </Link>
    <div className="mx-4 mb-5 flex shrink-0 items-center gap-3 rounded-2xl border bg-card px-3.5 py-3.5 shadow-sm">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/5 text-primary"><Building2 size={17} /></span>
      <div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Espace de travail</p><p className="truncate text-sm font-medium text-foreground" title={subscription?.workspace_name}>{subscription?.workspace_name || 'Votre agence'}</p></div>
    </div>
    <nav aria-label="Navigation principale" className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 pb-5 scrollbar-thin">
      {Object.entries(navigation || {}).filter(([, items]) => items.length > 0).map(([section, items]) => <div key={section} className="radar-nav-section">
        <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.13em] text-muted-foreground">{section}</p>
        <div className="space-y-1">{items.map(item => <Link key={item.path} href={item.path} onClick={() => setOpen(false)} aria-current={activeItem?.path === item.path ? 'page' : undefined}
          className={`radar-nav-link ${activeItem?.path === item.path ? 'radar-nav-active' : ''}`}>
          <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${activeItem?.path === item.path ? 'bg-primary/10 text-primary' : ''}`}><NavigationIcon name={item.icon} /></span><span className="min-w-0 flex-1">{item.label}</span>
          {activeItem?.path === item.path && <ChevronRight size={14} className="shrink-0 text-primary" aria-hidden="true" />}
        </Link>)}</div>
      </div>)}
      {user?.is_superuser && <Link className="radar-nav-link" href="/admin"><ShieldCheck size={18} />Administration plateforme</Link>}
    </nav>
    <div className="shrink-0 border-t bg-card/60 p-4">
      {subscription && <Link href="/settings/subscription" onClick={() => setOpen(false)} className="mb-3 flex items-center justify-between gap-2 rounded-xl border border-primary/15 bg-primary/5 px-3 py-2.5 text-primary hover:bg-primary/10 hover:no-underline"><span><span className="block text-[10px] text-muted-foreground">Votre abonnement</span><span className="text-xs font-semibold">{subscription.plan_display_name}</span></span><ChevronRight size={15} /></Link>}
      <div className="flex items-center gap-3 rounded-xl border bg-card px-2.5 py-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-xs font-semibold text-primary">{initials}</span><div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-foreground">{user?.full_name || 'Mon compte'}</p><p className="truncate text-[10px] text-muted-foreground" title={user?.email}>{user?.email}</p></div>
        <Button variant="ghost" size="icon" aria-label="Déconnexion" title="Déconnexion" onClick={() => { useSubscriptionStore.getState().reset(); logout(); }}><LogOut size={17} /></Button>
      </div>
    </div>
  </div>;

  return <div className="radar-app min-h-screen bg-background text-foreground">
    <a href="#radar-main" className="sr-only z-[100] rounded-lg bg-primary p-3 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Aller au contenu</a>
    <aside data-onboarding="sidebar" className="fixed inset-y-0 left-0 z-40 hidden w-[280px] border-r lg:block">{sidebar}</aside>
    <div className="min-w-0 lg:pl-[280px]">
      <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between gap-2 border-b bg-card/95 px-4 backdrop-blur-md sm:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild><Button variant="ghost" size="icon" className="lg:hidden shrink-0" aria-label="Ouvrir le menu"><Menu size={21} /></Button></SheetTrigger>
            <SheetContent side="left" className="radar-app w-[min(310px,90vw)] p-0 bg-card" closeLabel="Fermer le menu" aria-describedby="radar-menu-description">
              <SheetTitle className="sr-only">Navigation Radar</SheetTitle><SheetDescription id="radar-menu-description" className="sr-only">Accéder aux outils de votre agence.</SheetDescription>{sidebar}
            </SheetContent>
          </Sheet>
          <div className="flex min-w-0 items-center gap-2 text-sm"><span className="hidden text-muted-foreground sm:inline">{activeSection || 'Votre espace'}</span><ChevronRight size={14} className="hidden shrink-0 text-muted-foreground/60 sm:block" /><span className="truncate font-medium">{activeItem?.label || 'Radar'}</span></div>
        </div>
        <div className="flex shrink-0 items-center gap-0.5 sm:gap-1"><BackgroundTasksIndicator /><NotificationCenter /><OnboardingTrigger /><ThemeToggle /><Link href="/settings" aria-label="Paramètres du compte" className="ml-1 hidden h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary sm:flex">{initials}</Link></div>
      </header>
      <main id="radar-main" tabIndex={-1} className="radar-content mx-auto max-w-[1520px] px-4 py-6 pb-28 outline-none sm:px-8 sm:py-8 lg:px-10 lg:pb-10">
        {isLoading ? <div role="status" className="rounded-2xl border bg-card p-8 text-sm text-muted-foreground">Chargement de votre espace…</div> : error ? <div role="alert" className="rounded-2xl border bg-card p-6"><p>{error}</p><Button onClick={() => fetchSubscription(selectedWorkspace())} variant="outline" className="mt-4">Réessayer</Button></div> : <RouteGuard pathname={pathname}>{children}</RouteGuard>}
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
