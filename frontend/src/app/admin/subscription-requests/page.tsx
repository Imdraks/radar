'use client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ProtectedRoute, AdminLayout } from '@/components/layout';
import { useAuthStore } from '@/store/auth';
import { subscriptionFetch } from '@/store/subscriptionStore';
interface Request { id: number; workspace_id: number; kind: string; requested_value: string; status: string; }
function Requests() {
  const user = useAuthStore(s => s.user);
  const cache = useQueryClient();
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const { data, isLoading, isError } = useQuery<Request[]>({ queryKey: ['subscription-requests'], queryFn: () => subscriptionFetch('admin/requests'), enabled: user?.is_superuser === true });
  if (!user?.is_superuser) return <p>Accès réservé à l’administration de plateforme.</p>;
  return <div className="space-y-5"><h1 className="text-2xl font-semibold">Demandes d’abonnement</h1><p>Une approbation attribue les droits. Elle ne constitue pas une confirmation de paiement. Renseignez la référence de l’accord administratif ou commercial vérifié.</p>
    {message && <p role="status">{message}</p>}{isLoading ? <p>Chargement…</p> : isError ? <p role="alert">Demandes indisponibles.</p> : !data?.length ? <p>Aucune demande en attente.</p> : data.map(request => <form key={request.id} className="border rounded-xl p-4 space-y-3" onSubmit={async e => {
      e.preventDefault(); const form = new FormData(e.currentTarget); setPending(true);
      try { await subscriptionFetch(`admin/requests/${request.id}/decision`, undefined, { method: 'POST', body: JSON.stringify({ approve: form.get('decision') === 'approve', authorization_reference: form.get('reference') }) }); setMessage('Décision enregistrée.'); await cache.invalidateQueries({ queryKey: ['subscription-requests'] }); }
      catch { setMessage('Décision non enregistrée. Vérifiez que la demande est toujours en attente.'); }
      finally { setPending(false); }
    }}><h2>Workspace {request.workspace_id} · {request.kind} · {request.requested_value}</h2><label className="block">Référence d’autorisation<input required minLength={5} maxLength={2000} name="reference" className="block border rounded p-2 w-full text-black" /></label>
      <select name="decision" className="border rounded p-2 text-black"><option value="reject">Refuser</option>{request.kind === 'plan' && <option value="approve">Approuver et activer les droits</option>}</select><button disabled={pending} className="block rounded bg-purple-700 text-white p-2 disabled:opacity-50">Enregistrer la décision</button>
      {request.kind === 'addon' && <p>Les extensions nécessitent une livraison et des droits spécifiques validés séparément.</p>}
    </form>)}
  </div>;
}
export default function RequestsPage() { return <ProtectedRoute><AdminLayout><Requests /></AdminLayout></ProtectedRoute>; }
