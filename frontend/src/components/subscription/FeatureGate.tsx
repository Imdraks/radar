"use client";
/**
 * Feature Gate Components
 * =======================
 * 
 * Components for gating features based on subscription:
 * - FeatureGate: Wrap content that requires a feature
 * - LockedFeature: Display upgrade prompt for locked features
 * - UpgradeBadge: Badge to show upgrade required
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Lock, Sparkles, ArrowUpRight, Crown } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { 
  useSubscriptionStore, 
  useFeature, 
  Feature,
  ADMIN_ONLY_FEATURES 
} from '@/store/subscriptionStore';

// ============================================================================
// FEATURE GATE
// ============================================================================

interface FeatureGateProps {
  feature: Feature;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showLocked?: boolean; // Show locked state vs hide completely
}

/**
 * Gate content based on feature availability
 * 
 * @example
 * <FeatureGate feature="analytics">
 *   <AnalyticsDashboard />
 * </FeatureGate>
 */
export function FeatureGate({ 
  feature, 
  children, 
  fallback,
  showLocked = true 
}: FeatureGateProps) {
  const hasFeature = useFeature(feature);
  const isAdmin = useSubscriptionStore((s) => s.isAdmin);
  
  // Admin-only features
  if (ADMIN_ONLY_FEATURES.includes(feature)) {
    if (isAdmin) return <>{children}</>;
    if (fallback) return <>{fallback}</>;
    return null; // Hidden for non-admins
  }
  
  if (hasFeature) {
    return <>{children}</>;
  }
  
  if (fallback) {
    return <>{fallback}</>;
  }
  
  if (showLocked) {
    return <LockedFeature feature={feature} />;
  }
  
  return null;
}

// ============================================================================
// LOCKED FEATURE
// ============================================================================

interface LockedFeatureProps {
  feature: Feature;
  title?: string;
  compact?: boolean;
}

/**
 * Display a locked feature prompt with upgrade CTA
 */
export function LockedFeature({ feature, title, compact = false }: LockedFeatureProps) {
  const upgradeMessage = useSubscriptionStore((s) => s.getUpgradeMessage(feature));
  const plan = useSubscriptionStore((s) => s.subscription?.plan);
  
  const featureLabels: Record<Feature, string> = {
    events: "Événements",
    cockpit: 'Cockpit',
    pipeline: 'Pipeline',
    projects: 'Projets',
    production: 'Production',
    assets: 'Assets',
    calendar: 'Calendrier',
    clients: 'Clients',
    dossiers: 'Dossiers',
    daily_picks: 'Daily Picks',
    leads: 'Leads',
    kanban_leads: 'Kanban Leads',
    scoring: 'Scoring',
    artists: 'Artistes',
    profiles: 'Profils',
    discovery: 'Découverte',
    comparison: 'Comparaison',
    map: 'Carte',
    spotify_search: 'Spotify Search',
    analytics: 'Analytics',
    competitor_watch: 'Veille Concurrentielle',
    ai_predictions: 'Prédictions',
    crm_extended: 'CRM Étendu',
    quotes: 'Devis',
    invoices: 'Factures',
    sources: 'Sources',
    source_health: 'Santé des Sources',
    banking: 'Connexions Bancaires',
    market_intelligence: 'Market Intelligence',
  };
  
  if (compact) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <Lock className="h-4 w-4 text-gray-400" />
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {featureLabels[feature] || feature}
        </span>
        <UpgradeBadge size="sm" />
      </div>
    );
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center p-8 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl border border-gray-200 dark:border-gray-700"
    >
      <div className="h-16 w-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
        <Lock className="h-8 w-8 text-white" />
      </div>
      
      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        {title || featureLabels[feature] || 'Fonctionnalité verrouillée'}
      </h3>
      
      <p className="text-gray-500 dark:text-gray-400 text-center mb-6 max-w-md">
        {upgradeMessage || 'Cette fonctionnalité n\'est pas disponible avec votre plan actuel.'}
      </p>
      
      <div className="flex gap-3">
        <Link href="/settings/subscription">
          <Button className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600">
            <Crown className="h-4 w-4 mr-2" />
            Voir les plans
          </Button>
        </Link>
      </div>
      
      {plan && (
        <p className="mt-4 text-xs text-gray-400">
          Plan actuel : <span className="font-medium capitalize">{plan}</span>
        </p>
      )}
    </motion.div>
  );
}

