'use client';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Plus, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { registerPasskey, verifyReauthentication } from '@/lib/passkeys';
import { useAuthStore } from '@/store/auth';
import { MfaChallenge, mfaError } from '@/components/auth/MfaChallenge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';

type Key = { id: string; name: string; created_at: string; last_used_at: string | null };
type Challenge = { challenge_token: string; methods: string[]; destinations: Record<string, string> };

export function PasskeySettings() {
  const cache = useQueryClient();
  const { user, setTokens } = useAuthStore();
  const keys = useQuery<Key[]>({ queryKey: ['passkeys', user?.id], queryFn: async () => (await api.get('/auth/passkeys')).data });
  const [action, setAction] = useState<'add' | Key | null>(null);
  const [password, setPassword] = useState('');
  const [name, setName] = useState('Mon appareil');
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [codes, setCodes] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const close = () => { setAction(null); setPassword(''); setChallenge(null); setError(''); };
  const execute = async (token: string) => {
    const result = action === 'add' ? await registerPasskey(token, name) : (await api.post(`/auth/passkeys/${(action as Key).id}/revoke`, { management_token: token })).data;
    await setTokens(result.access_token, result.refresh_token);
    setCodes(result.backup_codes || []);
    setNotice(action === 'add' ? 'Clé d’accès ajoutée. Elle sera proposée pour confirmer vos prochaines connexions.' : 'Clé d’accès retirée.');
    close();
    await cache.invalidateQueries({ queryKey: ['passkeys'] });
    await cache.invalidateQueries({ queryKey: ['mfa-status'] });
  };
  const describe = (failure: unknown) => failure instanceof DOMException && failure.name === 'NotAllowedError' ? 'Opération annulée ou délai dépassé. Votre configuration existante est conservée.' : failure instanceof Error && !('response' in failure) ? failure.message : mfaError(failure);
  return <Card><CardHeader><CardTitle className="flex items-center gap-2"><KeyRound size={19} />Clés d’accès</CardTitle><CardDescription>Confirmez votre identité avec votre appareil, sa biométrie ou une clé de sécurité. La vérification reste liée au domaine Radar.</CardDescription></CardHeader><CardContent className="space-y-5">
    {keys.isPending ? <p>Chargement…</p> : keys.isError ? <p role="alert">Les clés n’ont pas pu être chargées. <button className="underline" onClick={() => keys.refetch()}>Réessayer</button></p> : keys.data?.length ? <ul className="space-y-3">{keys.data.map(key => <li key={key.id} className="flex items-center justify-between gap-3 rounded-xl border p-3"><div className="min-w-0"><p className="break-words text-sm font-medium">{key.name}</p><p className="mt-1 text-xs text-muted-foreground">Ajoutée le {new Date(key.created_at).toLocaleDateString('fr-FR')}{key.last_used_at ? ` · utilisée le ${new Date(key.last_used_at).toLocaleDateString('fr-FR')}` : ''}</p></div><Button variant="ghost" size="icon" aria-label={`Retirer ${key.name}`} onClick={() => { setAction(key); setError(''); }}><Trash2 size={16} /></Button></li>)}</ul> : <p className="text-sm text-muted-foreground">Aucune clé enregistrée.</p>}
    <Button variant="outline" className="gap-2" disabled={keys.isPending || keys.isError} onClick={() => { setAction('add'); setError(''); }}><Plus size={16} />Ajouter une clé d’accès</Button>
    {notice && <p role="status" className="rounded-xl bg-primary/5 p-3 text-sm">{notice}</p>}
    {codes.length > 0 && <section aria-label="Codes de secours de la clé d’accès" className="rounded-xl border p-4"><h3 className="font-semibold">Conservez ces nouveaux codes de secours</h3><p className="my-3 text-sm text-muted-foreground">Ils remplacent les précédents et ne seront plus affichés après fermeture.</p><ul className="grid grid-cols-1 gap-2 font-mono text-sm sm:grid-cols-2">{codes.map(code => <li key={code}>{code}</li>)}</ul><Button variant="outline" className="mt-4" onClick={() => setCodes([])}>J’ai enregistré mes codes</Button></section>}
    <Dialog open={Boolean(action)} onOpenChange={open => { if (!open && !busy) close(); }}><DialogContent className="max-h-[90dvh] overflow-y-auto"><DialogTitle>{action === 'add' ? 'Ajouter une clé d’accès' : 'Retirer la clé d’accès'}</DialogTitle><DialogDescription>Confirmez votre identité avant cette modification de sécurité.</DialogDescription>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {challenge ? <MfaChallenge token={challenge.challenge_token} methods={challenge.methods} destinations={challenge.destinations} onBack={close} onVerify={async (method, code) => {
        setBusy(true);
        try { const proof = await verifyReauthentication(challenge.challenge_token, method, code); await execute(proof.management_token); }
        catch (failure) { setError(describe(failure)); throw failure; } finally { setBusy(false); }
      }} /> : <form className="space-y-4" onSubmit={async event => {
        event.preventDefault(); setBusy(true); setError('');
        try {
          const { data } = await api.post('/auth/mfa/reauth/start', { password: password || null });
          setPassword('');
          if (data.requires_2fa) setChallenge(data); else await execute(data.management_token);
        } catch (failure) { setError(describe(failure)); } finally { setBusy(false); }
      }}>
        {action === 'add' && <div className="space-y-2"><Label htmlFor="passkey-name">Nom de la clé</Label><Input id="passkey-name" value={name} onChange={event => setName(event.target.value)} required minLength={2} maxLength={80} disabled={busy} /></div>}
        <div className="space-y-2"><Label htmlFor="passkey-password">Mot de passe Radar</Label><Input id="passkey-password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} /><p className="text-xs leading-6 text-muted-foreground">Pour un compte uniquement Google ou Apple, laissez vide et reconnectez-vous avec votre fournisseur si demandé.</p></div>
        <Button className="w-full" disabled={busy}>{busy ? 'Vérification…' : 'Continuer'}</Button>
      </form>}
    </DialogContent></Dialog>
  </CardContent></Card>;
}
