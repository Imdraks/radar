import type { SVGProps } from 'react';
import { cn } from '@/lib/utils';

/** Radar adaptation of the Uiverse.io loader by mobinkakei. No IDs: safe to repeat. */
export function RadarSpinner({ size = 32, className, ...props }: SVGProps<SVGSVGElement> & { size?: number | string }) {
  // The concentric arcs animate individually; legacy spin utilities must not rotate the SVG too.
  const classes = className?.split(/\s+/).filter(value => value !== 'animate-spin').join(' ');
  return <svg width={size} height={size} viewBox="0 0 86 86" fill="none" aria-hidden="true" focusable="false" data-radar-loading="true" className={cn('radar-spinner shrink-0', classes)} {...props}>
    {[{ name: 'outer', radius: 40 }, { name: 'middle', radius: 27 }, { name: 'inner', radius: 14 }].map(ring => <g key={ring.name} className={`radar-spinner-${ring.name}`}>
      <circle className="radar-spinner-back" cx="43" cy="43" r={ring.radius} />
      <circle className="radar-spinner-front" cx="43" cy="43" r={ring.radius} />
    </g>)}
    <circle className="radar-spinner-signal" cx="43" cy="43" r="2.8" fill="currentColor" />
  </svg>;
}

export function RadarLoader({ label = 'Chargement…', className }: { label?: string; className?: string }) {
  return <div role="status" aria-live="polite" aria-atomic="true" className={cn('radar-loader inline-flex flex-col items-center justify-center gap-5 text-primary', className)}>
    <RadarSpinner size={86} />
    <div aria-hidden="true" className="flex max-w-full flex-col items-center gap-2 text-center">
      <span className="text-[10px] font-semibold uppercase tracking-[.25em] text-primary">Radar</span>
      <span className="radar-loader-caption text-sm text-muted-foreground" data-text={label}>{label}</span>
    </div>
    <span className="sr-only">{label}</span>
  </div>;
}
