'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { clientRequest, clientError, type ClientDetail, type Order } from '@/lib/platform-clients';

const plans = { core: 'Radar Core', premium: 'Radar Premium', business: 'Radar Business' };

export function ClientPlanSelector({ client, onReview }: {
  client: ClientDetail;
  onReview: (order: Order) => Promise<void>;
}) {
  const [selected, setSelected] = useState(client.plan);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setSelected(client.plan); setError(''); }, [client.id, client.plan]);

  const review = async () => {
    if (busy || selected === client.plan) return;
    setBusy(true); setError('');
    try {
      // Reuse the real request/decision workflow; this screen grants no rights itself.
      const latest = await clientRequest<ClientDetail>(`/${client.id}`);
      if (latest.plan === selected) { setError('Cette offre est déjà active. Actualisez la fiche.'); return; }
      let order = latest.orders.find(row => row.kind === 'plan' && row.value === selected && row.status === 'pending');
      if (!order) {
        try {
          const created = await clientRequest<{ id: number }>(`/${client.id}/orders`, 'POST', { kind: 'plan', value: selected });
          const updated = await clientRequest<ClientDetail>(`/${client.id}`);
          order = updated.orders.find(row => row.id === created.id);
        } catch (failure) {
          // Another administrator may have prepared the same request concurrently.
          if ((failure as { response?: { status: number } }).response?.status !== 409) throw failure;
          const updated = await clientRequest<ClientDetail>(`/${client.id}`);
          order = updated.orders.find(row => row.kind === 'plan' && row.value === selected && row.status === 'pending');
          if (!order) throw failure;
        }
      }
      if (!order) throw new Error('Request unavailable');
      await onReview(order);
    } catch (failure) { setError(clientError(failure)); }
    finally { setBusy(false); }
  };

  return <section aria-labelledby="client-plan-title" className="rounded-2xl border bg-card p-5 sm:p-6">
    <h2 id="client-plan-title" className="text-lg font-semibold">Changer l’offre</h2>
    <p className="mt-2 text-sm text-muted-foreground">Offre actuellement active : <strong className="text-foreground">{client.plan_display_name}</strong>.</p>
    <div className="mt-5 flex flex-col items-start gap-3 sm:flex-row sm:items-end">
      <div className="w-full space-y-2 sm:max-w-xs">
        <Label htmlFor="client-target-plan">Nouvelle offre</Label>
        <select id="client-target-plan" value={selected} disabled={busy} onChange={event => { setSelected(event.target.value); setError(''); }} className="h-11 w-full rounded-xl border bg-background px-3 text-sm">
          {Object.entries(plans).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
      <Button disabled={busy || selected === client.plan} onClick={review}>{busy ? 'Préparation…' : 'Appliquer la modification'}</Button>
    </div>
    <p className="mt-3 text-xs leading-6 text-muted-foreground">Vous confirmerez la modification avec sa preuve contractuelle et sa référence. Une commande en attente sera réutilisée ou créée ; l’offre reste inchangée jusqu’à la validation. Aucun paiement n’est déclaré par cette action.</p>
    {error && <p role="alert" className="mt-3 text-sm text-destructive">{error}</p>}
  </section>;
}
