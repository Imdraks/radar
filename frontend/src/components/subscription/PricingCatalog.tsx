'use client';

import Link from 'next/link';
import { ArrowDown, ArrowUpRight, Check, HelpCircle, Minus, Users } from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { Button } from '@/components/ui/button';
import type { Feature, Plan, PlanInfo } from '@/store/subscriptionStore';

// Presentation only: inclusions and limits come from /subscription/plans.
const groups: { title: string; rows: { feature: Feature; label: string; description: string }[] }[] = [
  { title: 'Organisation & production', rows: [
    { feature: 'cockpit', label: 'Vue d’ensemble', description: 'Retrouvez les priorités et l’activité de votre espace.' },
    { feature: 'projects', label: 'Projets', description: 'Structurez vos projets, leurs étapes et leurs responsables.' },
    { feature: 'production', label: 'Tâches & production', description: 'Organisez le travail de l’équipe et suivez son avancement.' },
    { feature: 'calendar', label: 'Planning & calendrier', description: 'Gardez vos échéances et votre planning à portée de vue.' },
    { feature: 'assets', label: 'Fichiers & livrables', description: 'Rassemblez les ressources et les livrables de vos projets.' },
  ] },
  { title: 'Événements & intelligence artistique', rows: [
    { feature: 'events', label: 'Gestion événementielle', description: 'Préparez vos événements et organisez leur production.' },
    { feature: 'discovery', label: 'Discovery', description: 'Explorez des artistes pour vos prochains projets.' },
    { feature: 'spotify_search', label: 'Recherche Spotify', description: 'Recherchez des artistes depuis le parcours Discovery.' },
    { feature: 'profiles', label: 'Profils artistiques', description: 'Consultez les informations disponibles sur les artistes.' },
    { feature: 'comparison', label: 'Comparaison d’artistes', description: 'Mettez plusieurs profils en perspective avant de choisir.' },
    { feature: 'analytics', label: 'Analyses artistiques', description: 'Consultez les indicateurs disponibles pour éclairer vos choix.' },
  ] },
  { title: 'Gestion commerciale', rows: [
    { feature: 'clients', label: 'Clients & contacts', description: 'Centralisez les informations de vos relations commerciales.' },
    { feature: 'leads', label: 'Prospects', description: 'Organisez vos opportunités et leur suivi commercial.' },
    { feature: 'crm_extended', label: 'CRM avancé', description: 'Retrouvez le contexte et l’historique de vos échanges clients.' },
    { feature: 'quotes', label: 'Devis', description: 'Préparez vos propositions et suivez leur cycle de vie.' },
    { feature: 'invoices', label: 'Factures & suivi des paiements', description: 'Gérez vos factures et suivez les paiements enregistrés.' },
  ] },
];

const presentation: Record<Plan, { audience: string }> = {
  core: { audience: 'Pour une équipe qui veut mieux s’organiser.' },
  premium: { audience: 'Pour les agences qui produisent et créent des événements.' },
  business: { audience: 'Pour relier la production à la gestion commerciale.' },
};

function Inclusion({ plan, feature }: { plan: PlanInfo; feature: Feature }) {
  if (!plan.available_features) return <span className="text-xs text-muted-foreground">Non renseigné</span>;
  return plan.available_features.includes(feature)
    ? <span className="inline-flex rounded-full bg-primary/10 p-1.5 text-primary"><Check size={16} aria-hidden="true" /><span className="sr-only">Inclus</span></span>
    : <span className="inline-flex text-muted-foreground"><Minus size={17} aria-hidden="true" /><span className="sr-only">Non inclus</span></span>;
}

