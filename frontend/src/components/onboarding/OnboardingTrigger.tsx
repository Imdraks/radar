'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { RadarFace } from '@/components/mascot/RadarFace';
import { useRadarReaction } from '@/components/mascot/useRadarReaction';
import { getRadarHelp } from '@/components/mascot/contextual-help';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { useOnboarding } from './OnboardingContext';

interface OnboardingTriggerProps { variant?: 'icon' | 'button' | 'menu'; className?: string; }

export function OnboardingTrigger({ variant = 'icon', className }: OnboardingTriggerProps) {
  const { helpOpen, openHelp, closeHelp, guideOpen, openGuide } = useOnboarding();
  const pathname = usePathname();
  const { navigation, subscription } = useSubscriptionStore();
  const launchGuide = useRef(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const reaction = useRadarReaction(`${pathname}:${subscription?.workspace_id ?? ''}`, !guideOpen && !helpOpen);
  const allowed = Object.values(navigation || {}).flat().filter(item => item.available && !item.locked)
    .flatMap(item => [item.path, ...(item.context_links || []).map(link => link.path)])
    .some(path => pathname === path || pathname.startsWith(path + '/'));
  const help = getRadarHelp(pathname, allowed);
  const face = <RadarFace size={variant === 'icon' ? 30 : 24} active={!guideOpen && !helpOpen} attentive={hovered || focused} expression={reaction} />;
  const interactions = { 'data-radar-reaction': reaction || 'idle', title: 'Radar — aide pour cette page', onFocus: () => setFocused(true), onBlur: () => setFocused(false), onPointerEnter: () => setHovered(true), onPointerLeave: () => setHovered(false) };
  const trigger = variant === 'menu'
    ? <button type="button" {...interactions} className={`flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent ${className || ''}`}>{face}Radar, mon guide</button>
    : variant === 'button'
      ? <Button variant="outline" size="sm" {...interactions} className={className}>{face}<span className="ml-2">Radar, mon guide</span></Button>
      : <Button variant="ghost" size="icon" aria-label="Ouvrir l’aide Radar" {...interactions} className={className}>{face}</Button>;

  return <Sheet open={helpOpen} onOpenChange={open => open ? openHelp() : closeHelp()}>
    <SheetTrigger asChild>{trigger}</SheetTrigger>
    <SheetContent side="right" closeLabel="Fermer l’aide Radar" className="radar-app w-full overflow-y-auto bg-card sm:max-w-md" onCloseAutoFocus={() => {
      // Open the full guide only after the sheet has released its focus trap.
      if (launchGuide.current) { launchGuide.current = false; openGuide(); }
    }}>
      <div className="mb-6 flex items-center gap-4 pr-6"><RadarFace size={70} active={helpOpen} /><div><p className="text-xs font-medium text-primary">Radar, votre repère</p><SheetTitle className="mt-1 text-xl">{help.title}</SheetTitle></div></div>
      <SheetDescription className="text-sm leading-7">{help.description}</SheetDescription>
      {help.steps.length > 0 && <ol className="my-6 list-decimal space-y-4 pl-5 text-sm leading-7 marker:font-semibold marker:text-primary">{help.steps.map(step => <li key={step} className="pl-2">{step}</li>)}</ol>}
      {help.note && <p className="my-5 rounded-xl border bg-secondary/50 p-4 text-sm leading-7 text-muted-foreground">{help.note}</p>}
      <p className="mt-5 text-xs leading-6 text-muted-foreground">Les actions disponibles dépendent de votre rôle, de votre abonnement et des intégrations connectées.</p>
      <div className="mt-7 flex flex-col gap-3 border-t pt-6">
        <Button asChild variant="outline"><Link href={help.href} onClick={() => closeHelp()}><BookOpen size={16} className="mr-2" />Lire le guide complet<ArrowUpRight size={14} className="ml-2" /></Link></Button>
        <Button variant="ghost" onClick={() => { launchGuide.current = true; closeHelp(); }}>Revoir les premiers pas</Button>
      </div>
    </SheetContent>
  </Sheet>;
}
