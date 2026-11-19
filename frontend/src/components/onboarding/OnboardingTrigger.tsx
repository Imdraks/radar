'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { RadarFace } from '@/components/mascot/RadarFace';
import { useOnboarding } from './OnboardingContext';

interface OnboardingTriggerProps { variant?: 'icon' | 'button' | 'menu'; className?: string; }

export function OnboardingTrigger({ variant = 'icon', className }: OnboardingTriggerProps) {
  const { guideOpen, openGuide } = useOnboarding();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const attentive = hovered || focused;
  const face = <RadarFace size={variant === 'icon' ? 30 : 24} active={!guideOpen} attentive={attentive} />;
  const interactions = { onFocus: () => setFocused(true), onBlur: () => setFocused(false), onPointerEnter: () => setHovered(true), onPointerLeave: () => setHovered(false) };
  if (variant === 'menu') return <button type="button" onClick={openGuide} {...interactions} className={`flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent ${className || ''}`}>{face}Radar, mon guide</button>;
  if (variant === 'button') return <Button variant="outline" size="sm" onClick={openGuide} {...interactions} className={className}>{face}<span className="ml-2">Radar, mon guide</span></Button>;
  return <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" aria-label="Ouvrir l’aide Radar" onClick={openGuide} {...interactions} className={className}>{face}</Button></TooltipTrigger><TooltipContent>Radar — aide et premiers pas</TooltipContent></Tooltip>;
}
