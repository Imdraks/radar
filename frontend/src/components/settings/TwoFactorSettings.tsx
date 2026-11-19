'use client';
import { useState } from 'react';
import Image from 'next/image';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Shield, Smartphone, Mail, MessageSquare, Key, Loader2, Copy } from 'lucide-react';
import { verifyReauthentication } from '@/lib/passkeys';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { MfaChallenge, mfaLabels, mfaError } from '@/components/auth/MfaChallenge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

type Method = 'totp' | 'email' | 'sms';
type Status = { enabled: boolean; methods: string[]; destinations: Record<string, string>; available: Record<string, boolean>; has_backup_codes: boolean };
type Challenge = { challenge_token: string; methods: string[]; destinations: Record<string, string> };
type Enrollment = { challenge_token: string; method: Method; secret?: string; qr_code?: string; sent?: boolean; destination?: string };
type Action = { kind: 'add' | 'disable'; method: Method } | { kind: 'recovery' };

export function TwoFactorSettings() {
  const cache = useQueryClient();
  const { setTokens } = useAuthStore();
  const userId = useAuthStore(state => state.user?.id);
  const userEmail = useAuthStore(state => state.user?.email);
  const { data: status, isLoading, isError } = useQuery({ queryKey: ['mfa-status', userId], enabled: Boolean(userId), queryFn: async () => (await api.get('/auth/mfa/status')).data as Status });
  const [action, setAction] = useState<Action | null>(null);
  const [phase, setPhase] = useState<'password' | 'verify' | 'enroll'>('password');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [codes, setCodes] = useState<string[]>([]);
  const close = () => { setAction(null); setPassword(''); setPhone(''); setChallenge(null); setEnrollment(null); setError(''); setPhase('password'); };
  const start = (value: Action) => { close(); setNotice(''); setAction(value); };
  const changed = async (result: { access_token: string; refresh_token: string; backup_codes?: string[] }, message: string) => {
    if (result.backup_codes) setCodes(result.backup_codes);
    await setTokens(result.access_token, result.refresh_token);
    await cache.invalidateQueries({ queryKey: ['mfa-status'] });
    close(); setNotice(message);
  };
  const execute = async (managementToken: string) => {
    if (!action) return;
    if (action.kind === 'add') {
      const result = await api.post('/auth/mfa/enroll/start', { management_token: managementToken, method: action.method, ...(action.method === 'sms' ? { phone } : {}) });
      setEnrollment(result.data); setPhase('enroll');
    } else {
      const result = await api.post(action.kind === 'recovery' ? '/auth/mfa/recovery/regenerate' : '/auth/mfa/disable', { management_token: managementToken, ...(action.kind === 'disable' ? { method: action.method } : {}) });
      await changed(result.data, action.kind === 'recovery' ? 'Nouveaux codes de secours générés. Les précédents sont invalidés.' : 'Méthode désactivée. Les autres méthodes restent actives.');
    }
  };
  return <Card><CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Shield size={20} />Authentification à deux facteurs</CardTitle><CardDescription>Confirmez votre identité avec une application, un e-mail ou un SMS. Choisissez les méthodes qui vous conviennent.</CardDescription></CardHeader><CardContent className="space-y-6">
    {isLoading ? <p role="status" className="flex items-center gap-2 text-sm"><Loader2 className="animate-spin" size={16} />Chargement de la sécurité…</p> : isError || !status ? <p role="alert" className="text-sm text-destructive">Impossible de lire les méthodes. Réessayez avant de modifier la sécurité.</p> : <>
      <p className={`rounded-xl p-4 text-sm ${status.enabled ? 'bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-200' : 'bg-primary/5'}`}>{status.enabled ? 'La double authentification est activée sur votre compte.' : 'Votre compte utilise actuellement une seule étape de connexion. Ajoutez une méthode pour activer la double authentification.'}</p>
      <div className="space-y-3">{[
        { method: 'totp' as Method, icon: Smartphone, text: 'Google Authenticator, Microsoft Authenticator, 1Password ou toute application TOTP compatible.' },
        { method: 'email' as Method, icon: Mail, text: 'Un code temporaire envoyé à l’adresse vérifiée de votre compte.' },
        { method: 'sms' as Method, icon: MessageSquare, text: 'Un code temporaire envoyé au numéro que vous confirmez. Les envois dépendent d’un prestataire SMS.' },
      ].map(({ method, icon: Icon, text }) => {
        const enabled = status.methods.includes(method);
        return <article key={method} className="flex flex-col justify-between gap-4 rounded-2xl border p-5 sm:flex-row sm:items-center"><div className="flex min-w-0 gap-3"><Icon size={21} className="mt-0.5 shrink-0 text-primary" /><div><h3 className="text-sm font-semibold">{mfaLabels[method]}{enabled && <span className="ml-2 text-xs font-normal text-green-700 dark:text-green-300">Activée</span>}</h3><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{text}</p>{enabled && status.destinations[method] && <p className="mt-2 text-xs">{status.destinations[method]}</p>}{!status.available[method] && <p className="mt-2 text-xs text-muted-foreground">Envoi non configuré. Contactez l’administrateur pour activer cette méthode.</p>}</div></div><Button variant="outline" className="shrink-0" disabled={!enabled && !status.available[method]} onClick={() => start({ kind: enabled ? 'disable' : 'add', method })}>{enabled ? 'Désactiver' : 'Configurer'}</Button></article>;
      })}</div>
      {status.enabled && <div className="flex flex-col justify-between gap-4 rounded-2xl border p-5 sm:flex-row sm:items-center"><div><h3 className="flex items-center gap-2 text-sm font-semibold"><Key size={17} />Codes de secours</h3><p className="mt-2 text-xs leading-relaxed text-muted-foreground">À conserver hors de Radar. Chaque code est utilisable une seule fois.</p></div><Button variant="outline" onClick={() => start({ kind: 'recovery' })}>Générer de nouveaux codes</Button></div>}
      <p className="text-xs leading-relaxed text-muted-foreground">Une modification exige une nouvelle vérification de votre identité et déconnecte les autres sessions et autorisations Radar utilisant leurs anciens jetons. Conservez au moins une méthode accessible et vos codes de secours.</p>
    </>}
    {notice && <p role="status" className="rounded-xl bg-primary/5 p-4 text-sm">{notice}</p>}
    {codes.length > 0 && <section className="space-y-4 rounded-2xl border border-primary/20 p-5" aria-label="Nouveaux codes de secours"><h3 className="font-semibold">Enregistrez ces codes maintenant</h3><p className="text-sm text-muted-foreground">Ils ne seront plus affichés après fermeture ou rechargement. Ces codes remplacent les précédents.</p><ul className="grid gap-2 sm:grid-cols-2">{codes.map(code => <li key={code} className="rounded-lg bg-secondary px-3 py-2 font-mono text-xs">{code}</li>)}</ul><div className="flex flex-wrap gap-3"><Button variant="outline" className="gap-2" onClick={async () => { try { await navigator.clipboard.writeText(codes.join('\n')); setNotice('Codes copiés. Conservez-les dans un emplacement sécurisé.'); } catch { setNotice('Copie indisponible. Enregistrez les codes manuellement.'); } }}><Copy size={15} />Copier les codes</Button><Button variant="outline" onClick={() => setCodes([])}>J’ai enregistré mes codes</Button></div></section>}
    <Dialog open={Boolean(action)} onOpenChange={open => { if (!open && !busy) close(); }}><DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg"><DialogHeader><DialogTitle>{phase === 'enroll' ? 'Confirmer la nouvelle méthode' : 'Vérifier votre identité'}</DialogTitle><DialogDescription>{phase === 'password' ? 'Une modification de sécurité nécessite une vérification récente. Votre méthode actuelle reste active pendant la configuration.' : phase === 'verify' ? 'Confirmez avec une méthode déjà activée ou un code de secours.' : 'La méthode sera activée seulement après validation du code reçu.'}</DialogDescription></DialogHeader>
      {phase === 'password' && <form className="space-y-4" onSubmit={async event => {
        event.preventDefault(); setBusy(true); setError('');
        try {
          const response = await api.post('/auth/mfa/reauth/start', { password: password || null });
          setPassword('');
          if (response.data.requires_2fa) { setChallenge(response.data); setPhase('verify'); }
          else await execute(response.data.management_token);
        } catch (error) { setError(mfaError(error)); } finally { setBusy(false); }
      }}><p className="break-all rounded-xl bg-secondary p-3 text-sm">Compte vérifié : <span className="font-medium">{userEmail || "Compte connecté"}</span></p><div className="space-y-2"><Label htmlFor="mfa-password">Mot de passe Radar</Label><Input id="mfa-password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} /><p className="text-xs text-muted-foreground">Saisissez le mot de passe Radar du compte indiqué, différent de votre mot de passe Google ou Apple. Si aucun mot de passe Radar n’est défini, laissez vide après une connexion récente avec votre fournisseur.</p></div>{action?.kind === 'add' && action.method === 'sms' && <div className="space-y-2"><Label htmlFor="mfa-phone">Numéro de téléphone international</Label><Input id="mfa-phone" type="tel" autoComplete="tel" placeholder="+33612345678" value={phone} onChange={event => setPhone(event.target.value)} required /><p className="text-xs text-muted-foreground">Le numéro n’est enregistré comme méthode qu’après confirmation du SMS.</p></div>}{error && <p role="alert" className="text-sm text-destructive">{error}</p>}<Button type="submit" className="w-full gap-2" disabled={busy}>{busy && <Loader2 size={15} className="animate-spin" />}Continuer</Button></form>}
      {phase === 'verify' && challenge && <MfaChallenge key={challenge.challenge_token} token={challenge.challenge_token} methods={challenge.methods} destinations={challenge.destinations} onBack={close} onVerify={async (method, code) => {
        setBusy(true);
        try { const response = await verifyReauthentication(challenge.challenge_token, method, code); await execute(response.management_token); } finally { setBusy(false); }
      }} />}
      {phase === 'enroll' && enrollment && <div className="space-y-5">{enrollment.qr_code && <div className="space-y-3"><Image unoptimized src={`data:image/png;base64,${enrollment.qr_code}`} width={200} height={200} alt="QR code de configuration de votre application d’authentification" className="mx-auto rounded-xl bg-white" /><p className="text-xs leading-relaxed text-muted-foreground">Scannez ce QR code dans votre application. Si nécessaire, saisissez cette clé manuellement :</p><code className="block break-all rounded-xl bg-secondary p-3 text-sm">{enrollment.secret}</code></div>}<MfaChallenge key={enrollment.challenge_token} token={enrollment.challenge_token} methods={[enrollment.method]} destinations={enrollment.destination ? { [enrollment.method]: enrollment.destination } : {}} alreadySent={enrollment.sent} enrollment onBack={close} onVerify={async (method, code) => {
        setBusy(true);
        try { const response = await api.post('/auth/mfa/enroll/complete', { challenge_token: enrollment.challenge_token, method, code }); await changed(response.data, 'Méthode confirmée et activée. Enregistrez vos nouveaux codes de secours.'); } finally { setBusy(false); }
      }} /></div>}
    </DialogContent></Dialog>
  </CardContent></Card>;
}
