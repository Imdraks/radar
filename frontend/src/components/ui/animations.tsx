'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface AnimatedContainerProps {
  children: ReactNode;
  animation?: 'fade-in' | 'fade-in-up' | 'fade-in-down' | 'slide-in-left' | 'slide-in-right' | 'scale-in';
  delay?: number;
  className?: string;
}

export function AnimatedContainer({
  children,
  animation = 'fade-in-up',
  delay = 0,
  className,
}: AnimatedContainerProps) {
  const delayClass = delay > 0 ? `animate-delay-${delay}` : '';
  
  return (
    <div
      className={cn(
        `animate-${animation} animate-fill-both`,
        delayClass,
        className
      )}
      style={delay > 0 && delay % 100 !== 0 ? { animationDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}

interface StaggeredListProps {
  children: ReactNode[];
  animation?: 'fade-in-up' | 'slide-in-left' | 'slide-in-right' | 'scale-in';
  baseDelay?: number;
  staggerDelay?: number;
  className?: string;
  itemClassName?: string;
}

export function StaggeredList({
  children,
  animation = 'fade-in-up',
  baseDelay = 0,
  staggerDelay = 100,
  className,
  itemClassName,
}: StaggeredListProps) {
  return (
    <div className={className}>
      {children.map((child, index) => (
        <div
          key={index}
          className={cn(`animate-${animation} animate-fill-both`, itemClassName)}
          style={{ animationDelay: `${baseDelay + index * staggerDelay}ms` }}
        >
          {child}
        </div>
      ))}
    </div>
  );
}

interface SkeletonCardProps {
  className?: string;
}

export function SkeletonCard({ className }: SkeletonCardProps) {
  return (
    <div className={cn('rounded-xl border bg-card p-4 space-y-3', className)}>
      <div className="skeleton h-4 w-3/4" />
      <div className="skeleton h-3 w-1/2" />
      <div className="space-y-2">
        <div className="skeleton h-3 w-full" />
        <div className="skeleton h-3 w-5/6" />
      </div>
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function LoadingSpinner({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };
  
  return (
    <div className={cn('flex items-center justify-center', className)}>
      <div className={cn(
        'animate-spin rounded-full border-2 border-primary/20 border-t-primary',
        sizeClasses[size]
      )} />
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <LoadingSpinner size="lg" />
      <p className="text-muted-foreground text-sm animate-pulse">Chargement...</p>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] text-center p-8 animate-fade-in">
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
          <Icon className="h-8 w-8 text-muted-foreground" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-foreground mb-1">{title}</h3>
      {description && (
        <p className="text-muted-foreground text-sm max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}
