'use client';
import { useState } from 'react';
import { CheckCircle2, Users, Sparkles, ArrowUpRight, Loader2, ShieldCheck } from 'lucide-react';
import { AppLayout, ProtectedRoute } from '@/components/layout';
import { PlanCatalog } from '@/components/subscription/PlanCatalog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useSubscriptionStore, subscriptionFetch } from '@/store/subscriptionStore';

export default function SubscriptionPage() {
  const { subscription, changePlan } = useSubscriptionStore();
  const [message, setMessage] = useState('');
  const [addon, setAddon] = useState('');
  const [sending, setSending] = useState(false);
  return <ProtectedRoute><AppLayout><div className="space-y-8">
    <div><p className="radar-eyebrow mb-2">Administration</p><h1 className="radar-page-title text-3xl font-semibold">Abonnement</h1><p className="mt-2 text-sm text-muted-foreground">Une offre adaptée à votre agence, des outils qui évoluent avec vous.</p></div>
    {message && <p role="status" className="rounded-xl border bg-card px-5 py-4 text-sm">{message}</p>}
    <section aria-label="Votre abonnement" className="flex flex-col gap-5 rounded-2xl border bg-card p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
      <div className="flex items-center gap-4"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><ShieldCheck size={24} strokeWidth={1.6} /></span><div><p className="text-xs text-muted-foreground">Votre offre actuelle</p><p className="mt-1 text-lg font-semibold text-foreground">{subscription?.plan_display_name || 'Chargement…'}</p></div></div>
      <div className="flex flex-wrap items-center gap-5 text-sm"><span className="flex items-center gap-2 text-muted-foreground"><Users size={16} />{subscription?.current_seats ?? '—'} membre(s)</span><span className="flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 dark:bg-green-950/40 dark:text-green-400"><CheckCircle2 size={14} />Offre actuelle</span></div>
    </section>
    <section aria-labelledby="plans-title" className="space-y-5">
      <div><h2 id="plans-title" className="text-lg font-semibold">Les offres Radar</h2><p className="mt-1 text-sm text-muted-foreground">Les fonctionnalités des offres inférieures sont déjà comprises dans votre abonnement.</p></div>
      <PlanCatalog currentPlan={subscription?.plan} onRequest={async plan => {
        const ok = await changePlan(plan);
        setMessage(ok ? 'Demande enregistrée. Votre abonnement actif reste inchangé en attendant sa validation.' : 'Demande refusée ou service indisponible. Vérifiez vos permissions.');
      }} />
      <p className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground"><ShieldCheck size={15} className="mt-0.5 shrink-0" />Les demandes sont examinées par notre équipe. Les droits changent uniquement après autorisation administrative.</p>
    </section>
    <section className="grid gap-6 rounded-2xl border bg-card p-6 lg:grid-cols-[1fr_1.2fr] lg:gap-12">
      <div><span className="mb-3 inline-flex items-center gap-2 text-xs font-semibold text-primary"><Sparkles size={15} />RADAR ADDONS</span><h2 className="text-lg font-semibold">Un besoin spécifique ?</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Décrivez l’extension ou l’outil sur mesure dont votre équipe a besoin.</p></div>
      <form className="flex flex-col justify-center gap-3" onSubmit={async e => {
        e.preventDefault(); setSending(true);
        try { await subscriptionFetch('addon-requests', subscription?.workspace_id, { method: 'POST', body: JSON.stringify({ description: addon }) }); setMessage('Demande Radar Addons enregistrée.'); setAddon(''); }
        catch { setMessage('Impossible d’enregistrer cette demande.'); }
        finally { setSending(false); }
      }}><label htmlFor="addon" className="text-sm font-medium">Besoin d’une extension spécifique ?</label><Input id="addon" required minLength={3} maxLength={100} value={addon} onChange={e => setAddon(e.target.value)} placeholder="Décrivez votre besoin en quelques mots…" /><Button disabled={sending} variant="outline" className="self-start gap-2" type="submit">{sending ? <Loader2 size={15} className="animate-spin" /> : <ArrowUpRight size={15} />}Envoyer une demande Radar Addons</Button></form>
    </section>
  </div></AppLayout></ProtectedRoute>;
}
