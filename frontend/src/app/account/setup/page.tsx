'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { PasswordSettings } from '@/components/settings/PasswordSettings';
import { TwoFactorSettings } from '@/components/settings/TwoFactorSettings';
import { PasskeySettings } from '@/components/settings/PasskeySettings';
import { Button } from '@/components/ui/button';
import { mfaError } from '@/components/auth/MfaChallenge';

function Setup() {
  const { user, fetchUser, logout } = useAuthStore();
  const router = useRouter();
  const [choice, setChoice] = useState<'mfa' | 'passkey'>('mfa');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { if (user && !user.must_change_password && !user.security_setup_pending) router.replace('/account/entry'); }, [user, router]);
  const finish = async (security: 'later' | 'configured') => {
    setBusy(true); setError('');
    try { await api.post('/auth/account/setup/complete', { security }); await fetchUser(); router.replace('/account/entry'); }
    catch (failure) { setError(mfaError(failure)); } finally { setBusy(false); }
  };
  return <main className="radar-app min-h-screen bg-background px-5 py-8 text-foreground"><div className="mx-auto max-w-2xl space-y-7">
    <header className="flex items-center justify-between gap-4"><RadarLogo /><Button variant="ghost" onClick={logout}>Déconnexion</Button></header>
    <div><p className="radar-eyebrow">Bienvenue sur Radar · {user?.must_change_password ? 'Étape 1 sur 2' : 'Étape 2 sur 2'}</p><h1 className="mt-3 text-3xl font-semibold tracking-tight">{user?.must_change_password ? 'Choisissez votre mot de passe.' : 'Un accès qui vous ressemble.'}</h1><p className="mt-4 text-sm leading-7 text-muted-foreground">{user?.must_change_password ? 'Remplacez le mot de passe temporaire reçu par e-mail pour accéder à votre espace. Cette étape est obligatoire.' : 'Protégez vos connexions avec une application, un code par e-mail ou une clé d’accès. Vous pouvez aussi configurer cette protection plus tard dans les paramètres.'}</p></div>
    {user?.must_change_password ? <PasswordSettings /> : <>
      <div className="flex flex-wrap gap-3"><Button variant={choice === 'mfa' ? 'default' : 'outline'} onClick={() => setChoice('mfa')}>Configurer l’A2F</Button><Button variant={choice === 'passkey' ? 'default' : 'outline'} onClick={() => setChoice('passkey')}>Configurer une clé d’accès</Button></div>
      {choice === 'mfa' ? <TwoFactorSettings /> : <PasskeySettings />}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <footer className="flex flex-wrap justify-between gap-3 border-t pt-5"><Button variant="ghost" disabled={busy} onClick={() => finish('later')}>Plus tard</Button><Button disabled={busy} onClick={() => finish('configured')}>Terminer la configuration</Button></footer>
    </>}
  </div></main>;
}
export default function AccountSetupPage() { return <ProtectedRoute><Setup /></ProtectedRoute>; }
