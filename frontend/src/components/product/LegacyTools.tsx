'use client';
import Link from 'next/link';
import { Archive, ArrowUpRight } from 'lucide-react';
import { useSubscriptionStore, type Feature } from '@/store/subscriptionStore';

export const LEGACY_TOOLS: { path: string; label: string; description: string; feature: Feature; destination: string; destinationLabel: string }[] = [
  { path: '/analytics', label: 'Analyses territoriales', description: 'Anciennes analyses par zone, source et genre.', feature: 'analytics', destination: '/discovery', destinationLabel: 'Discovery' },
  { path: '/intelligence', label: 'Ancien fil d’intelligence', description: 'Informations issues des anciens parcours de veille.', feature: 'invoices', destination: '/discovery', destinationLabel: 'Discovery' },
  { path: '/profiles', label: 'Profils de recherche', description: 'Paramètres et critères des profils de veille existants.', feature: 'profiles', destination: '/discovery', destinationLabel: 'Discovery' },
  { path: '/shortlist', label: 'Sélections de veille', description: 'Historique des sélections générées par les profils de veille.', feature: 'daily_picks', destination: '/comparison', destinationLabel: 'Sélections artistiques' },
  { path: '/scoring', label: 'Règles de scoring historiques', description: 'Règles de qualification des opportunités de veille.', feature: 'scoring', destination: '/clients', destinationLabel: 'Clients et prospects' },
  { path: '/deadlines', label: 'Échéances de veille', description: 'Échéances issues des opportunités de veille historiques.', feature: 'calendar', destination: '/agency-calendar', destinationLabel: 'Calendrier de production' },
  { path: '/leads', label: 'Leads historiques', description: 'Opportunités conservées avec leurs fiches et leur historique.', feature: 'leads', destination: '/clients', destinationLabel: 'Clients et prospects' },
  { path: '/dossiers', label: 'Dossiers de veille', description: 'Dossiers et documents produits dans les anciens parcours.', feature: 'dossiers', destination: '/projects', destinationLabel: 'Projets' },
  { path: '/briefs', label: 'Briefs de veille', description: 'Briefs enregistrés et informations de collecte associées.', feature: 'dossiers', destination: '/projects', destinationLabel: 'Projets' },
];

export function LegacyToolNotice({ pathname }: { pathname: string }) {
  const tool = LEGACY_TOOLS.find(item => pathname === item.path || pathname.startsWith(item.path + '/'));
  if (!tool) return null;
  return <aside aria-label="Outil historique" className="mb-6 flex flex-col gap-3 rounded-2xl border bg-card p-4 text-sm sm:flex-row sm:items-start"><Archive size={18} className="mt-0.5 shrink-0 text-muted-foreground" /><div className="flex-1"><p className="font-medium text-foreground">Outil historique</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Cet espace reste accessible pour retrouver vos données et réglages. Le parcours principal est désormais {tool.destinationLabel}.</p></div><div className="flex flex-wrap gap-4 text-xs"><Link href={tool.destination} className="font-medium text-primary">Ouvrir {tool.destinationLabel}</Link><Link href="/settings/tools" className="text-muted-foreground">Tous les outils historiques</Link></div></aside>;
}

export function LegacyToolsCatalog() {
  const features = useSubscriptionStore(state => state.subscription?.available_features || []);
  const tools = LEGACY_TOOLS.filter(tool => features.includes(tool.feature));
  return <div className="space-y-7"><div><p className="radar-eyebrow mb-2">Administration</p><h1 className="text-3xl font-semibold tracking-tight">Outils historiques</h1><p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">Retrouvez les données et réglages de vos anciens parcours. Les projets, Discovery, les événements et la gestion commerciale restent accessibles depuis la navigation principale.</p></div>
    {tools.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{tools.map(tool => <Link key={tool.path} href={tool.path} className="rounded-2xl border bg-card p-5 transition-colors hover:border-primary/40"><Archive size={20} className="mb-5 text-muted-foreground" /><h2 className="flex items-center justify-between gap-2 text-base font-semibold">{tool.label}<ArrowUpRight size={15} /></h2><p className="mt-2 text-xs leading-relaxed text-muted-foreground">{tool.description}</p></Link>)}</div> : <p className="rounded-2xl border bg-card p-6 text-sm text-muted-foreground">Aucun outil historique n’est disponible avec vos droits actuels. Vos outils de travail restent dans la navigation principale.</p>}
  </div>;
}
