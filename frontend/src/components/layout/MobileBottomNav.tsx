'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { NavigationIcon } from './navigation-icons';
export function MobileBottomNav() {
  const pathname = usePathname();
  const navigation = useSubscriptionStore(s => s.navigation);
  const items = Object.values(navigation || {}).flat().filter(i => ['/today', '/projects', '/events', '/discovery'].includes(i.path));
  return <nav aria-label="Accès rapides" className="safe-bottom lg:hidden fixed bottom-0 inset-x-0 z-30 flex justify-around border-t bg-card/95 px-2 pt-2 backdrop-blur-md">
    {items.map(i => {
      const active = pathname === i.path || pathname.startsWith(i.path + '/');
      return <Link aria-current={active ? 'page' : undefined} className={`flex min-h-[58px] min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-lg px-1 pb-2 text-[10px] font-medium hover:no-underline ${active ? 'text-primary' : 'text-muted-foreground'}`} key={i.path} href={i.path}><NavigationIcon name={i.icon} className="h-5 w-5" /><span className="truncate max-w-full">{i.label}</span></Link>;
    })}
  </nav>;
}
