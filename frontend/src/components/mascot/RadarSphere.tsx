'use client';

import { useEffect, useRef, useState } from 'react';
import './radar-sphere.css';

type Expression = 'neutral' | 'awake' | 'dreamy' | 'yawn' | 'wink';
export type SphereMood = 'calm' | 'curious' | 'idea';

/** Decorative face: no requests, microphone, cursor storage or animation dependency. */
export function RadarSphere({ size = 96, mood = 'calm', active = true, attentive = false, cue = 0 }: {
  size?: number; mood?: SphereMood; active?: boolean; attentive?: boolean; cue?: number;
}) {
  const root = useRef<HTMLSpanElement>(null);
  const nearby = useRef(false);
  const focused = useRef(attentive);
  focused.current = attentive;
  const [near, setNear] = useState(false);
  const [expression, setExpression] = useState<Expression>('neutral');
  const [blinking, setBlinking] = useState(false);
  const [motion, setMotion] = useState(false);
  const [inView, setInView] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);
  const moving = active && motion && inView && pageVisible;

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotion = () => setMotion(!preference.matches);
    const updateVisibility = () => setPageVisible(!document.hidden);
    updateMotion(); updateVisibility();
    preference.addEventListener('change', updateMotion);
    document.addEventListener('visibilitychange', updateVisibility);
    const observer = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(entries => setInView(entries[0]?.isIntersecting ?? false));
    if (root.current) observer?.observe(root.current);
    return () => { preference.removeEventListener('change', updateMotion); document.removeEventListener('visibilitychange', updateVisibility); observer?.disconnect(); };
  }, []);

  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const timers = new Set<ReturnType<typeof setTimeout>>();
    let frame = 0;
    const later = (callback: () => void, delay: number) => {
      const timer = setTimeout(() => { timers.delete(timer); callback(); }, delay);
      timers.add(timer);
    };
    const restore = () => setExpression(nearby.current || focused.current ? 'awake' : 'neutral');
    const gaze = (x: number, y: number) => {
      element.style.setProperty('--look-x', `${x.toFixed(2)}px`);
      element.style.setProperty('--look-y', `${y.toFixed(2)}px`);
    };
    nearby.current = false; setNear(false); setBlinking(false); gaze(0, 0);
    if (!moving) { setExpression('neutral'); return; }
    setExpression('awake'); later(restore, 1100);
    const blink = () => {
      setBlinking(true);
      later(() => setBlinking(false), 130);
      later(blink, 2400 + Math.random() * 4200);
    };
    const observe = () => {
      if (!nearby.current && !focused.current) gaze((Math.random() - .5) * 6, (Math.random() - .5) * 4);
      later(observe, 3200 + Math.random() * 3200);
    };
    const wonder = () => {
      if (!nearby.current && !focused.current) {
        const expressions: Expression[] = ['dreamy', 'yawn', 'wink'];
        const next = expressions[Math.floor(Math.random() * expressions.length)];
        setExpression(next);
        if (next === 'dreamy') gaze(1, -4);
        later(restore, next === 'wink' ? 850 : 1600);
      }
      later(wonder, 8500 + Math.random() * 7000);
    };
    later(blink, 1400 + Math.random() * 2000);
    later(observe, 2000);
    later(wonder, 7000 + Math.random() * 5000);
    const pointer = (event: PointerEvent) => {
      if (event.pointerType === 'touch' || frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const rect = element.getBoundingClientRect();
        const dx = event.clientX - rect.left - rect.width / 2;
        const dy = event.clientY - rect.top - rect.height / 2;
        const radius = Math.max(120, size * 1.3);
        const close = Math.hypot(dx, dy) <= radius;
        if (nearby.current !== close) {
          nearby.current = close; setNear(close); setExpression(close || focused.current ? 'awake' : 'neutral');
        }
        if (close) gaze(Math.max(-4, Math.min(4, dx / radius * 5)), Math.max(-3, Math.min(3, dy / radius * 4)));
      });
    };
    window.addEventListener('pointermove', pointer, { passive: true });
    return () => { timers.forEach(clearTimeout); cancelAnimationFrame(frame); window.removeEventListener('pointermove', pointer); };
  }, [moving, size, attentive, cue]);

  const visibleMood = near ? 'curious' : mood;
  return <span ref={root} className="radar-sphere" aria-hidden="true" data-mood={visibleMood} data-expression={attentive && moving ? 'awake' : expression} data-blink={blinking} data-moving={moving} data-attentive={near || attentive || expression === 'awake'} style={{ width: size, height: size }}>
    <svg viewBox="0 0 100 100" focusable="false" className="radar-sphere-face">
      <g className="radar-sphere-gaze">
        <g className="radar-sphere-eye radar-sphere-eye-left"><ellipse cx="36" cy="44" rx="8.5" ry="11" /><circle cx="33.5" cy="40" r="2.2" className="radar-sphere-glint" /></g>
        <g className="radar-sphere-eye radar-sphere-eye-right"><ellipse cx="64" cy="44" rx="8.5" ry="11" /><circle cx="61.5" cy="40" r="2.2" className="radar-sphere-glint" /></g>
        <path className="radar-sphere-mouth radar-sphere-smile" d="M42 65 Q50 72 58 65" />
        <ellipse className="radar-sphere-mouth radar-sphere-yawn" cx="50" cy="67" rx="4" ry="5.5" />
      </g>
    </svg>
  </span>;
}
