'use client';
import { useState } from 'react';
import { AppLayout, ProtectedRoute } from '@/components/layout';
import { PlanCatalog } from '@/components/subscription/PlanCatalog';
import { useSubscriptionStore, subscriptionFetch } from '@/store/subscriptionStore';
export default function SubscriptionPage() {
  const { subscription, changePlan } = useSubscriptionStore();
  const [message, setMessage] = useState('');
  const [addon, setAddon] = useState('');
  return <ProtectedRoute><AppLayout><div className="space-y-6">
    <h1 className="text-3xl font-semibold">Abonnement</h1>
    <p>{subscription?.plan_display_name} · {subscription?.current_seats} membre(s)</p>
    <p>Les demandes sont examinées par notre équipe. Les droits changent uniquement après autorisation administrative.</p>
    {message && <p role="status">{message}</p>}
    <PlanCatalog currentPlan={subscription?.plan} onRequest={async plan => {
      const ok = await changePlan(plan);
      setMessage(ok ? 'Demande enregistrée. Votre abonnement actif reste inchangé en attendant sa validation.' : 'Demande refusée ou service indisponible. Vérifiez vos permissions.');
    }} />
    <form className="space-y-3 border rounded-lg p-4" onSubmit={async e => {
      e.preventDefault();
      try { await subscriptionFetch('addon-requests', subscription?.workspace_id, { method: 'POST', body: JSON.stringify({ description: addon }) }); setMessage('Demande Radar Addons enregistrée.'); }
      catch { setMessage('Impossible d’enregistrer cette demande.'); }
    }}><label htmlFor="addon">Besoin d’une extension spécifique ?</label><input id="addon" required minLength={3} maxLength={100} value={addon} onChange={e => setAddon(e.target.value)} className="block border rounded p-2 w-full text-black" /><button className="underline" type="submit">Envoyer une demande Radar Addons</button></form>
  </div></AppLayout></ProtectedRoute>;
}
