"use client";

import { memo, useMemo, useCallback, ComponentType, ReactNode } from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

/**
 * HOC to wrap components with React.memo for performance
 * Use for components that render frequently but don't change often
 */
export function withMemo<P extends object>(
  Component: ComponentType<P>,
  propsAreEqual?: (prevProps: Readonly<P>, nextProps: Readonly<P>) => boolean
): ComponentType<P> {
  return memo(Component, propsAreEqual) as unknown as ComponentType<P>;
}

/**
 * Create a lazy-loaded component with a loading spinner
 */
export function createLazyComponent<P extends object>(
  importFn: () => Promise<{ default: ComponentType<P> }>,
  loadingFallback?: ReactNode
) {
  return dynamic(importFn, {
    loading: () => (
      <div className="flex items-center justify-center p-4">
        {loadingFallback || <Loader2 className="h-6 w-6 animate-spin text-gray-400" />}
      </div>
    ),
    ssr: false, // Disable SSR for heavy components
  });
}

/**
 * Hook to create stable callbacks that don't change reference
 */
export function useStableCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  deps: React.DependencyList
): T {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useCallback(callback, deps);
}

/**
 * Hook to create expensive computed values only when dependencies change
 */
export function useExpensiveValue<T>(
  factory: () => T,
  deps: React.DependencyList
): T {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(factory, deps);
}

/**
 * Debounce hook for search inputs and filters
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Need to import these for useDebounce
import { useState, useEffect } from 'react';

/**
 * Throttle function for scroll handlers and resize events
 */
export function throttle<T extends (...args: unknown[]) => void>(
  func: T,
  limit: number
): T {
  let inThrottle = false;
  return ((...args: unknown[]) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  }) as T;
}

/**
 * Intersection Observer hook for lazy loading content
 */
export function useIntersectionObserver(
  elementRef: React.RefObject<Element>,
  options?: IntersectionObserverInit
): boolean {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect(); // Stop observing once visible
        }
      },
      { threshold: 0.1, ...options }
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, [elementRef, options]);

  return isVisible;
}

/**
 * Virtual list helper for large datasets
 * Returns only visible items based on scroll position
 */
export function useVirtualList<T>(
  items: T[],
  containerRef: React.RefObject<HTMLElement>,
  itemHeight: number,
  overscan: number = 5
) {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 20 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = throttle(() => {
      const scrollTop = container.scrollTop;
      const clientHeight = container.clientHeight;

      const start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
      const end = Math.min(
        items.length,
        Math.ceil((scrollTop + clientHeight) / itemHeight) + overscan
      );

      setVisibleRange({ start, end });
    }, 100);

    container.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial calculation

    return () => container.removeEventListener('scroll', handleScroll);
  }, [containerRef, items.length, itemHeight, overscan]);

  const visibleItems = useMemo(
    () => items.slice(visibleRange.start, visibleRange.end),
    [items, visibleRange]
  );

  const paddingTop = visibleRange.start * itemHeight;
  const paddingBottom = (items.length - visibleRange.end) * itemHeight;

  return {
    visibleItems,
    paddingTop,
    paddingBottom,
    totalHeight: items.length * itemHeight,
  };
}
