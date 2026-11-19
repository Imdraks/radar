'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSonner } from 'sonner';
import { useToast } from '@/components/ui/toaster';
import type { RadarExpression } from './expressions';

const reactions: Record<string, RadarExpression> = {
  success: 'satisfied', error: 'disappointed', warning: 'intrigued',
};

/** Observe actual user feedback; never infer a saved result from an HTTP read. */
export function useRadarReaction(scope: string, enabled: boolean) {
  const { toasts: sonner } = useSonner();
  const { toasts: custom } = useToast();
  const [expression, setExpression] = useState<RadarExpression>();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const seen = useRef(new Map<string, string>());
  const currentScope = useRef(scope);
  const initialized = useRef(false);
  const react = useCallback((next: RadarExpression) => {
    clearTimeout(timer.current);
    setExpression(next);
    timer.current = setTimeout(() => setExpression(undefined), 3000);
  }, []);

  useEffect(() => {
    // Sonner's snapshot is newest first. Keep memory bounded without replaying old entries.
    const snapshot = [
      ...sonner.slice(0, 100).map(t => ({ key: `sonner:${t.id}`, type: t.type || '' })),
      ...custom.map(t => ({ key: `custom:${t.id}`, type: t.type })),
    ];
    const fresh = snapshot.filter(t => seen.current.get(t.key) !== t.type);
    seen.current = new Map(snapshot.map(t => [t.key, t.type]));
    // Ignore notifications already visible when a new page/header mounts.
    if (!initialized.current) { initialized.current = true; return; }
    if (scope !== currentScope.current || !enabled) {
      currentScope.current = scope;
      clearTimeout(timer.current);
      setExpression(undefined);
      return;
    }
    if (document.hidden) return;
    // Errors take precedence over simultaneous confirmations; duplicate renders do not replay.
    const next = ['error', 'warning', 'success'].find(type => fresh.some(t => t.type === type));
    if (next) react(reactions[next]);
  }, [sonner, custom, scope, enabled, react]);

  useEffect(() => {
    const invalid = (event: Event) => {
      if (enabled && !document.hidden && event.target instanceof HTMLElement && event.target.closest('#radar-main, [role="dialog"]')) react('intrigued');
    };
    const hide = () => {
      if (document.hidden) { clearTimeout(timer.current); setExpression(undefined); }
    };
    document.addEventListener('invalid', invalid, true);
    document.addEventListener('visibilitychange', hide);
    return () => {
      clearTimeout(timer.current);
      document.removeEventListener('invalid', invalid, true);
      document.removeEventListener('visibilitychange', hide);
    };
  }, [enabled, scope, react]);

  return expression;
}
