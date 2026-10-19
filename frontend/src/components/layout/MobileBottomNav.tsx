'use client';
import Link from 'next/link';
import { useSubscriptionStore } from '@/store/subscriptionStore';
export function MobileBottomNav() {
  const navigation = useSubscriptionStore(s => s.navigation);
  const items = Object.values(navigation || {}).flat().filter(i => ['/today', '/projects', '/events', '/discovery'].includes(i.path));
  return <nav aria-label="Accès rapides" className="lg:hidden fixed bottom-0 inset-x-0 flex justify-around gap-2 border-t bg-white dark:bg-slate-900 p-4 z-30">
    {items.map(i => <Link className="text-xs" key={i.path} href={i.path}>{i.label}</Link>)}
  </nav>;
}
