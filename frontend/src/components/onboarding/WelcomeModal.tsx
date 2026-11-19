'use client';

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import './radar-guide.css';
import { ArrowRight, ArrowUpRight, Check, ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { RadarFace, type RadarMood } from '@/components/mascot/RadarFace';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { useOnboarding } from './OnboardingContext';

const WELCOME_STORAGE_KEY = 'opportunities-radar-welcome-shown-v2';
const stages: { label: string; mood: RadarMood; message: string }[] = [
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
  const [direction, setDirection] = useState(1);
  const reduceMotion = useReducedMotion();
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
  useLayoutEffect(() => {
    if (guideOpen) {
      setStep(0);
      setDirection(1);
      helpTrigger.current = document.querySelector<HTMLButtonElement>('[aria-label="Ouvrir l’aide Radar"]');
    }
  }, [guideOpen]);
  const advance = (delta: number) => { setDirection(delta); setStep(value => Math.max(0, Math.min(stages.length - 1, value + delta))); };
  const finish = () => { closeGuide(); skipOnboarding(); };

  return <Dialog open={guideOpen} onOpenChange={open => { if (!open) closeGuide(); }}>
    <DialogContent closeLabel="Fermer le guide Radar" aria-describedby="radar-guide-description" onCloseAutoFocus={event => { event.preventDefault(); if (helpTrigger.current?.isConnected) helpTrigger.current.focus(); }} className="radar-guide">
      <header className="radar-guide-header">
        <span className="radar-guide-brand">Radar<span>.</span></span>
        <DialogTitle className="sr-only">Bienvenue sur Radar</DialogTitle>
        <DialogDescription id="radar-guide-description" className="sr-only">Un point de repère pour votre espace, vos connexions et vos outils.</DialogDescription>
        <ol aria-label="Étapes du guide Radar" className="radar-guide-steps">
          {stages.map((stage, index) => <li key={stage.label} aria-label={`Étape ${index + 1} : ${stage.label}`} aria-current={step === index ? 'step' : undefined} data-complete={index < step}><span className="radar-guide-step-number">{index < step ? <Check size={13} aria-hidden="true" /> : index + 1}</span><span className="radar-guide-step-label">{stage.label}</span></li>)}
        </ol>
      </header>
      <div className="radar-guide-progress" aria-hidden="true"><span style={{ width: `${(step + 1) / stages.length * 100}%` }} /></div>
      <div className="radar-guide-scroll">
      <div className="radar-guide-main">
        <aside className="radar-guide-mascot"><RadarFace size={240} mood={stages[step].mood} cue={step} active={guideOpen} /><p>{stages[step].message}</p></aside>
        <div className="radar-guide-copy">
        <AnimatePresence mode="wait" initial={false} custom={direction}>
        <motion.div key={step} custom={direction} variants={{ enter: (way: number) => ({ opacity: 0, y: reduceMotion ? 0 : 18 * way }), center: { opacity: 1, y: 0 }, exit: (way: number) => ({ opacity: 0, y: reduceMotion ? 0 : -12 * way }) }} initial="enter" animate="center" exit="exit" transition={{ duration: reduceMotion ? 0 : .22, ease: [.22, 1, .36, 1] }}>

          {step === 0 && <section aria-labelledby="radar-guide-space"><p className="radar-eyebrow">Votre espace de travail</p><h2 id="radar-guide-space" className="mt-3 text-2xl font-semibold tracking-tight">Un même endroit pour avancer.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Retrouvez vos projets, vos ressources et les outils accessibles à votre équipe. Je vous accompagne avec quelques repères, à votre rythme.</p>{subscription?.workspace_name && <p className="mt-5 rounded-xl border bg-card p-4 text-sm"><span className="block text-xs text-muted-foreground">Espace actuel</span><strong className="mt-1 block break-words font-medium">{subscription.workspace_name}</strong></p>}</section>}
          {step === 1 && <section aria-labelledby="radar-guide-connections"><p className="radar-eyebrow">Vos intégrations</p><h2 id="radar-guide-connections" className="mt-3 text-2xl font-semibold tracking-tight">Reliez les outils de votre agence.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Google Drive et Calendar se connectent depuis les paramètres de l’espace. Leur disponibilité dépend de la configuration et de l’autorisation de votre compte Google.</p><p className="mt-3 text-xs leading-6 text-muted-foreground">{canConfigure ? 'Vous pouvez ouvrir les réglages pour configurer vos connexions.' : 'L’administrateur de votre espace gère ces connexions.'}</p>{canConfigure && <Button asChild variant="outline" className="mt-5"><Link href="/workspace/settings" onClick={closeGuide}>Configurer les intégrations<ArrowUpRight size={15} className="ml-2" /></Link></Button>}<p className="mt-4 text-xs leading-5 text-muted-foreground">Vous pouvez revenir à ce guide après avoir configuré vos intégrations.</p></section>}
          {step === 2 && <section aria-labelledby="radar-guide-tools"><p className="radar-eyebrow">À vous de choisir</p><h2 id="radar-guide-tools" className="mt-3 text-2xl font-semibold tracking-tight">Vos outils, à portée de main.</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">Les accès ci-dessous suivent les droits de votre espace.</p><div className="mt-5 grid gap-2 sm:grid-cols-2">{availableTools.map(tool => <Link key={tool.path} href={tool.path} onClick={closeGuide} className="rounded-xl border bg-card p-3 transition-colors hover:border-primary/40"><span className="flex items-center justify-between gap-2 text-xs font-semibold">{tool.label}<ArrowUpRight size={13} className="shrink-0 text-primary" /></span><span className="mt-1 block text-[11px] leading-5 text-muted-foreground">{tool.detail}</span></Link>)}</div>{!availableTools.length && <p role="status" className="mt-4 text-sm text-muted-foreground">Vos accès ne sont pas encore disponibles ici. Retrouvez vos outils dans la navigation de l’espace.</p>}</section>}
          {step === 3 && <section aria-labelledby="radar-guide-ready"><p className="radar-eyebrow">Votre prochain pas</p><h2 id="radar-guide-ready" className="mt-3 text-2xl font-semibold tracking-tight">Les premiers repères sont posés.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">Choisissez un outil dans la navigation pour commencer. Vous pouvez me retrouver à tout moment dans la barre du haut pour revoir ce guide.</p><Link href="/doc" onClick={closeGuide} className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary">Explorer la documentation<ArrowUpRight size={15} /></Link></section>}
        </motion.div>
        </AnimatePresence>
        </div>
      </div>
      </div>
      <footer className="radar-guide-footer"><Button variant="ghost" onClick={step > 0 ? () => advance(-1) : closeGuide}>{step > 0 ? <><ChevronLeft size={15} className="mr-1" />Précédent</> : 'Plus tard'}</Button><Button onClick={step === stages.length - 1 ? finish : () => advance(1)}>{step === stages.length - 1 ? 'Entrer dans Radar' : 'Continuer'}<ArrowRight size={15} className="ml-2" /></Button></footer>
    </DialogContent>
  </Dialog>;
}
