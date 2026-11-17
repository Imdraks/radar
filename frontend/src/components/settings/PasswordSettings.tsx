'use client';
import Link from 'next/link';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PasswordFields, passwordChecks, passwordError, usePasswordPolicy } from '@/components/auth/PasswordFields';
import { MfaChallenge } from '@/components/auth/MfaChallenge';

type Challenge = { challenge_token: string; methods: string[]; destinations: Record<string, string> };
export function PasswordSettings() {
  const user = useAuthStore(state => state.user);
  const policy = usePasswordPolicy();
  const status = useQuery<{ has_password: boolean }>({ queryKey: ['password-status', user?.id], enabled: !!user?.id, queryFn: async () => (await api.get('/auth/password/status')).data });
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const clear = () => { setCurrent(''); setPassword(''); setConfirm(''); setChallenge(null); };
  const change = async (managementToken: string) => {
    const result = await api.post('/auth/password/change', { current_password: current, new_password: password, confirm_password: confirm, management_token: managementToken });
    clear();
    await useAuthStore.getState().setTokens(result.data.access_token, result.data.refresh_token);
    setNotice(result.data.message);
  };
  return <Card><CardHeader><CardTitle>Mot de passe Radar</CardTitle><CardDescription>Compte : {user?.email}. L’ancien mot de passe et, si elle est active, votre A2F sont nécessaires. Les autres sessions et les autorisations de 30 jours seront révoquées.</CardDescription></CardHeader><CardContent className="space-y-5">
    {(policy.isError || status.isError) && <p role="alert" className="text-sm text-destructive">Impossible de charger la sécurité du compte. Réessayez plus tard.</p>}
    {notice && <p role="status" className="rounded-xl bg-primary/5 p-3 text-sm">{notice}</p>}
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {status.isPending || policy.isPending ? <p className="text-sm text-muted-foreground">Chargement…</p> : !status.isError && status.data && !status.data.has_password ? <p className="text-sm">Votre compte ne possède pas encore de mot de passe Radar. <Link href="/forgot-password" className="text-primary underline">Recevoir un lien par e-mail pour en définir un</Link>. Votre connexion Google ou Apple reste disponible.</p> : policy.data && status.data?.has_password ? challenge ? <MfaChallenge key={challenge.challenge_token} token={challenge.challenge_token} methods={challenge.methods} destinations={challenge.destinations} onBack={clear} onVerify={async (method, code) => {
      setBusy(true);
      try {
        const proof = await api.post('/auth/mfa/reauth/complete', { challenge_token: challenge.challenge_token, method, code });
        await change(proof.data.management_token);
      } finally { setBusy(false); }
    }} /> : <form className="space-y-5" onSubmit={async event => {
      event.preventDefault(); if (busy) return;
      setBusy(true); setError(''); setNotice('');
      try {
        const proof = await api.post('/auth/mfa/reauth/start', { password: current });
        if (proof.data.requires_2fa) setChallenge(proof.data);
        else await change(proof.data.management_token);
      } catch (error) { setError(passwordError(error)); } finally { setBusy(false); }
    }}>
      <div className="space-y-2"><Label htmlFor="current-password">Ancien mot de passe Radar</Label><Input id="current-password" type="password" autoComplete="current-password" value={current} onChange={event => setCurrent(event.target.value)} disabled={busy} required maxLength={128} /></div>
      <PasswordFields password={password} confirm={confirm} onPassword={setPassword} onConfirm={setConfirm} disabled={busy} policy={policy.data} prefix="account" />
      <Button type="submit" disabled={busy || !current || password !== confirm || !passwordChecks(policy.data, password).every(value => value.valid)}>{busy ? 'Vérification…' : 'Continuer pour changer le mot de passe'}</Button>
      <p className="text-xs text-muted-foreground">Si l’A2F est active, un code sera demandé à l’étape suivante. Le changement ne sera effectué qu’après cette vérification.</p>
    </form> : null}
    <Link href="/forgot-password" className="inline-block text-sm text-primary underline underline-offset-4">Ancien mot de passe oublié ?</Link>
  </CardContent></Card>;
}
