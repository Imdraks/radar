/** UI projection of backend rights. Backend authorization remains authoritative. */
import { create } from 'zustand';
export type Plan = 'core' | 'premium' | 'business';
export type Pack = 'core' | 'clients' | 'leads' | 'talents' | 'intelligence';
export type Addon = 'radar_business'; // Legacy read compatibility only.
export type Feature = 'cockpit' | 'pipeline' | 'projects' | 'production' | 'assets' | 'calendar'
  | 'clients' | 'dossiers' | 'daily_picks' | 'leads' | 'kanban_leads' | 'scoring'
  | 'artists' | 'profiles' | 'discovery' | 'comparison' | 'map' | 'spotify_search' | 'events'
  | 'analytics' | 'competitor_watch' | 'ai_predictions' | 'market_intelligence'
  | 'crm_extended' | 'quotes' | 'invoices' | 'banking' | 'sources' | 'source_health';
export interface NavItem { label: string; path: string; icon: string; available: boolean; locked: boolean; admin_only: boolean; upgrade_message?: string; }
export interface NavigationSections { [section: string]: NavItem[]; }
export interface WorkspaceSubscription {
  workspace_id: number; workspace_name: string; plan: Plan; plan_display_name: string;
  enabled_packs: Pack[]; addons: Addon[]; max_seats: number; current_seats: number;
  available_features: Feature[]; plan_expires_at?: string;
}
export interface PlanInfo {
  name: Plan; display_name: string; description: string; price_monthly: number | null;
  included_packs: string[]; included_addons: string[]; max_seats: number;
  features_bullets: string[]; is_current: boolean; is_recommended: boolean;
}
export interface AddonInfo { name: string; display_name: string; description: string; price_monthly: number | null; features: string[]; is_active: boolean; included_in_plan: boolean; }
export const ADMIN_ONLY_FEATURES: Feature[] = ['sources', 'source_health'];
export const FEATURE_ROUTES: Record<string, Feature> = {
  '/today': 'cockpit', '/cockpit': 'cockpit', '/dashboard': 'cockpit', '/inbox': 'cockpit',
  '/projects': 'projects', '/production': 'production', '/assets': 'assets',
  '/agency-calendar': 'calendar', '/calendar': 'calendar', '/events': 'events',
  '/clients': 'clients', '/pipeline': 'pipeline', '/leads': 'leads', '/opportunities': 'leads',
  '/dossiers': 'dossiers', '/artist': 'artists', '/artists': 'artists', '/discovery': 'discovery',
  '/spotify-search': 'spotify_search', '/comparison': 'comparison', '/profiles': 'profiles',
  '/analytics': 'analytics', '/map': 'events', '/shortlist': 'daily_picks', '/scoring': 'scoring',
  '/devis': 'quotes', '/quotes': 'quotes', '/factures': 'invoices', '/invoices': 'invoices',
  '/transactions': 'banking', '/competitive': 'competitor_watch', '/predictions': 'ai_predictions',
  '/sources': 'sources', '/source-health': 'source_health',
};
export function routeFeature(path: string): Feature | undefined {
  return FEATURE_ROUTES[Object.keys(FEATURE_ROUTES).sort((a,b) => b.length-a.length).find(p => path === p || path.startsWith(p + '/')) || ''];
}
interface SubscriptionState {
  subscription: WorkspaceSubscription | null; navigation: NavigationSections | null;
  isLoading: boolean; error: string | null; isAdmin: boolean;
  fetchSubscription: (workspaceId?: number) => Promise<void>;
  fetchNavigation: (workspaceId?: number) => Promise<void>;
  setAdmin: (value: boolean) => void; hasFeature: (feature: Feature) => boolean;
  canAccessRoute: (path: string) => boolean; getUpgradeMessage: (feature: Feature) => string | null;
  changePlan: (plan: Plan) => Promise<boolean>; toggleAddon: (addon: Addon, enable: boolean) => Promise<boolean>;
  togglePack: (pack: Pack, enable: boolean) => Promise<boolean>; reset: () => void;
}
let fetchGeneration = 0;
const initialState = { subscription: null, navigation: null, isLoading: false, error: null, isAdmin: false };
export function selectedWorkspace(): number | undefined {
  const id = Number(localStorage.getItem('current_workspace_id'));
  return Number.isSafeInteger(id) && id > 0 ? id : undefined;
}
export async function subscriptionFetch(path: string, workspaceId?: number, init?: RequestInit) {
  const id = workspaceId ?? selectedWorkspace();
  const response = await fetch(`/api/v1/subscription/${path}${id ? `?workspace_id=${id}` : ''}`, {
    ...init, headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}`, 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) throw new Error('Impossible de charger ou de modifier cet abonnement');
  return response.json();
}
export const useSubscriptionStore = create<SubscriptionState>((set, get) => ({
  ...initialState,
  fetchSubscription: async (workspaceId) => {
    const generation = ++fetchGeneration;
    set({ subscription: null, navigation: null, error: null, isLoading: true });
    if (!localStorage.getItem('access_token')) { set({ isLoading: false }); return; }
    try {
      const subscription = await subscriptionFetch('current', workspaceId);
      const navigation = await subscriptionFetch('navigation', subscription.workspace_id);
      if (generation === fetchGeneration) set({ subscription, navigation: navigation.sections, isLoading: false });
    } catch (error) {
      if (generation === fetchGeneration) set({ subscription: null, navigation: null, isLoading: false, error: String(error) });
    }
  },
  fetchNavigation: async (workspaceId) => { await get().fetchSubscription(workspaceId); },
  setAdmin: (isAdmin) => set({ isAdmin }),
  hasFeature: (feature) => ADMIN_ONLY_FEATURES.includes(feature) ? get().isAdmin : !!get().subscription?.available_features.includes(feature),
  canAccessRoute: (path) => { const feature = routeFeature(path); return !feature || get().hasFeature(feature); },
  getUpgradeMessage: () => 'Consultez votre abonnement ou contactez votre administrateur.',
  changePlan: async (plan) => {
    try { await subscriptionFetch('change-plan', get().subscription?.workspace_id, { method: 'POST', body: JSON.stringify({ plan }) }); return true; }
    catch (error) { set({ error: String(error) }); return false; }
  },
  toggleAddon: async () => false,
  togglePack: async () => false,
  reset: () => { ++fetchGeneration; set(initialState); },
}));
export const useFeature = (feature: Feature) => useSubscriptionStore(state => state.hasFeature(feature));
export function useRouteAccess(path: string) {
  const canAccess = useSubscriptionStore(state => state.canAccessRoute(path));
  return { canAccess, isLocked: !canAccess, upgradeMessage: canAccess ? null : 'Consultez votre abonnement.' };
}
export const usePlan = () => useSubscriptionStore(state => state.subscription?.plan || null);
export const useIsAdmin = () => useSubscriptionStore(state => state.isAdmin);
