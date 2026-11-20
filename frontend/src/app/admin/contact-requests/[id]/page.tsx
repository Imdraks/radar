'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AdminLayout, ProtectedRoute } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { inquiryRequest, inquiryStatus, ackStatus, type ContactInquiry } from '@/lib/contact-inquiries';
import { clientDate, clientError } from '@/lib/platform-clients';

function Dossier() {
  const { id } = useParams<{ id: string }>();
  const cache = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const query = useQuery<ContactInquiry>({ queryKey: ['admin-contact', 'detail', id], queryFn: async () => {
    const row = await inquiryRequest<ContactInquiry>(`/${id}/open`, 'POST');
    void cache.invalidateQueries({ queryKey: ['admin-contact', 'count'] });
    void cache.invalidateQueries({ queryKey: ['admin-contact', 'list'] });
    return row;
  }, retry: false, refetchOnMount: 'always', refetchOnWindowFocus: false });
  const update = async (retry: boolean) => {
    if (busy || !query.data) return;
    setBusy(true); setError('');
    try {
      const row = retry ? await inquiryRequest<ContactInquiry>(`/${id}/retry-acknowledgement`, 'POST') : await inquiryRequest<ContactInquiry>(`/${id}`, 'PATCH', { status: query.data.status === 'closed' ? 'opened' : 'closed' });
      cache.setQueryData(['admin-contact', 'detail', id], row);
      await cache.invalidateQueries({ queryKey: ['admin-contact', 'list'] });
    } catch (failure) { setError(clientError(failure)); } finally { setBusy(false); }
  };
  return <div className="mx-auto max-w-4xl space-y-6 p-4 sm:p-8"><Link href="/admin/contact-requests" className="text-sm text-primary hover:underline">← Demandes de contact</Link>
    {query.isPending ? <p role="status">Ouverture du dossier…</p> : query.isError || !query.data ? <section role="alert" className="space-y-4 rounded-2xl border bg-card p-6"><h1 className="text-xl font-semibold">Dossier indisponible</h1><p className="text-sm">{clientError(query.error)}</p><Button onClick={() => query.refetch()}>Réessayer</Button></section> : <><header className="flex flex-wrap items-start justify-between gap-4"><div><p className="radar-eyebrow">Demande reçue le {clientDate(query.data.created_at)}</p><h1 className="mt-2 break-words text-3xl font-semibold">{query.data.name}</h1><p className="mt-3 text-sm text-muted-foreground">{inquiryStatus[query.data.status]}</p></div><Button variant="outline" disabled={busy} onClick={() => update(false)}>{query.data.status === 'closed' ? 'Rouvrir le dossier' : 'Clôturer le dossier'}</Button></header>
      <section className="rounded-2xl border bg-card p-6"><h2 className="text-lg font-semibold">Coordonnées et demande</h2><dl className="mt-5 grid gap-5 sm:grid-cols-2">{[['E-mail', query.data.email], ['Entreprise', query.data.company], ['Téléphone', query.data.phone], ['Offre souhaitée', ({ core: 'Radar Core', premium: 'Radar Premium', business: 'Radar Business', custom: 'Besoin sur mesure' } as Record<string, string>)[query.data.plan]]].map(([label, value]) => <div key={label}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-2 break-words text-sm">{value || 'Non renseigné'}</dd></div>)}</dl><h3 className="mt-7 text-sm font-semibold">Message</h3><p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7">{query.data.message}</p></section>
      <section className="space-y-4 rounded-2xl border bg-card p-6"><h2 className="text-lg font-semibold">Accusé d’ouverture</h2><p role="status" className="text-sm">{ackStatus[query.data.acknowledgement_status]}</p><p className="text-xs leading-6 text-muted-foreground">L’accusé indique que la demande a été ouverte et que l’équipe contactera prochainement le demandeur. Il ne confirme ni commande, ni devis, ni paiement. Une nouvelle consultation du dossier n’envoie pas d’autre e-mail.</p>{query.data.acknowledgement_sent_at && <p className="text-xs text-muted-foreground">Transmission au service d’envoi : {clientDate(query.data.acknowledgement_sent_at)}. La livraison dans la boîte de réception dépend du prestataire.</p>}{query.data.acknowledgement_status === 'failed' && <Button disabled={busy} onClick={() => update(true)}>Relancer l’accusé d’ouverture</Button>}<Button variant="ghost" disabled={busy} onClick={() => query.refetch()}>Actualiser l’état</Button></section>
      {error && <p role="alert" className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
    </>}
  </div>;
}
export default function ContactDossierPage() { return <ProtectedRoute><AdminLayout><Dossier /></AdminLayout></ProtectedRoute>; }
