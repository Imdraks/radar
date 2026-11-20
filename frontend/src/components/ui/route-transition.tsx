'use client';

import { useLayoutEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';

/** Animate committed content, including pages mounted after an auth/loading gate.
 * Never wrap/key the route tree, intercept links, delay navigation or snapshot data.
 */
export function RouteTransition() {
  const pathname = usePathname();
  const previous = useRef(pathname);

  useLayoutEffect(() => {
    if (previous.current === pathname) return;
    previous.current = pathname;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (preference.matches) return;
    let observer: MutationObserver | undefined;
    let deadline: ReturnType<typeof setTimeout> | undefined;
    const animations = new Set<Animation>();
    const cancel = () => {
      observer?.disconnect();
      if (deadline) clearTimeout(deadline);
      animations.forEach(animation => animation.cancel());
      animations.clear();
    };
    const play = (element: Element, keyframes: Keyframe[], duration: number) => {
      if (typeof element.animate !== 'function') return;
      const animation = element.animate(keyframes, {
        duration, easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      });
      animations.add(animation);
      animation.onfinish = () => animations.delete(animation);
    };
    const reveal = () => {
      const content = document.querySelector('main, .radar-auth-card');
      if (!content || content.getAttribute('aria-busy') === 'true') return false;
      const title = content.querySelector('h1:not(.sr-only), h2');
      // Some business pages mount a spinner before their first heading. Wait
      // for that content too, while keeping the loader visible and interactive.
      if (!title && Array.from(content.querySelectorAll('.animate-spin, [data-radar-loading]'))
        .some(element => element.getClientRects().length > 0)) return false;
      if (preference.matches) { cancel(); return true; }
      observer?.disconnect();
      if (deadline) clearTimeout(deadline);
      // Keep fixed dialogs, maps, headers and sidebars in their own coordinates.
      play(content, [{ opacity: 0.3 }, { opacity: 1 }], 280);
      // Move only a heading, never the ancestor of a fixed-position overlay.
      if (title && !title.querySelector('[role="dialog"]')) {
        play(title, [{ opacity: 0.4, translate: '0 8px' }, { opacity: 1, translate: '0 0' }], 320);
      }
      return true;
    };
    if (!reveal() && typeof MutationObserver !== 'undefined') {
      observer = new MutationObserver(reveal);
      observer.observe(document.body, {
        childList: true, subtree: true, attributes: true, attributeFilter: ['aria-busy'],
      });
      // A failed/abandoned navigation must never leave a permanent body observer.
      deadline = setTimeout(() => observer?.disconnect(), 8000);
    }
    const onPreference = () => { if (preference.matches) cancel(); };
    preference.addEventListener('change', onPreference);
    return () => { cancel(); preference.removeEventListener('change', onPreference); };
  }, [pathname]);

  return null;
}
