'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ArrowUpRight, Check, ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { RadarSphere, type SphereMood } from '@/components/mascot/RadarSphere';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { useOnboarding } from './OnboardingContext';

const WELCOME_STORAGE_KEY = 'opportunities-radar-welcome-shown-v2';
const stages: { label: string; mood: SphereMood; message: string }[] = [
  { label: 'Espace', mood: 'calm', message: 'Salut, moi c’est Radar. Je vous montre les premiers repères ?' },
  { label: 'Connexions', mood: 'curious', message: 'Vos outils se relient ici. Chaque connexion reste entre vos mains.' },
  { label: 'Outils', mood: 'idea', message: 'Une idée ? Commençons par le bon outil.' },
  { label: 'Bienvenue', mood: 'calm', message: 'Je reste juste là, dans la barre du haut, si vous avez besoin d’un repère.' },
];
const tools = [
  { path: '/projects', label: 'Projets', detail: 'Les étapes et ressources de votre production.' },
  { path: '/production', label: 'Tâches et production', detail: 'Le travail à organiser avec votre équipe.' },
  { path: '/agency-calendar', label: 'Calendrier', detail: 'Vos dates et vos échéances.' },
  { path: '/assets', label: 'Fichiers', detail: 'Les ressources de votre espace.' },
  { path: '/discovery', label: 'Discovery', detail: 'Les artistes et les données disponibles.' },
  { path: '/events', label: 'Événements', detail: 'La préparation de vos événements.' },
  { path: '/clients', label: 'Clients et prospects', detail: 'Vos relations commerciales.' },
  { path: '/devis', label: 'Devis', detail: 'Vos propositions commerciales.' },
  { path: '/factures', label: 'Factures', detail: 'Votre facturation et le suivi des paiements.' },
];

