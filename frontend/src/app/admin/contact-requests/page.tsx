'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { AdminLayout, ProtectedRoute } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { inquiryRequest, inquiryStatus, type ContactInquiry } from '@/lib/contact-inquiries';
import { clientDate, clientError } from '@/lib/platform-clients';

function Inbox() {
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);
  const query = useQuery<{ items: ContactInquiry[]; total: number; new_count: number; limit: number }>({
    queryKey: ['admin-contact', 'list', q, status, page],
    queryFn: () => inquiryRequest(`?${new URLSearchParams({ q, status, page: String(page) })}`), retry: false,
  });
  return <div className="mx-auto max-w-[1440px] space-y-7 p-4 sm:p-8"><header><p className="radar-eyebrow">Administration Radar</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Demandes de contact</h1><p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">Les demandes envoyées depuis le site arrivent ici. La première ouverture du dossier déclenche un accusé d’ouverture par e-mail au demandeur.</p></header>
    <form className="flex flex-col gap-4 rounded-2xl border bg-card p-4 sm:flex-row sm:items-end" onSubmit={event => { event.preventDefault(); setQ(search.trim()); setPage(1); }}><div className="w-full space-y-2"><Label htmlFor="inquiry-search">Nom, entreprise ou e-mail</Label><Input id="inquiry-search" value={search} maxLength={100} onChange={event => setSearch(event.target.value)} placeholder="Rechercher une demande…" /></div><div className="w-full space-y-2 sm:max-w-[200px]"><Label htmlFor="inquiry-status">État</Label><select id="inquiry-status" value={status} onChange={event => { setStatus(event.target.value); setPage(1); }} className="h-10 w-full rounded-xl border bg-background px-3 text-sm"><option value="all">Toutes les demandes</option>{Object.entries(inquiryStatus).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div><Button>Rechercher</Button></form>
    {query.isPending ? <p role="status">Chargement des demandes…</p> : query.isError ? <section role="alert" className="space-y-4 rounded-2xl border bg-card p-6"><p>{clientError(query.error)}</p><Button onClick={() => query.refetch()}>Réessayer</Button></section> : query.data && <><p role="status" className="text-sm text-muted-foreground">{query.data.total} demande(s) · {query.data.new_count} à ouvrir</p>{query.data.items.length ? <ul className="space-y-4">{query.data.items.map(row => <li key={row.id} className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border bg-card p-5"><div className="min-w-0 space-y-2"><div className="flex flex-wrap items-center gap-3"><h2 className="break-words font-semibold">{row.name}</h2><span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs text-primary">{inquiryStatus[row.status]}</span></div><p className="break-all text-sm text-muted-foreground">{row.email}</p><p className="text-xs text-muted-foreground">{row.company || 'Entreprise non renseignée'} · reçue le {clientDate(row.created_at)}</p></div><Button asChild variant="outline"><Link href={'/admin/contact-requests/' + row.id}>Ouvrir le dossier</Link></Button></li>)}</ul> : <section className="rounded-2xl border bg-card p-8 text-center"><h2 className="font-semibold">Aucune demande trouvée</h2><p className="mt-2 text-sm text-muted-foreground">Les nouveaux messages du formulaire apparaîtront ici.</p></section>}<div className="flex flex-wrap items-center justify-between gap-3"><Button variant="outline" disabled={page === 1} onClick={() => setPage(value => value - 1)}>Précédent</Button><span className="text-xs text-muted-foreground">Page {page} sur {Math.max(1, Math.ceil(query.data.total / query.data.limit))}</span><Button variant="outline" disabled={page * query.data.limit >= query.data.total} onClick={() => setPage(value => value + 1)}>Suivant</Button></div></>}
  </div>;
}
export default function ContactRequestsPage() { return <ProtectedRoute><AdminLayout><Inbox /></AdminLayout></ProtectedRoute>; }
