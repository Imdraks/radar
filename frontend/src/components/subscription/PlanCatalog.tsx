'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PlanInfo, Plan } from '@/store/subscriptionStore';
export function PlanCatalog({ onRequest, currentPlan }: { onRequest?: (plan: Plan) => Promise<void>; currentPlan?: Plan }) {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [error, setError] = useState(false);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    workspaceFetch('/api/v1/subscription/plans', { signal: controller.signal }).then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(setPlans).catch(e => { if (e.name !== 'AbortError') setError(true); });
    return () => controller.abort();
  }, []);
  return <div className="space-y-6">
    {error && <p role="alert">Catalogue indisponible. Réessayez ultérieurement ou contactez notre équipe.</p>}
    {!error && !plans.length && <p role="status">Chargement des offres…</p>}
    <div className="grid md:grid-cols-3 gap-5">{plans.map(plan => <article key={plan.name} className="rounded-xl border p-6 bg-white dark:bg-slate-900 space-y-4">
      <h3 className="text-xl font-semibold">{plan.display_name}</h3><p>{plan.description}</p>
      <p className="text-sm text-gray-500">Conditions tarifaires sur demande</p>
      <ul className="space-y-2">{plan.features_bullets.map(b => <li key={b}>✓ {b}</li>)}</ul>
      {currentPlan === plan.name ? <p className="font-medium">Abonnement actif</p> : onRequest ? <button disabled={pending} className="rounded bg-purple-700 text-white px-4 py-2 disabled:opacity-50" onClick={async () => { setPending(true); try { await onRequest(plan.name); } finally { setPending(false); } }}>Demander cet abonnement</button> : <Link className="block underline" href={`/contact?plan=${plan.name}`}>Contacter l’équipe</Link>}
    </article>)}</div>
    <p className="text-sm">Radar Addons : extensions spécifiques et outils sur mesure après accord commercial. Offre complémentaire aux abonnements.</p>
  </div>;
}
