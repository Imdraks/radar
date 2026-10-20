'use client';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useSubscriptionStore } from '@/store/subscriptionStore';
export function EventExpenses({ eventId }: { eventId: number }) {
  const enabled = useSubscriptionStore(s => s.hasFeature('invoices'));
  const workspaceId = useSubscriptionStore(s => s.subscription?.workspace_id);
  const cache = useQueryClient();
  const [message, setMessage] = useState('');
  const [pending,setPending] = useState(false);
  const { data, isError, isLoading } = useQuery<{id:number; description:string; amount:string}[]>({queryKey:['event-expenses',workspaceId,eventId],queryFn:async()=>(await api.get(`/events/${eventId}/expenses`)).data,enabled});
  if (!enabled) return <p className="text-sm">Le suivi des dépenses nécessite Radar Business.</p>;
  return <div className="space-y-2"><h3 className="font-medium">Dépenses enregistrées</h3>
    {isLoading ? <p>Chargement…</p> : isError ? <p role="alert">Dépenses indisponibles.</p> : !data?.length ? <p>Aucune dépense enregistrée.</p> : data.map(expense=><p key={expense.id}>{expense.description} · {expense.amount} €</p>)}
    <form className="flex flex-wrap gap-2" onSubmit={async e=>{e.preventDefault();const form=e.currentTarget;const values=new FormData(form);setPending(true);try{await api.post(`/events/${eventId}/expenses`,{description:values.get('description'),amount:values.get('amount')});form.reset();setMessage('Dépense enregistrée.');await cache.invalidateQueries({queryKey:['event-expenses',workspaceId,eventId]});}catch{setMessage('Impossible d’enregistrer la dépense.');}finally{setPending(false);}}}>
      <label>Prestation ou dépense<input name="description" required maxLength={500} className="block border rounded p-2 text-black" /></label><label>Montant (€)<input name="amount" required type="number" min="0" step="0.01" className="block border rounded p-2 text-black" /></label><button disabled={pending} className="underline disabled:opacity-50">Enregistrer</button>
    </form>{message&&<p role="status">{message}</p>}
  </div>;
}
