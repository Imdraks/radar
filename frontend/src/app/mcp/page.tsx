import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, ArrowUpRight, BookOpen, Check, Folder, Lock, MessageSquare, Search, Shield, Sparkles, Users } from 'lucide-react';
import { PublicPage } from '@/components/landing/PublicPage';
import { RadarField, RadarMark } from '@/components/brand/RadarBrand';
import { Button } from '@/components/ui/button';

// /mcp also serves the authenticated protocol at the edge; do not cache HTML
// under that shared URL in a way that could mix the two representations.
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Radar dans ChatGPT — Connecteur MCP',
  description: 'Retrouvez votre workspace Radar dans ChatGPT : projets, tâches, clients et recherche artistique. Extension payante Radar Addons, sur demande.',
  alternates: { canonical: '/mcp' },
};

const uses = [
  { icon: Folder, title: 'Faites avancer vos projets', text: 'Retrouvez une mission, consultez ses tâches ou demandez une mise à jour. Votre workspace reste le contexte de travail.', prompt: 'Quelles tâches restent à faire sur ce projet ?' },
  { icon: Search, title: 'Explorez les bons artistes', text: 'Recherchez, consultez une fiche, demandez un enrichissement et comparez les données disponibles, avec leurs sources et leurs limites.', prompt: 'Recherche cet artiste et indique les données manquantes.' },
  { icon: Users, title: 'Gardez le contexte client', text: 'Retrouvez les clients et leurs projets sans quitter votre échange. Les actions disponibles suivent votre rôle et votre offre Radar.', prompt: 'Retrouve ce client et présente ses projets.' },
];
const safeguards = [
  { icon: Lock, title: 'Un accès que vous autorisez', text: 'La connexion passe par l’autorisation Radar. Vos identifiants ne se saisissent pas dans la conversation.' },
  { icon: Shield, title: 'Le bon workspace, les bons droits', text: 'Le connecteur utilise l’espace autorisé. Les permissions et les fonctionnalités de votre offre restent contrôlées par Radar.' },
  { icon: Check, title: 'Les écritures sous contrôle', text: 'Créer ou modifier nécessite radar:write. Les envois, validations financières et suppressions doivent suivre une demande explicite.' },
];
const faqs = [
  ['Est-ce inclus dans mon abonnement ?', 'Le connecteur est proposé comme une extension payante Radar Addons, après accord commercial. Contactez l’équipe pour confirmer les conditions applicables à votre workspace. Aucun tarif public n’est défini ici.'],
  ['Faut-il une offre ChatGPT particulière ?', 'Votre compte et votre environnement ChatGPT doivent permettre l’ajout d’un connecteur MCP distant. La disponibilité varie selon le client et son offre. Les éventuels coûts du client d’IA restent distincts de Radar.'],
  ['Toutes les statistiques artistiques sont-elles disponibles ?', 'Non. Les données dépendent des sources, des accès et des quotas. Les fans Deezer ne sont pas des auditeurs mensuels Spotify. Les observations absentes restent signalées ; les cachets et projections sont indicatifs.'],
  ['L’assistant peut-il agir seul sur mes données ?', 'Les consultations suivent les droits de la connexion. Les écritures nécessitent un consentement radar:write et les permissions du compte. Donnez des demandes précises et vérifiez les actions engageantes avant de les autoriser.'],
];

