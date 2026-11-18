'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { RouteTransition } from './route-transition';

/** Progressive enhancement: content stays visible without JS or animation APIs. */
export function SiteMotion() {
  const pathname = usePathname();

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const animations = new Set<Animation>();
    let observer: IntersectionObserver | undefined;
    const stop = () => {
      observer?.disconnect();
      animations.forEach(animation => animation.cancel());
      animations.clear();
    };
    const animate = (element: Element, frames: Keyframe[], duration: number) => {
      if (typeof element.animate !== 'function' || preference.matches) return;
      const animation = element.animate(frames, {
        duration, easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      });
      animations.add(animation);
      animation.onfinish = () => animations.delete(animation);
    };
    const start = () => {
      stop();
      if (preference.matches) return;
      if (!('IntersectionObserver' in window)) return;
      observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          observer?.unobserve(entry.target);
          animate(entry.target, [
            { opacity: 0.6, transform: 'translateY(12px)' },
            { opacity: 1, transform: 'translateY(0)' },
          ], 380);
        }
      }, { threshold: 0.08 });
      // Observe public content only; never animate tables, drag targets or maps.
      document.querySelectorAll('.radar-public .radar-section > .radar-site-container, .radar-auth-story')
        .forEach(element => observer?.observe(element));
    };
    start();
    preference.addEventListener('change', start);
    return () => { stop(); preference.removeEventListener('change', start); };
  }, [pathname]);

  return <RouteTransition />;
}
