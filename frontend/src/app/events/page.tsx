'use client';
import { EventExpenses } from '@/components/EventExpenses';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AppLayout, ProtectedRoute } from '@/components/layout';
import { useSubscriptionStore } from '@/store/subscriptionStore';
interface Event { id: number; name: string; venue?: string; starts_at: string; ends_at: string; project_id: number; forecast_budget?: string; }
function Events() {
  const client = useQueryClient();
  const workspace = useSubscriptionStore(s => s.subscription?.workspace_id);
  const { data: events, isLoading, isError } = useQuery<Event[]>({ queryKey: ['production-events', workspace], queryFn: async () => (await api.get('/events')).data });
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const { data: detail, isError: detailError } = useQuery<{ artists: { id: string; name: string }[] }>({ queryKey: ['event', workspace, selected], queryFn: async () => (await api.get(`/events/${selected}`)).data, enabled: selected !== null });
  const artist = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('artist') : null;
  return <div className="space-y-6">
    <h1 className="text-3xl font-semibold">Événements</h1>
    <p>Chaque événement est relié à un projet de production pour ses tâches, fichiers, contrats et livrables.</p>
    <Link href="/map" className="underline">Consulter les événements artistiques sur la carte</Link>
    {message && <p role="status">{message}</p>}
    <form className="border rounded-xl p-4 space-y-3" onSubmit={async e => {
      e.preventDefault(); const form = e.currentTarget; const values = new FormData(form); setPending(true);
      try {
        const event = (await api.post('/events', { name: values.get('name'), venue: values.get('venue'), starts_at: values.get('start'), ends_at: values.get('end'), forecast_budget: values.get('budget') || null })).data;
        if (artist) {
          try { await api.post(`/events/${event.id}/artists/${encodeURIComponent(artist)}`); setMessage('Événement créé et artiste ajouté.'); }
          catch { setMessage('Événement créé. L’artiste n’a pas pu être ajouté ; vous pouvez réessayer dans la liste.'); }
        } else setMessage('Événement et projet de production créés.');
        form.reset(); await client.invalidateQueries({ queryKey: ['production-events', workspace] });
      } catch { setMessage('Création impossible. Vérifiez les dates et vos droits.'); }
      finally { setPending(false); }
    }}>
      <h2 className="text-lg font-medium">Créer un événement{artist ? ' avec l’artiste sélectionné' : ''}</h2>
      <label className="block">Nom<input required name="name" maxLength={255} className="border rounded p-2 block w-full text-black" /></label>
      <label className="block">Lieu<input name="venue" maxLength={500} className="border rounded p-2 block w-full text-black" /></label>
      <div className="flex flex-wrap gap-4"><label>Début (UTC)<input required type="datetime-local" name="start" className="border rounded p-2 block text-black" /></label><label>Fin (UTC)<input required type="datetime-local" name="end" className="border rounded p-2 block text-black" /></label></div>
      <label className="block">Budget prévisionnel (€)<input type="number" min="0" step="0.01" name="budget" className="border rounded p-2 block text-black" /></label>
      <button disabled={pending} className="bg-purple-700 text-white px-4 py-2 rounded disabled:opacity-50">{pending ? 'Création…' : 'Créer l’événement'}</button>
    </form>
    {isLoading ? <p role="status">Chargement…</p> : isError ? <p role="alert">Impossible de charger les événements.</p> : !events?.length ? <p>Aucun événement enregistré.</p> : <div className="grid md:grid-cols-2 gap-4">{events.map(event => <article key={event.id} className="border rounded-xl p-4 space-y-2">
      <h2 className="font-semibold">{event.name}</h2><p>{event.venue || 'Lieu à définir'} · {new Date(event.starts_at + 'Z').toLocaleString('fr-FR')}</p>
      {event.forecast_budget != null && <p>Budget prévisionnel : {event.forecast_budget} €</p>}
      <Link className="block underline" href={`/projects/${event.project_id}`}>Production, documents et tâches</Link>
      <button className="underline" onClick={() => setSelected(event.id)}>Voir les artistes</button>
      {artist && <button disabled={pending} className="block underline" onClick={async () => { setPending(true); try { await api.post(`/events/${event.id}/artists/${encodeURIComponent(artist)}`); setMessage('Artiste ajouté à l’événement.'); await client.invalidateQueries({ queryKey: ['event', workspace, event.id] }); } catch { setMessage('Impossible d’ajouter cet artiste.'); } finally { setPending(false); } }}>Ajouter l’artiste sélectionné</button>}
      {selected === event.id && (detailError ? <p role="alert">Artistes indisponibles.</p> : detail?.artists.length ? detail.artists.map(a => <Link key={a.id} className="block underline" href={`/discovery/${a.id}`}>{a.name}</Link>) : <p>Aucun artiste enregistré.</p>)}
      {selected === event.id && <EventExpenses eventId={event.id} />}
    </article>)}</div>}
  </div>;
}
export default function EventsPage() { return <ProtectedRoute><AppLayout><Events /></AppLayout></ProtectedRoute>; }
