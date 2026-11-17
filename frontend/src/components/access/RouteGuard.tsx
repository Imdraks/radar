'use client';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import ModuleNotActivated from './ModuleNotActivated';
export function RouteGuard({ children, pathname }: { children: React.ReactNode; pathname: string }) {
  const allowed = useSubscriptionStore(s => s.canAccessRoute(pathname));
  return allowed ? <>{children}</> : <ModuleNotActivated moduleName="cette fonctionnalité" />;
}
export function useModuleAccess(path: string) {
  const isAllowed = useSubscriptionStore(s => s.canAccessRoute(path));
  return { isAllowed, moduleName: 'cette fonctionnalité' };
}
export default RouteGuard;