export function WelcomeModal() {
  const { guideOpen, openGuide, closeGuide, hasCompletedOnboarding, skipOnboarding } = useOnboarding();
  const { navigation, subscription } = useSubscriptionStore();
  const [step, setStep] = useState(0);
  const helpTrigger = useRef<HTMLButtonElement | null>(null);
  const paths = new Set(Object.values(navigation || {}).flat().filter(item => item.available && !item.locked)
    .flatMap(item => [item.path, ...(item.context_links || []).map(link => link.path)]));
  const availableTools = tools.filter(tool => paths.has(tool.path));
  const canConfigure = paths.has('/workspace/settings');

  useEffect(() => {
    try {
      if (!guideOpen && !localStorage.getItem(WELCOME_STORAGE_KEY) && !hasCompletedOnboarding) {
        const timer = setTimeout(openGuide, 500);
        return () => clearTimeout(timer);
      }
    } catch { /* Help can still be opened manually when storage is unavailable. */ }
  }, [guideOpen, hasCompletedOnboarding, openGuide]);
  useEffect(() => {
    if (guideOpen) {
      setStep(0);
      helpTrigger.current = document.querySelector<HTMLButtonElement>('[aria-label="Ouvrir l’aide Radar"]');
    }
  }, [guideOpen]);
  const finish = () => { closeGuide(); skipOnboarding(); };

  return <Dialog open={guideOpen} onOpenChange={open => { if (!open) closeGuide(); }}>
    <DialogContent closeLabel="Fermer le guide Radar" aria-describedby="radar-guide-description" onCloseAutoFocus={event => { event.preventDefault(); if (helpTrigger.current?.isConnected) helpTrigger.current.focus(); }} className="max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-3xl p-0 sm:rounded-3xl">
      <div className="border-b px-5 pb-5 pt-6 sm:px-8">
        <DialogTitle className="pr-7 text-xl font-semibold tracking-tight">Bienvenue sur Radar</DialogTitle>
        <DialogDescription id="radar-guide-description" className="mt-2 text-sm">Un point de repère pour votre espace, vos connexions et vos outils.</DialogDescription>
        <ol aria-label="Étapes du guide Radar" className="mt-6 grid grid-cols-4 gap-2">
          {stages.map((stage, index) => <li key={stage.label} aria-current={step === index ? 'step' : undefined} className={`flex flex-col items-center gap-2 text-center text-[10px] sm:flex-row sm:text-xs ${step === index ? 'font-semibold text-primary' : 'text-muted-foreground'}`}><span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border ${step === index ? 'border-primary bg-primary text-white' : index < step ? 'border-primary/10 bg-primary/10 text-primary' : ''}`}>{index < step ? <Check size={13} aria-hidden="true" /> : index + 1}</span>{stage.label}</li>)}
        </ol>
      </div>
      <div className="grid gap-6 p-5 sm:grid-cols-[180px_1fr] sm:gap-8 sm:p-8">
        <aside className="flex flex-col items-center gap-4 sm:border-r sm:pr-7"><RadarSphere size={132} mood={stages[step].mood} cue={step} active={guideOpen} /><p className="rounded-2xl bg-primary/5 p-4 text-xs leading-6 text-foreground sm:text-center">{stages[step].message}</p></aside>
        <div className="min-w-0 self-center">
          {step === 0 && <section aria-labelledby="radar-guide-space"><p className="radar-eyebrow">Votre espace de travail</p><h2 id="radar-guide-space" className="mt-3 text-2xl font-semibold tracking-tight">Un même endroit pour avancer.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Retrouvez vos projets, vos ressources et les outils accessibles à votre équipe. Je vous accompagne avec quelques repères, à votre rythme.</p>{subscription?.workspace_name && <p className="mt-5 rounded-xl border bg-card p-4 text-sm"><span className="block text-xs text-muted-foreground">Espace actuel</span><strong className="mt-1 block break-words font-medium">{subscription.workspace_name}</strong></p>}</section>}
          {step === 1 && <section aria-labelledby="radar-guide-connections"><p className="radar-eyebrow">Vos intégrations</p><h2 id="radar-guide-connections" className="mt-3 text-2xl font-semibold tracking-tight">Reliez les outils de votre agence.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Google Drive et Calendar se connectent depuis les paramètres de l’espace. Leur disponibilité dépend de la configuration et de l’autorisation de votre compte Google.</p><p className="mt-3 text-xs leading-6 text-muted-foreground">{canConfigure ? 'Vous pouvez ouvrir les réglages pour configurer vos connexions.' : 'L’administrateur de votre espace gère ces connexions.'}</p>{canConfigure && <Button asChild variant="outline" className="mt-5"><Link href="/workspace/settings" onClick={closeGuide}>Configurer les intégrations<ArrowUpRight size={15} className="ml-2" /></Link></Button>}<p className="mt-4 text-xs leading-5 text-muted-foreground">Vous pouvez revenir à ce guide après avoir configuré vos intégrations.</p></section>}
          {step === 2 && <section aria-labelledby="radar-guide-tools"><p className="radar-eyebrow">À vous de choisir</p><h2 id="radar-guide-tools" className="mt-3 text-2xl font-semibold tracking-tight">Vos outils, à portée de main.</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">Les accès ci-dessous suivent les droits de votre espace.</p><div className="mt-5 grid gap-2 sm:grid-cols-2">{availableTools.map(tool => <Link key={tool.path} href={tool.path} onClick={closeGuide} className="rounded-xl border bg-card p-3 transition-colors hover:border-primary/40"><span className="flex items-center justify-between gap-2 text-xs font-semibold">{tool.label}<ArrowUpRight size={13} className="shrink-0 text-primary" /></span><span className="mt-1 block text-[11px] leading-5 text-muted-foreground">{tool.detail}</span></Link>)}</div>{!availableTools.length && <p role="status" className="mt-4 text-sm text-muted-foreground">Vos accès ne sont pas encore disponibles ici. Retrouvez vos outils dans la navigation de l’espace.</p>}</section>}
          {step === 3 && <section aria-labelledby="radar-guide-ready"><p className="radar-eyebrow">Votre prochain pas</p><h2 id="radar-guide-ready" className="mt-3 text-2xl font-semibold tracking-tight">Les premiers repères sont posés.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Choisissez un outil dans la navigation pour commencer. Vous pouvez me retrouver à tout moment dans la barre du haut pour revoir ce guide.</p><Link href="/doc" onClick={closeGuide} className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary">Explorer la documentation<ArrowUpRight size={15} /></Link></section>}
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t p-5 sm:px-8"><Button variant="ghost" size="sm" onClick={step > 0 ? () => setStep(value => value - 1) : closeGuide}>{step > 0 ? <><ChevronLeft size={15} className="mr-1" />Précédent</> : 'Explorer à mon rythme'}</Button><Button onClick={step === stages.length - 1 ? finish : () => setStep(value => value + 1)}>{step === stages.length - 1 ? 'Continuer dans Radar' : 'Continuer'}<ArrowRight size={15} className="ml-2" /></Button></div>
    </DialogContent>
  </Dialog>;
}