// ============================================================================
// UPGRADE BADGE
// ============================================================================

interface UpgradeBadgeProps {
  size?: 'sm' | 'md';
  text?: string;
}

/**
 * Badge to indicate upgrade required
 */
export function UpgradeBadge({ size = 'md', text = 'Upgrade' }: UpgradeBadgeProps) {
  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
  };
  
  return (
    <span className={`
      inline-flex items-center gap-1 rounded-full font-medium
      bg-gradient-to-r from-purple-500 to-pink-500 text-white
      ${sizeClasses[size]}
    `}>
      <Sparkles className={size === 'sm' ? 'h-2.5 w-2.5' : 'h-3 w-3'} />
      {text}
    </span>
  );
}

// ============================================================================
// NAV ITEM WITH LOCK
// ============================================================================

interface NavItemWithLockProps {
  label: string;
  path: string;
  icon: React.ReactNode;
  isLocked: boolean;
  isActive?: boolean;
  upgradeMessage?: string;
  onClick?: () => void;
}

/**
 * Navigation item that shows lock state
 */
export function NavItemWithLock({
  label,
  path,
  icon,
  isLocked,
  isActive = false,
  upgradeMessage,
  onClick,
}: NavItemWithLockProps) {
  if (isLocked) {
    return (
      <div 
        className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 cursor-not-allowed group relative"
        title={upgradeMessage}
      >
        <span className="opacity-50">{icon}</span>
        <span className="flex-1 text-sm opacity-50">{label}</span>
        <Lock className="h-3.5 w-3.5" />
        
        {/* Tooltip on hover */}
        <div className="absolute left-full ml-2 hidden group-hover:block z-50">
          <div className="bg-gray-900 text-white text-xs px-3 py-2 rounded-lg whitespace-nowrap shadow-lg">
            {upgradeMessage || 'Passez à un plan supérieur'}
            <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 border-4 border-transparent border-r-gray-900" />
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <Link
      href={path}
      onClick={onClick}
      className={`
        flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
        ${isActive 
          ? 'bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300' 
          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
        }
      `}
    >
      {icon}
      <span className="flex-1 text-sm">{label}</span>
    </Link>
  );
}

// ============================================================================
// LOCKED PAGE WRAPPER
// ============================================================================

interface LockedPageProps {
  feature: Feature;
  title: string;
  description?: string;
}

/**
 * Full page locked state for protected routes
 */
export function LockedPage({ feature, title, description }: LockedPageProps) {
  const upgradeMessage = useSubscriptionStore((s) => s.getUpgradeMessage(feature));
  
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md w-full text-center"
      >
        <div className="h-24 w-24 bg-gradient-to-br from-purple-500 to-pink-500 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-2xl">
          <Lock className="h-12 w-12 text-white" />
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
          {title}
        </h1>
        
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          {description || upgradeMessage || 'Cette page n\'est pas disponible avec votre plan actuel.'}
        </p>
        
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/settings/subscription">
            <Button size="lg" className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 w-full sm:w-auto">
              <Crown className="h-5 w-5 mr-2" />
              Découvrir les plans
            </Button>
          </Link>
          
          <Link href="/cockpit">
            <Button variant="outline" size="lg" className="w-full sm:w-auto">
              Retour au Cockpit
            </Button>
          </Link>
        </div>
        
        <div className="mt-8 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-xl">
          <div className="flex items-center gap-2 text-purple-700 dark:text-purple-300 mb-2">
            <Sparkles className="h-4 w-4" />
            <span className="font-medium text-sm">Inclus dans les plans supérieurs</span>
          </div>
          <p className="text-sm text-purple-600 dark:text-purple-400">
            {upgradeMessage}
          </p>
        </div>
      </motion.div>
    </div>
  );
}

// ============================================================================
// FEATURE CHECK HOOK FOR PAGES
// ============================================================================

/**
 * Hook for pages to check feature access and redirect if locked
 */
export function useFeatureGuard(feature: Feature): {
  hasAccess: boolean;
  isLoading: boolean;
  upgradeMessage: string | null;
} {
  const isLoading = useSubscriptionStore((s) => s.isLoading);
  const hasFeature = useFeature(feature);
  const upgradeMessage = useSubscriptionStore((s) => s.getUpgradeMessage(feature));
  
  return {
    hasAccess: hasFeature,
    isLoading,
    upgradeMessage,
  };
}
