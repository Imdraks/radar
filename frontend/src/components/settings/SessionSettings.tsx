'use client';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Monitor, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { mfaError } from '@/components/auth/MfaChallenge';

type Entry = { id: string; label: string; created_at: string; expires_at: string; is_current: boolean };
const date = (value: string) => new Date(value).toLocaleString('fr-FR');

function AccessList({ devices = false }: { devices?: boolean }) {
  const userId = useAuthStore(state => state.user?.id);
  const queryClient = useQueryClient();
  const path = devices ? '/auth/trusted-devices' : '/auth/sessions';
  const key = ['security-access', userId, path];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const query = useQuery<{ items: Entry[] }>({ queryKey: key, queryFn: async () => (await api.get(path)).data, enabled: !!userId, refetchOnWindowFocus: true });
  const revoke = async (id?: string) => {
    const message = id ? (devices ? 'Retirer l’autorisation de cet appareil ?' : 'Fermer cette session à distance ?') : (devices ? 'Demander à nouveau l’A2F sur tous les appareils aux prochaines connexions ?' : 'Fermer toutes les autres sessions ? Votre session actuelle sera conservée.');
    if (!window.confirm(message)) return;
    setBusy(true); setError(''); setNotice('');
    try {
      if (id) await api.delete(`${path}/${id}`);
      else await api.post(`${path}/${devices ? 'revoke-all' : 'revoke-others'}`);
      setNotice(devices ? 'Autorisation retirée. L’A2F sera demandée à la prochaine connexion.' : 'Session(s) fermée(s). Votre session actuelle est conservée.');
      await queryClient.invalidateQueries({ queryKey: key });
    } catch (error) { setError(mfaError(error)); } finally { setBusy(false); }
  };
  return <Card><CardHeader><CardTitle className="flex items-center gap-2">{devices ? <ShieldCheck size={20} /> : <Monitor size={20} />}{devices ? 'Appareils autorisés pendant 30 jours' : 'Sessions actives'}</CardTitle><CardDescription>{devices ? 'Ces navigateurs peuvent éviter l’A2F après authentification. Leur autorisation expire sans renouvellement automatique. Retirer cette autorisation ne ferme pas une session déjà ouverte.' : 'Connexions encore valides, sans indication de présence en temps réel. La révocation bloque aussi leur renouvellement et ne concerne que votre compte.'}</CardDescription></CardHeader><CardContent className="space-y-4">
    {(error || query.isError) && <p role="alert" className="text-sm text-destructive">{error || 'Impossible de charger cette liste.'}</p>}
    {notice && <p role="status" className="text-sm text-primary">{notice}</p>}
    {query.isPending ? <p className="text-sm text-muted-foreground">Chargement…</p> : query.isError ? <Button variant="outline" onClick={() => void query.refetch()}>Réessayer</Button> : <>
      {!query.data?.items.length && <p className="text-sm text-muted-foreground">{devices ? 'Aucun appareil autorisé.' : 'Aucune session disponible.'}</p>}
      {query.data?.items.map(row => <div key={row.id} className="flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="text-sm font-medium">{row.label}{row.is_current && <span className="ml-2 text-xs text-primary">{devices ? 'Cet appareil' : 'Session actuelle'}</span>}</p><p className="mt-1 text-xs text-muted-foreground">{devices ? 'Autorisé' : 'Connecté'} le {date(row.created_at)} · Expire le {date(row.expires_at)}</p></div>{(devices || !row.is_current) && <Button variant="outline" size="sm" disabled={busy} onClick={() => void revoke(row.id)}>{devices ? 'Retirer' : 'Fermer la session'}</Button>}</div>)}
      <Button variant="outline" disabled={busy || !query.data?.items.some(row => devices || !row.is_current)} onClick={() => void revoke()}>{devices ? 'Retirer toutes les autorisations' : 'Fermer toutes les autres sessions'}</Button>
    </>}
  </CardContent></Card>;
}
export function SessionSettings() { return <><AccessList /><AccessList devices /></>; }
