'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, LogOut, ChevronLeft, ChevronRight, Building2, ShieldCheck } from 'lucide-react';
import { Portal as TooltipPortal } from '@radix-ui/react-tooltip';
import { useAuthStore } from '@/store/auth';
import { useSubscriptionStore, selectedWorkspace, navigationMatches } from '@/store/subscriptionStore';
import { RouteGuard } from '@/components/access/RouteGuard';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle, SheetDescription, SheetTrigger } from '@/components/ui/sheet';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { BackgroundTasksIndicator } from '@/components/tasks/BackgroundTasksIndicator';
import { OnboardingProvider, OnboardingTour, OnboardingTrigger, WelcomeModal } from '@/components/onboarding';
import { MobileBottomNav } from './MobileBottomNav';
import { NavigationIcon } from './navigation-icons';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import { LegacyToolNotice } from '@/components/product/LegacyTools';

function SidebarHint({ label, compact, children }: { label: string; compact: boolean; children: React.ReactElement }) {
  if (!compact) return children;
  return <Tooltip><TooltipTrigger asChild>{children}</TooltipTrigger><TooltipPortal><TooltipContent side="right" sideOffset={12}>{label}</TooltipContent></TooltipPortal></Tooltip>;
}

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { navigation, subscription, isLoading, error, fetchSubscription, setAdmin } = useSubscriptionStore();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    try { setCollapsed(localStorage.getItem('radar-sidebar-collapsed') === 'true'); } catch { /* Storage can be unavailable. */ }
  }, []);
  const toggleSidebar = () => {
    const next = !collapsed;
    setCollapsed(next);
    try { localStorage.setItem('radar-sidebar-collapsed', String(next)); } catch { /* The control still works without persistence. */ }
  };
  const activeItem = Object.values(navigation || {}).flat().sort((a, b) => b.path.length - a.path.length)
    .find(item => navigationMatches(item, pathname));
  const activeContext = [...(activeItem?.context_links || [])].sort((a, b) => b.path.length - a.path.length)
    .find(link => pathname === link.path || pathname.startsWith(link.path + '/'));
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

  const renderSidebar = (compact = false, mobile = false) => <div className="radar-sidebar flex h-full flex-col">
    <Link href="/today" aria-label="Radar — Accueil" onClick={() => setOpen(false)} className={`flex shrink-0 items-center gap-3 py-6 text-foreground hover:no-underline ${compact ? 'justify-center px-2' : 'px-6'}`}>
      <span><RadarLogo compact={compact} />{!compact && <span className="mt-2 block text-[10px] tracking-wide text-muted-foreground">Le point de repère de votre agence</span>}</span>
    </Link>
    {!compact && <div className="mx-4 mb-5 flex shrink-0 items-center gap-3 rounded-2xl border bg-card px-3.5 py-3.5 shadow-sm">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/5 text-primary"><Building2 size={17} /></span>
      <div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Espace de travail</p><p className="truncate text-sm font-medium text-foreground" title={subscription?.workspace_name}>{subscription?.workspace_name || 'Votre agence'}</p></div>
    </div>}
    <nav id={mobile ? undefined : 'radar-desktop-navigation'} aria-label="Navigation principale" className={`min-h-0 flex-1 space-y-4 overflow-y-auto pb-5 scrollbar-thin ${compact ? 'px-2' : 'px-4'}`}>
      {Object.entries(navigation || {}).filter(([, items]) => items.length > 0).map(([section, items]) => <div key={section} className="radar-nav-section">
        <p className={compact ? 'sr-only' : 'mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.13em] text-muted-foreground'}>{section}</p>
        <div className="space-y-1">{items.map(item => <SidebarHint key={item.path} label={item.label} compact={compact}><Link href={item.path} onClick={() => setOpen(false)} aria-current={activeItem?.path === item.path ? 'page' : undefined}
          className={`radar-nav-link ${compact ? 'justify-center px-0' : ''} ${activeItem?.path === item.path ? 'radar-nav-active' : ''}`}>
          <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${activeItem?.path === item.path ? 'bg-primary/10 text-primary' : ''}`}><NavigationIcon name={item.icon} /></span><span className={compact ? 'sr-only' : 'min-w-0 flex-1'}>{item.label}</span>
          {!compact && activeItem?.path === item.path && <ChevronRight size={14} className="shrink-0 text-primary" aria-hidden="true" />}
        </Link></SidebarHint>)}</div>
      </div>)}
      {user?.is_superuser && <SidebarHint label="Administration plateforme" compact={compact}><Link className={`radar-nav-link ${compact ? 'justify-center px-0' : ''}`} href="/admin"><ShieldCheck size={18} /><span className={compact ? 'sr-only' : ''}>Administration plateforme</span></Link></SidebarHint>}
    </nav>
    {compact ? <div className="flex shrink-0 flex-col items-center gap-2 border-t bg-card/60 px-2 py-3">
      <SidebarHint compact label="Déconnexion"><Button variant="ghost" size="icon" aria-label="Déconnexion" onClick={() => { useSubscriptionStore.getState().reset(); logout(); }}><LogOut size={17} /></Button></SidebarHint>
    </div> : <div className="shrink-0 border-t bg-card/60 p-4">
      <div className="flex items-center gap-3 rounded-xl border bg-card px-2.5 py-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-xs font-semibold text-primary">{initials}</span><div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-foreground">{user?.full_name || 'Mon compte'}</p><p className="truncate text-[10px] text-muted-foreground" title={user?.email}>{user?.email}</p></div>
        <Button variant="ghost" size="icon" aria-label="Déconnexion" title="Déconnexion" onClick={() => { useSubscriptionStore.getState().reset(); logout(); }}><LogOut size={17} /></Button>
      </div>
    </div>}
  </div>;

  return <div className="radar-app min-h-screen bg-background text-foreground">
    <a href="#radar-main" className="sr-only z-[100] rounded-lg bg-primary p-3 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Aller au contenu</a>
    <aside data-onboarding="sidebar" className={`fixed inset-y-0 left-0 z-40 hidden border-r lg:block ${collapsed ? 'w-[80px]' : 'w-[280px]'}`}>
      <Button variant="outline" size="icon" className="absolute -right-3.5 top-7 z-50 h-7 w-7 rounded-full bg-card shadow-sm" aria-label={collapsed ? 'Déplier la barre latérale' : 'Rétracter la barre latérale'} aria-expanded={!collapsed} aria-controls="radar-desktop-navigation" onClick={toggleSidebar}>{collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}</Button>
      {renderSidebar(collapsed)}
    </aside>
    <div className={`min-w-0 ${collapsed ? 'lg:pl-[80px]' : 'lg:pl-[280px]'}`}>
      <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between gap-2 border-b bg-card/95 px-4 backdrop-blur-md sm:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild><Button variant="ghost" size="icon" className="lg:hidden shrink-0" aria-label="Ouvrir le menu"><Menu size={21} /></Button></SheetTrigger>
            <SheetContent side="left" className="radar-app w-[min(310px,90vw)] p-0 bg-card" closeLabel="Fermer le menu" aria-describedby="radar-menu-description">
              <SheetTitle className="sr-only">Navigation Radar</SheetTitle><SheetDescription id="radar-menu-description" className="sr-only">Accéder aux outils de votre agence.</SheetDescription>{renderSidebar(false, true)}
            </SheetContent>
          </Sheet>
          <div className="flex min-w-0 items-center gap-2 text-sm"><span className="hidden text-muted-foreground sm:inline">{activeSection || 'Votre espace'}</span><ChevronRight size={14} className="hidden shrink-0 text-muted-foreground/60 sm:block" /><span className="truncate font-medium">{activeContext?.label || activeItem?.label || 'Radar'}</span></div>
        </div>
        <div className="flex shrink-0 items-center gap-0.5 sm:gap-1"><BackgroundTasksIndicator /><NotificationCenter /><OnboardingTrigger /><ThemeToggle /><Link href="/settings" aria-label="Paramètres du compte" className="ml-1 hidden h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary sm:flex">{initials}</Link></div>
      </header>
      <main id="radar-main" tabIndex={-1} className="radar-content mx-auto max-w-[1520px] px-4 py-6 pb-28 outline-none sm:px-8 sm:py-8 lg:px-10 lg:pb-10">
        {isLoading ? <div role="status" className="rounded-2xl border bg-card p-8 text-sm text-muted-foreground">Chargement de votre espace…</div> : error ? <div role="alert" className="rounded-2xl border bg-card p-6"><p>{error}</p><Button onClick={() => fetchSubscription(selectedWorkspace())} variant="outline" className="mt-4">Réessayer</Button></div> : <RouteGuard pathname={pathname}>
          {(activeItem?.context_links?.length || 0) > 1 && <nav aria-label={`Parcours ${activeItem?.label}`} className="mb-7 flex flex-wrap gap-1.5 rounded-2xl border bg-card p-1.5">{activeItem?.context_links?.map(link => <Link key={link.path} href={link.path} aria-current={activeContext?.path === link.path ? 'page' : undefined} className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${activeContext?.path === link.path ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-secondary'}`}><NavigationIcon name={link.icon} className="h-4 w-4" />{link.label}</Link>)}</nav>}
          <LegacyToolNotice pathname={pathname} />{children}
        </RouteGuard>}
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