export default function McpPage() {
  return <PublicPage><main id="main-content" className="pt-20">
    <section className="radar-hero overflow-hidden border-b">
      <div className="radar-site-container grid items-center gap-14 py-16 sm:py-24 lg:grid-cols-[1.05fr_1fr] lg:gap-20">
        <div>
          <p className="radar-kicker"><span className="radar-signal-dot" />Radar Connect · ChatGPT / MCP</p>
          <h1 className="mt-7 text-[clamp(2.7rem,5vw,4.8rem)] font-semibold leading-[1.06] tracking-[-0.055em]">Radar, dans<br /><span className="text-primary">votre conversation.</span></h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted-foreground">Vos projets, vos clients et vos recherches artistiques. Retrouvez le contexte de votre agence et demandez des actions depuis ChatGPT.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="gap-2"><Link href="/contact?offer=mcp">Demander l’extension<ArrowUpRight size={17} /></Link></Button>
            <Button asChild size="lg" variant="outline" className="gap-2"><Link href="/doc/mcp"><BookOpen size={17} />Lire le guide</Link></Button>
          </div>
          <p className="mt-5 text-sm text-muted-foreground">Extension payante Radar Addons · Conditions sur demande</p>
        </div>
        <div className="relative isolate min-w-0">
          <RadarField className="pointer-events-none absolute -right-20 -top-16 -z-10 w-[360px] max-w-full opacity-60" />
          <div className="radar-orbit-panel overflow-hidden rounded-3xl border border-primary/15 bg-white">
            <div className="flex items-center justify-between gap-3 border-b p-5"><div className="flex items-center gap-3"><RadarMark className="h-9 w-9 text-primary" /><div><p className="text-sm font-semibold">Votre contexte, relié.</p><p className="text-xs text-muted-foreground">Un exemple de parcours dans ChatGPT</p></div></div><MessageSquare className="shrink-0 text-primary" size={20} /></div>
            <div className="space-y-6 p-5 sm:p-7">
              <div className="ml-8 rounded-2xl rounded-tr-md bg-primary/[0.07] p-4 text-sm leading-relaxed">Recherche cet artiste, puis montre-moi les sources disponibles.</div>
              <div className="flex gap-3"><Sparkles className="mt-1 shrink-0 text-primary" size={18} /><div><p className="text-sm font-medium">Une recherche avec son contexte</p><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Les résultats distinguent les fiches de votre workspace et les candidats du catalogue public.</p></div></div>
              <div className="rounded-2xl border bg-background p-4"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Vous gardez la main</p><p className="mt-2 text-sm leading-relaxed">L’enregistrement est une action distincte. Son enrichissement se suit jusqu’au résultat réel.</p></div>
              <p className="text-xs leading-relaxed text-muted-foreground">Échange illustratif. Aucune donnée d’artiste ni action réelle n’est exécutée sur cette page.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section className="radar-section"><div className="radar-site-container">
      <p className="radar-kicker">Moins de détours, plus de contexte</p>
      <h2 className="radar-display mt-4 max-w-2xl">Votre agence reste au centre.<br />La conversation devient un accès.</h2>
      <div className="mt-10 grid gap-5 lg:grid-cols-3">{uses.map(({ icon: Icon, title, text, prompt }) => <article key={title} className="flex flex-col rounded-2xl border bg-white p-6"><span className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/[0.07] text-primary"><Icon size={22} /></span><h3 className="text-lg font-semibold tracking-tight">{title}</h3><p className="mt-3 flex-1 text-sm leading-relaxed text-muted-foreground">{text}</p><p className="mt-6 border-t pt-5 text-sm leading-relaxed">« {prompt} »</p></article>)}</div>
    </div></section>

    <section className="radar-section border-y bg-white"><div className="radar-site-container grid gap-12 lg:grid-cols-[.8fr_1fr]">
      <div><p className="radar-kicker">Une connexion maîtrisée</p><h2 className="radar-display mt-4">Vos données.<br />Vos autorisations.</h2><p className="mt-5 max-w-md text-sm leading-relaxed text-muted-foreground">MCP est le protocole qui relie l’assistant aux outils Radar. Il ne remplace ni votre abonnement, ni les autorisations de votre équipe.</p><Link href="/doc/mcp" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary">Comprendre la connexion<ArrowRight size={16} /></Link></div>
      <div className="space-y-7">{safeguards.map(({ icon: Icon, title, text }) => <article key={title} className="flex gap-4"><Icon className="mt-1 shrink-0 text-primary" size={21} /><div><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{text}</p></div></article>)}<p className="rounded-xl border p-4 text-xs leading-relaxed text-muted-foreground">Les résultats peuvent contenir des données métier. Vérifiez les règles de votre agence et les conditions du client d’IA avant de partager des informations confidentielles.</p></div>
    </div></section>

    <section className="radar-section"><div className="radar-site-container">
      <div className="grid overflow-hidden rounded-3xl border border-primary/15 bg-primary/[0.04] lg:grid-cols-[1.2fr_1fr]">
        <div className="p-7 sm:p-10"><p className="radar-kicker">Radar Addons</p><h2 className="radar-display mt-4">Une extension.<br />Un accord clair.</h2><p className="mt-5 max-w-lg text-sm leading-relaxed text-muted-foreground">Le connecteur complète votre abonnement Radar. Nous confirmons avec vous le périmètre utile, les conditions et l’activation du workspace.</p></div>
        <div className="flex flex-col justify-center border-t border-primary/10 bg-white/80 p-7 sm:p-10 lg:border-l lg:border-t-0"><span className="text-xs font-semibold uppercase tracking-wider text-primary">Extension payante</span><p className="mt-3 text-3xl font-semibold tracking-tight">Conditions sur demande</p><p className="mt-4 text-sm leading-relaxed text-muted-foreground">Aucun achat automatique. Les coûts éventuels de ChatGPT et des fournisseurs externes sont distincts.</p><Button asChild className="mt-6 w-fit gap-2"><Link href="/contact?offer=mcp">Parlons de votre connexion<ArrowUpRight size={16} /></Link></Button></div>
      </div>
      <div className="mx-auto mt-16 max-w-3xl"><h2 className="text-2xl font-semibold tracking-tight">Avant de vous connecter</h2><div className="mt-6 divide-y border-y">{faqs.map(([question, answer]) => <details key={question} className="group py-5"><summary className="cursor-pointer text-sm font-semibold leading-relaxed marker:text-primary">{question}</summary><p className="mt-3 text-sm leading-relaxed text-muted-foreground">{answer}</p></details>)}</div></div>
    </div></section>

    <section className="border-t bg-white py-14"><div className="radar-site-container flex flex-col justify-between gap-6 sm:flex-row sm:items-center"><div className="flex items-start gap-4"><BookOpen className="mt-1 shrink-0 text-primary" size={27} /><div><h2 className="text-xl font-semibold tracking-tight">Votre prochain repère : la documentation.</h2><p className="mt-2 text-sm text-muted-foreground">Connexion, permissions, outils artistes et guides de toute la plateforme.</p></div></div><Button asChild variant="outline" className="shrink-0 gap-2"><Link href="/doc">Explorer la documentation<ArrowRight size={16} /></Link></Button></div></section>
  </main></PublicPage>;
}
