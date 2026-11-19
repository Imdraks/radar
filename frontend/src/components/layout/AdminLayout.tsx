'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { Building2, Users, Activity, Settings, Shield, LogOut, LayoutDashboard, Rss, HeartPulse, Menu, ChevronDown, ShoppingCart, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { RadarLogo } from '@/components/brand/RadarBrand';

const navigation = [
  { name: 'Vue d’ensemble', href: '/admin', icon: LayoutDashboard },
  { name: 'Entreprises clientes', href: '/admin/clients', icon: Building2 },
  { name: 'Commandes', href: '/admin/orders', icon: ShoppingCart },
  { name: 'Utilisateurs', href: '/users', icon: Users },
  { name: 'Contrats et éditeur', href: '/admin/legal', icon: Shield },
  { name: 'Demandes RGPD', href: '/admin/privacy-requests', icon: Shield },
  { name: 'Journal d’activité', href: '/admin/activity', icon: Activity },
];
const technical = [
  { name: 'Sources', href: '/sources', icon: Rss },
  { name: 'État des sources', href: '/source-health', icon: HeartPulse },
];
const matches = (path: string, current: string) => current === path || (path !== '/admin' && current.startsWith(path + '/'));

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [mobile, setMobile] = useState(false);
  const [tools, setTools] = useState(() => technical.some(item => matches(item.href, pathname)));
  useEffect(() => { if (user && !user.is_superuser) router.replace('/today'); }, [user, router]);
  useEffect(() => {
    const viewport = window.matchMedia('(min-width: 1024px)');
    const close = () => { if (viewport.matches) setMobile(false); };
    viewport.addEventListener('change', close);
    return () => viewport.removeEventListener('change', close);
  }, []);
  if (!user?.is_superuser) return null;
  const active = [...navigation, ...technical].find(item => matches(item.href, pathname));
  const sidebar = (isMobile = false) => <div className="flex h-full flex-col">
    <Link href="/admin" className="px-6 pb-5 pt-7" onClick={() => setMobile(false)}><RadarLogo /><span className="mt-3 block text-[10px] font-semibold uppercase tracking-[.16em] text-muted-foreground">Administration de plateforme</span></Link>
    <nav aria-label="Administration de plateforme" className="min-h-0 flex-1 space-y-1 overflow-y-auto px-4 py-3">
      {navigation.map(item => <Link key={item.href} href={item.href} onClick={() => setMobile(false)} aria-current={matches(item.href, pathname) ? 'page' : undefined} className={cn('flex min-h-11 items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors', matches(item.href, pathname) ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-secondary hover:text-foreground')}><item.icon size={18} className="shrink-0" /><span>{item.name}</span></Link>)}
      <div className="pb-2 pt-5"><button type="button" className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-muted-foreground hover:bg-secondary" aria-expanded={tools} aria-controls={isMobile ? 'admin-mobile-tools' : 'admin-desktop-tools'} onClick={() => setTools(value => !value)}><Settings size={17} /><span className="flex-1 text-left">Outils techniques</span><ChevronDown size={15} className={tools ? 'rotate-180' : ''} /></button>{tools && <div id={isMobile ? 'admin-mobile-tools' : 'admin-desktop-tools'} className="ml-5 mt-1 space-y-1 border-l pl-3">{technical.map(item => <Link key={item.href} href={item.href} onClick={() => setMobile(false)} aria-current={matches(item.href, pathname) ? 'page' : undefined} className={cn('flex items-center gap-3 rounded-lg px-3 py-3 text-xs', matches(item.href, pathname) ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary')}><item.icon size={15} />{item.name}</Link>)}</div>}</div>
    </nav>
    <footer className="space-y-2 border-t p-4"><div className="mb-3 rounded-xl bg-secondary/60 px-3 py-3"><p className="truncate text-sm font-medium">{user.full_name || 'Mon compte'}</p><p className="mt-1 truncate text-xs text-muted-foreground">{user.email}</p></div><Link href="/account/security" className="flex items-center gap-3 rounded-xl px-3 py-2 text-xs text-muted-foreground hover:bg-secondary"><Settings size={16} />Sécurité de mon compte</Link><Link href="/account/workspaces" className="flex items-center gap-3 rounded-xl px-3 py-2 text-xs text-muted-foreground hover:bg-secondary"><ArrowLeft size={16} />Mes espaces de travail</Link><Button variant="ghost" className="w-full justify-start gap-3" onClick={() => { logout(); router.replace('/login'); }}><LogOut size={16} />Déconnexion</Button></footer>
  </div>;
  return <div className="radar-admin flex h-dvh min-h-0 bg-background text-foreground">
    <aside className="hidden w-[260px] shrink-0 border-r bg-card lg:block">{sidebar()}</aside>
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden"><header className="flex min-h-[72px] shrink-0 items-center justify-between gap-3 border-b bg-card px-4 sm:px-8"><div className="flex min-w-0 items-center gap-3"><Sheet open={mobile} onOpenChange={setMobile}><SheetTrigger asChild><Button variant="ghost" size="icon" className="shrink-0 lg:hidden" aria-label="Ouvrir le menu administration"><Menu size={20} /></Button></SheetTrigger><SheetContent side="left" closeLabel="Fermer le menu administration" className="radar-admin w-[min(310px,90vw)] bg-card p-0"><SheetTitle className="sr-only">Navigation de l’administration</SheetTitle><SheetDescription className="sr-only">Entreprises clientes, commandes, contrats et utilisateurs.</SheetDescription>{sidebar(true)}</SheetContent></Sheet><p className="truncate text-sm font-medium">{active?.name || 'Administration Radar'}</p></div><ThemeToggle /></header><main className="min-w-0 flex-1 overflow-y-auto bg-background">{children}</main></div>
  </div>;
}
export default AdminLayout;
