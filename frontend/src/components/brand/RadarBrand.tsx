import { cn } from '@/lib/utils';

/** Radar's signal mark. Decorative geometry, never a data visualization. */
export function RadarMark({ className }: { className?: string }) {
  return <svg viewBox="0 0 48 48" fill="none" className={cn('h-11 w-11 shrink-0', className)} aria-hidden="true">
    <rect width="48" height="48" rx="15" fill="currentColor" />
    <circle cx="24" cy="24" r="15" stroke="white" strokeOpacity=".45" strokeWidth="1.4" />
    <circle cx="24" cy="24" r="9" stroke="white" strokeOpacity=".75" strokeWidth="1.4" />
    <path d="M24 24 34.5 13.5" stroke="white" strokeWidth="1.7" strokeLinecap="round" />
    <circle cx="24" cy="24" r="3" fill="white" />
    <circle cx="34.5" cy="13.5" r="3" fill="white" stroke="currentColor" strokeWidth="2" />
  </svg>;
}

export function RadarLogo({ className, compact = false, inverted = false }: { className?: string; compact?: boolean; inverted?: boolean }) {
  return <span className={cn('inline-flex items-center gap-3 text-primary', className)} role="img" aria-label="Radar">
    <RadarMark />{!compact && <span className={cn('text-[26px] font-semibold leading-none tracking-[-0.055em]', inverted ? 'text-white' : 'text-foreground')}>Radar<span className="text-primary">.</span></span>}
  </span>;
}

export function RadarField({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('radar-field relative', className)}><span /><span /><span /><span /><i /></div>;
}
