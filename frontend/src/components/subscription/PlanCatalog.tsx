'use client';
import { workspaceFetch } from '@/lib/workspace-fetch';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Check, CheckCircle2, LayoutGrid, Sparkles, Briefcase, ArrowUpRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PlanInfo, Plan } from '@/store/subscriptionStore';

const planIcons = { core: LayoutGrid, premium: Sparkles, business: Briefcase };

export function PlanCatalog({ onRequest, currentPlan }: { onRequest?: (plan: Plan) => Promise<void>; currentPlan?: Plan }) {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [error, setError] = useState(false);
  const [pending, setPending] = useState<Plan | null>(null);
  const currentFeatures = plans.find(plan => plan.name === currentPlan)?.available_features;
  useEffect(() => {
    const controller = new AbortController();
    workspaceFetch('/api/v1/subscription/plans', { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setPlans).catch(e => { if (e.name !== 'AbortError') setError(true); });
    return () => controller.abort();
  }, []);

  return <div className="space-y-5">
    {error && <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Catalogue indisponible. Réessayez ultérieurement ou contactez notre équipe.</p>}
    {!error && !plans.length && <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 size={16} className="animate-spin" />Chargement des offres…</p>}
    <div className="grid gap-5 xl:grid-cols-3">{plans.map(plan => {
      const isCurrent = currentPlan === plan.name;
      const isIncluded = Boolean(currentFeatures?.length && plan.available_features?.length && plan.available_features.every(feature => currentFeatures.includes(feature)));
      const Icon = planIcons[plan.name] || LayoutGrid;
      return <article key={plan.name} className={`relative flex flex-col overflow-hidden rounded-2xl border bg-card p-6 shadow-sm ${isCurrent ? 'border-primary/40 ring-1 ring-primary/10' : 'border-border'}`}>
        {isCurrent && <div className="absolute inset-x-0 top-0 h-1 bg-primary" />}
        <div className="mb-6 flex items-center justify-between gap-2"><span className={`flex h-11 w-11 items-center justify-center rounded-xl ${isCurrent ? 'bg-primary/10 text-primary' : 'bg-secondary text-muted-foreground'}`}><Icon size={21} strokeWidth={1.7} /></span>{isCurrent && <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-semibold text-primary">Votre offre</span>}</div>
        <h3 className="text-xl font-semibold tracking-tight">{plan.display_name}</h3>
        <p className="mt-2 min-h-[42px] text-sm leading-relaxed text-muted-foreground">{plan.description}</p>
        <p className="my-5 border-b pb-5 text-xs text-muted-foreground">Conditions tarifaires sur demande</p>
        <ul className="mb-8 flex-1 space-y-3">{plan.features_bullets.map(b => <li key={b} className="flex items-start gap-2.5 text-sm leading-relaxed"><Check size={16} className="mt-0.5 shrink-0 text-primary" /><span>{b}</span></li>)}</ul>
        {isCurrent || isIncluded ? <p className="flex min-h-10 items-center justify-center gap-2 rounded-xl bg-green-50 px-3 py-2.5 text-sm font-medium text-green-700 dark:bg-green-950/40 dark:text-green-400"><CheckCircle2 size={16} />{isCurrent ? 'Abonnement actif' : 'Déjà inclus'}</p>
          : onRequest ? <Button disabled={pending !== null} className="w-full gap-2" variant="outline" onClick={async () => { setPending(plan.name); try { await onRequest(plan.name); } finally { setPending(null); } }}>{pending === plan.name ? <Loader2 size={16} className="animate-spin" /> : null}Demander cet abonnement<ArrowUpRight size={15} /></Button>
            : <Button asChild variant="outline" className="w-full"><Link href={`/contact?plan=${plan.name}`}>Contacter l’équipe<ArrowUpRight size={15} className="ml-2" /></Link></Button>}
      </article>;
    })}</div>
    <p className="text-xs leading-relaxed text-muted-foreground">Radar Addons : extensions spécifiques et outils sur mesure après accord commercial. Offre complémentaire aux abonnements.</p>
  </div>;
}
