'use client';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authApi } from '@/lib/api';
import { Loader2, Send } from 'lucide-react';

export const mfaLabels: Record<string, string> = {
  passkey: 'Clé d’accès', totp: 'Application d’authentification', email: 'Code par e-mail', sms: 'Code par SMS', recovery: 'Code de secours',
};
export function mfaError(error: unknown) {
  const message = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof message === 'string' ? message : 'La vérification a échoué. Réessayez ou recommencez la connexion.';
}

export function MfaChallenge({ token, methods, destinations = {}, onVerify, onBack, enrollment = false, alreadySent = false, allowTrust = false }: {
  token: string; methods: string[]; destinations?: Record<string, string>;
  onVerify: (method: string, code: string, trustDevice?: boolean) => Promise<void>; onBack: () => void;
  enrollment?: boolean; alreadySent?: boolean; allowTrust?: boolean;
}) {
  const [trustDevice, setTrustDevice] = useState(false);
  const [method, setMethod] = useState(methods[0] || 'totp');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(alreadySent ? 'Code envoyé. Consultez le destinataire indiqué.' : '');
  const [cooldown, setCooldown] = useState(alreadySent ? 60 : 0);
  useEffect(() => {
    if (!cooldown) return;
    const timer = setTimeout(() => setCooldown(value => Math.max(0, value - 1)), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);
  const delivered = method === 'email' || method === 'sms';
  const send = async () => {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await authApi.mfaSend(token, method);
      setCooldown(result.retry_after_seconds || 60);
      setNotice(`Code envoyé${result.destination ? ` à ${result.destination}` : ''}. Le dernier code remplace le précédent.`);
    } catch (error) { setError(mfaError(error)); } finally { setBusy(false); }
  };
  return <form className="space-y-5" onSubmit={async event => {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError('');
    try { await onVerify(method, code, allowTrust && trustDevice); } catch (error) { setError(mfaError(error)); setCode(''); } finally { setBusy(false); }
  }}>
    {methods.length > 1 && <div className="space-y-2"><Label htmlFor="mfa-method">Méthode de vérification</Label><select id="mfa-method" className="h-11 w-full rounded-xl border bg-background px-3 text-sm" value={method} disabled={busy} onChange={event => { setMethod(event.target.value); setCode(''); setError(''); setNotice(''); }}>{methods.map(value => <option key={value} value={value}>{mfaLabels[value] || value}</option>)}</select></div>}
    <p className="text-sm leading-relaxed text-muted-foreground">{method === 'passkey' ? 'Utilisez votre clé d’accès enregistrée et confirmez avec votre appareil.' : method === 'totp' ? 'Saisissez le code actuel de votre application. Un code déjà utilisé doit être remplacé par le suivant.' : method === 'recovery' ? 'Saisissez un de vos codes de secours. Il ne peut être utilisé qu’une fois.' : `Recevez un code ${method === 'sms' ? 'par SMS' : 'par e-mail'}${destinations[method] ? ` à ${destinations[method]}` : ''}.`}</p>
    {delivered && <Button type="button" variant="outline" className="w-full gap-2" disabled={busy || cooldown > 0} onClick={send}><Send size={15} />{cooldown ? `Nouvel envoi dans ${cooldown} s` : 'Envoyer un code'}</Button>}
    {notice && <p role="status" className="rounded-xl bg-primary/5 p-3 text-sm">{notice}</p>}
    {error && <p role="alert" className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
    {method !== 'passkey' && <div className="space-y-2"><Label htmlFor="mfa-code">{method === 'recovery' ? 'Code de secours' : 'Code à 6 chiffres'}</Label><Input id="mfa-code" type="text" inputMode={method === 'recovery' ? 'text' : 'numeric'} autoComplete="one-time-code" autoFocus maxLength={method === 'recovery' ? 40 : 6} value={code} disabled={busy} className="h-12 text-center font-mono text-lg tracking-widest" onChange={event => setCode(method === 'recovery' ? event.target.value.toUpperCase().replace(/[^A-Z0-9 -]/g, '') : event.target.value.replace(/[^0-9]/g, ''))} /></div>}
    {allowTrust && <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={trustDevice} disabled={busy} onChange={event => setTrustDevice(event.target.checked)} className="mt-1 accent-violet-600" /><span>Faire confiance à cet appareil pendant 30 jours<span className="mt-1 block text-xs text-muted-foreground">Sur un appareil personnel uniquement. Autorisation révocable dans Paramètres → Sécurité.</span></span></label>}
    <div className="flex gap-3"><Button type="button" variant="outline" className="flex-1" disabled={busy} onClick={onBack}>Retour</Button><Button type="submit" className="flex-1 gap-2" disabled={busy || (method === 'passkey' ? false : method === 'recovery' ? code.replace(/[ -]/g, '').length < 8 : code.length !== 6)}>{busy && <Loader2 size={15} className="animate-spin" />}{enrollment ? 'Activer la méthode' : method === 'passkey' ? 'Utiliser ma clé d’accès' : 'Vérifier'}</Button></div>
    <p className="text-xs leading-relaxed text-muted-foreground">La vérification expire après cinq minutes. Les codes ne doivent être communiqués à personne.</p>
  </form>;
}