export function PricingCatalog({ plans, error, onRetry }: { plans: PlanInfo[]; error: boolean; onRetry: () => void }) {
  if (error) return <div role="alert" className="rounded-3xl border bg-white p-8 text-center"><p className="font-medium">Les offres sont momentanément indisponibles.</p><p className="mt-2 text-sm text-muted-foreground">Réessayez ou contactez notre équipe pour connaître le périmètre adapté à votre agence.</p><div className="mt-5 flex flex-wrap justify-center gap-3"><Button variant="outline" onClick={onRetry}>Réessayer</Button><Button asChild><Link href="/contact">Contacter l’équipe</Link></Button></div></div>;
  if (!plans.length) return <div role="status" className="flex min-h-72 items-center justify-center gap-3 rounded-3xl border bg-white text-muted-foreground"><RadarSpinner className="animate-spin" size={20} aria-hidden="true" />Chargement des offres…</div>;

  const ordered = [...plans].sort((a, b) => ['core', 'premium', 'business'].indexOf(a.name) - ['core', 'premium', 'business'].indexOf(b.name));
  return <>
    <div className="grid items-stretch gap-5 lg:grid-cols-3">
      {ordered.map(plan => {
        const info = presentation[plan.name];
        const highlighted = plan.name === 'premium';
        return <article key={plan.name} aria-labelledby={`offer-${plan.name}`} className={`flex min-w-0 flex-col rounded-3xl border bg-white shadow-sm ${highlighted ? 'border-primary/35 shadow-[0_16px_60px_-32px_hsl(var(--primary)/0.3)]' : 'border-border/75'}`}>
          <div className="flex flex-1 flex-col px-6 pb-6 pt-8 sm:px-8 sm:pt-10">
            <h2 id={`offer-${plan.name}`} className={`text-2xl font-medium tracking-tight lg:text-3xl ${highlighted ? 'text-primary' : 'text-foreground'}`}>{plan.display_name}</h2>
            <p className="mt-3 min-h-12 text-sm leading-6 text-muted-foreground">{info?.audience || plan.description}</p>
            <div className="mt-7">
              <p className="text-[clamp(2rem,3.2vw,2.75rem)] font-light leading-tight tracking-tight text-foreground">Sur demande</p>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">Conditions tarifaires à définir avec notre équipe</p>
            </div>
            <Button asChild className="mt-7 h-12 w-full gap-2 rounded-full border-2 border-primary bg-primary px-4 text-sm font-medium text-white shadow-none transition-colors hover:bg-transparent hover:text-primary focus-visible:ring-primary motion-reduce:transition-none"><Link href={`/contact?plan=${plan.name}`}>Parlons de {plan.display_name.replace('Radar ', '')}<ArrowUpRight size={16} aria-hidden="true" /></Link></Button>
          </div>
          <div className="mx-6 border-t border-border/70 pb-7 pt-5 sm:mx-8 sm:pb-8">
            <p className="text-xs font-medium text-muted-foreground">{plan.description}</p>
            <ul className="mt-4 space-y-3">{plan.features_bullets.map(bullet => <li key={bullet} className="flex items-start gap-2.5 text-sm leading-6"><Check size={15} className="mt-1 shrink-0 text-primary" aria-hidden="true" /><span>{bullet}</span></li>)}</ul>
            <p className="mt-5 flex items-center gap-2 text-xs text-muted-foreground"><Users size={14} className="shrink-0" aria-hidden="true" />Jusqu’à {plan.max_seats} membres dans votre espace</p>
            <a href="#comparatif" className="mt-5 inline-flex items-center gap-2 text-xs font-medium text-primary underline-offset-4 hover:underline">Comparer les fonctionnalités<ArrowDown size={14} aria-hidden="true" /></a>
          </div>
        </article>;
      })}
    </div>
    <section id="comparatif" className="scroll-mt-28 pt-20 sm:pt-28" aria-labelledby="comparison-title">
      <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="radar-kicker">À chaque équipe, son périmètre</p><h2 id="comparison-title" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Tout ce qui fait la différence.</h2></div><p className="max-w-sm text-sm leading-6 text-muted-foreground">Repérez les outils inclus dans chaque offre et trouvez le périmètre qui correspond à votre équipe.</p></div>
      <p className="mt-5 text-xs text-muted-foreground lg:hidden">Faites défiler le tableau horizontalement pour comparer les trois offres.</p>
      <div role="region" aria-label="Comparatif des abonnements, défilement horizontal" tabIndex={0} className="relative mt-6 overflow-x-auto rounded-2xl border bg-white outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
        <table className="w-full min-w-[650px] border-collapse text-sm">
          <caption className="sr-only">Fonctionnalités et limites de chaque abonnement Radar</caption>
          <thead><tr className="border-b"><th scope="col" className="p-5 text-left font-medium text-muted-foreground">Fonctionnalités</th>{ordered.map(plan => <th key={plan.name} scope="col" className={`p-5 text-center font-semibold ${plan.name === 'premium' ? 'bg-primary/5 text-primary' : ''}`}>{plan.display_name}</th>)}</tr></thead>
          {groups.map(group => <tbody key={group.title}><tr><th colSpan={ordered.length + 1} scope="rowgroup" className="border-y bg-secondary/40 px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{group.title}</th></tr>{group.rows.map(row => <tr key={row.feature} className="border-b last:border-b-0"><th scope="row" className="px-5 py-4 text-left font-normal"><span className="block font-medium">{row.label}</span><span className="mt-1 block max-w-sm text-xs leading-5 text-muted-foreground">{row.description}</span></th>{ordered.map(plan => <td key={plan.name} className={`w-[19%] px-5 py-4 text-center ${plan.name === 'premium' ? 'bg-primary/[0.025]' : ''}`}><Inclusion plan={plan} feature={row.feature} /></td>)}</tr>)}</tbody>)}
          <tbody><tr className="border-t"><th scope="row" className="p-5 text-left font-medium">Membres par espace</th>{ordered.map(plan => <td key={plan.name} className="p-5 text-center font-medium">{plan.max_seats}</td>)}</tr></tbody>
        </table>
      </div>
      <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-muted-foreground"><HelpCircle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />Les données artistiques dépendent des sources disponibles et des intégrations configurées. Le suivi des paiements ne constitue pas une connexion bancaire ni un service de comptabilité générale.</p>
    </section>
  </>;
}
