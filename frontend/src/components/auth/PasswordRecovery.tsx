'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/auth';
import { authApi } from '@/lib/api';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PasswordFields, passwordChecks, passwordError, usePasswordPolicy } from './PasswordFields';

export function PasswordRecovery({ reset = false }: { reset?: boolean }) {
  const policy = usePasswordPolicy();
  const [token, setToken] = useState('');
  const [ready, setReady] = useState(!reset);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    if (!reset) return;
    const readLink = () => {
      const value = new URLSearchParams(window.location.hash.slice(1)).get('token') || '';
      window.history.replaceState(null, '', window.location.pathname);
      setToken(value); setReady(true); setPassword(''); setConfirm(''); setError(''); setNotice('');
    };
    readLink();
    window.addEventListener('hashchange', readLink);
    return () => window.removeEventListener('hashchange', readLink);
  }, [reset]);
  const canSubmit = !busy && !!policy.data && (!reset || (token.length >= 32 && token.length <= 128 && password === confirm && passwordChecks(policy.data, password).every(value => value.valid)));
  return <main className="min-h-screen bg-background px-4 py-14 sm:py-20"><div className="mx-auto max-w-lg"><Link href="/" aria-label="Radar — Accueil" className="mb-8 flex justify-center"><RadarLogo /></Link><Card><CardHeader><CardTitle>{reset ? 'Choisir un nouveau mot de passe' : 'Mot de passe oublié'}</CardTitle><CardDescription>{reset ? 'Le lien expire après 15 minutes et ne fonctionne qu’une fois. Votre A2F déjà configurée reste active.' : 'Recevez un lien pour choisir un nouveau mot de passe Radar. Il expirera après 15 minutes.'}</CardDescription></CardHeader><CardContent className="space-y-5">
    {notice ? <><p role="status" className="rounded-xl bg-primary/5 p-4 text-sm">{notice}</p><Button asChild className="w-full"><Link href="/login">Revenir à la connexion</Link></Button></> : <>
      {error && <p role="alert" className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      {policy.isError && <p role="alert" className="text-sm text-destructive">Impossible de charger les critères de sécurité. Réessayez plus tard.</p>}
      {!ready || policy.isPending ? <p role="status" className="text-sm text-muted-foreground">Chargement…</p> : reset && (token.length < 32 || token.length > 128) ? <p role="alert" className="text-sm">Le lien de réinitialisation est absent ou invalide. Demandez un nouveau lien.</p> : <form className="space-y-5" onSubmit={async event => {
        event.preventDefault(); if (!canSubmit) return;
        setBusy(true); setError('');
        try {
          if (reset) {
            const result = await authApi.resetPassword(token, password, confirm);
            setPassword(''); setConfirm(''); setToken('');
            useAuthStore.getState().logout();
            setNotice(result.message);
          } else {
            const result = await authApi.forgotPassword(email);
            setNotice(result.message);
          }
        } catch (error) { setError(passwordError(error)); } finally { setBusy(false); }
      }}>
        {reset && policy.data ? <PasswordFields password={password} confirm={confirm} onPassword={setPassword} onConfirm={setConfirm} disabled={busy} policy={policy.data} /> : <div className="space-y-2"><Label htmlFor="recovery-email">Adresse e-mail du compte Radar</Label><Input id="recovery-email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy} required maxLength={254} /></div>}
        <Button type="submit" className="w-full" disabled={!canSubmit}>{busy ? 'Traitement…' : reset ? 'Enregistrer le nouveau mot de passe' : 'Demander un lien par e-mail'}</Button>
      </form>}
      <div className="flex flex-wrap justify-between gap-3 text-sm"><Link href="/login" className="text-primary underline underline-offset-4">Retour à la connexion</Link>{reset && <Link href="/forgot-password" className="text-primary underline underline-offset-4">Demander un nouveau lien</Link>}</div>
    </>}
  </CardContent></Card></div></main>;
}
