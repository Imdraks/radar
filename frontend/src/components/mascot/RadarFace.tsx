'use client';

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import './radar-face.css';
import { RADAR_EXPRESSIONS, RADAR_IDLE_EXPRESSIONS, type RadarExpression } from './expressions';
export { RADAR_EXPRESSIONS, type RadarExpression } from './expressions';

export type RadarMood = 'calm' | 'curious' | 'idea';

/** Real Inter glyphs, animated in the DOM. No image, SVG, canvas or external request. */
export function RadarFace({ size = 96, mood = 'calm', active = true, attentive = false, cue = 0, expression: requestedExpression }: {
  size?: number; mood?: RadarMood; active?: boolean; attentive?: boolean; cue?: number; expression?: RadarExpression;
}) {
  const root = useRef<HTMLSpanElement>(null);
  const nearby = useRef(false);
  const focused = useRef(attentive);
  focused.current = attentive;
  const [near, setNear] = useState(false);
  const [idleExpression, setExpression] = useState<RadarExpression>('neutral');
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
    const restore = () => setExpression(nearby.current || focused.current ? 'smile' : 'neutral');
    const gaze = (x: number, y: number) => {
      element.style.setProperty('--look-x', `${(x / 100).toFixed(4)}em`);
      element.style.setProperty('--look-y', `${(y / 100).toFixed(4)}em`);
    };
    nearby.current = false; setNear(false); setBlinking(false); gaze(0, 0);
    element.style.setProperty('--life-x', '0em');
    element.style.setProperty('--life-y', '0em');
    if (!moving) { setExpression('neutral'); return; }
    setExpression('neutral');
    const blink = () => {
      if (!requestedExpression) setBlinking(true);
      later(() => setBlinking(false), 130);
      later(blink, 2400 + Math.random() * 4200);
    };
    const observe = () => {
      if (!nearby.current && !focused.current) gaze((Math.random() - .5) * 6, (Math.random() - .5) * 4);
      later(observe, 3200 + Math.random() * 3200);
    };
    // Tiny, independently timed eye movements; never move the mouth or brows.
    const eyeLife = () => {
      if (!nearby.current && !focused.current) {
        element.style.setProperty('--life-x', `${((Math.random() - .5) * .012).toFixed(4)}em`);
        element.style.setProperty('--life-y', `${((Math.random() - .5) * .008).toFixed(4)}em`);
      }
      later(eyeLife, 900 + Math.random() * 1800);
    };
    const wonder = () => {
      if (!requestedExpression && !nearby.current && !focused.current) {
        const next = RADAR_IDLE_EXPRESSIONS[Math.floor(Math.random() * RADAR_IDLE_EXPRESSIONS.length)];
        setExpression(next);
        if (next === 'sleepy') gaze(1, -4);
        later(restore, next === 'wink' ? 850 : 1600);
      }
      later(wonder, 8500 + Math.random() * 7000);
    };
    later(blink, 1400 + Math.random() * 2000);
    later(observe, 2000);
    later(eyeLife, 800 + Math.random() * 900);
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
          nearby.current = close; setNear(close); setExpression(close || focused.current ? 'smile' : 'neutral');
        }
        if (close) {
          gaze(Math.max(-4, Math.min(4, dx / radius * 5)), Math.max(-3, Math.min(3, dy / radius * 4)));
          element.style.setProperty('--life-x', '0em');
          element.style.setProperty('--life-y', '0em');
        }
      });
    };
    window.addEventListener('pointermove', pointer, { passive: true });
    return () => { timers.forEach(clearTimeout); cancelAnimationFrame(frame); window.removeEventListener('pointermove', pointer); };
  }, [moving, size, attentive, cue, requestedExpression]);

  const visibleMood = near ? 'curious' : mood;
  const shown = requestedExpression ?? (attentive && moving ? 'smile' : idleExpression);
  const [leftBrow, rightBrow, leftEye, rightEye, mouth] = RADAR_EXPRESSIONS[shown];
  const left = blinking ? '-' : leftEye;
  const right = blinking ? '-' : rightEye;
  const roundEye = (glyph: string) => ['.', 'O', '0'].includes(glyph);
  const eyeGlyph = (glyph: string) => roundEye(glyph) ? '.' : glyph;
  const mouthShape = mouth === ')' ? 'smile' : mouth === '(' ? 'frown' : mouth === '3' ? 'lips' : 'plain';
  return <span ref={root} className="radar-mascot" aria-hidden="true" data-mood={visibleMood} data-expression={shown} data-blink={blinking} data-moving={moving} data-attentive={near || attentive} style={{ '--mascot-size': `${size}px` } as CSSProperties}>
    <span key={shown} className="radar-mascot-features">
    <span className="radar-mascot-brow radar-mascot-brow-left" data-double={leftBrow.length > 1}>{leftBrow}</span>
    <span className="radar-mascot-brow radar-mascot-brow-right" data-double={rightBrow.length > 1}>{rightBrow}</span>
    <span className="radar-mascot-gaze"><span className="radar-mascot-eye-life">
      <span className="radar-mascot-eye radar-mascot-eye-left" data-round={roundEye(left)} data-wide={left === 'O' || left === '0'}><span>{eyeGlyph(left)}</span></span>
      <span className="radar-mascot-eye radar-mascot-eye-right" data-round={roundEye(right)} data-wide={right === 'O' || right === '0'}><span>{eyeGlyph(right)}</span></span>
    </span></span>
    <span className="radar-mascot-mouth" data-shape={mouthShape}>{mouth}</span>
    </span>
  </span>;
}
