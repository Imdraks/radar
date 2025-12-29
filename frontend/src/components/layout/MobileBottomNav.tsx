'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Target, 
  FileText, 
  Search, 
  User 
} from 'lucide-react';
import { cn } from '@/lib/utils';

const mobileNav = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Leads', href: '/leads', icon: Target },
  { name: 'Dossiers', href: '/dossiers', icon: FileText },
  { name: 'Découverte', href: '/discovery', icon: Search },
  { name: 'Profil', href: '/settings', icon: User },
];

export function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 safe-bottom">
      <div className="flex items-center justify-around h-16">
        {mobileNav.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== '/dashboard' && pathname.startsWith(item.href));
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex flex-col items-center justify-center flex-1 h-full px-2 transition-all duration-200 touch-active',
                isActive
                  ? 'text-primary'
                  : 'text-gray-500 dark:text-gray-400'
              )}
            >
              <item.icon 
                className={cn(
                  'h-5 w-5 mb-1 transition-transform duration-200',
                  isActive && 'scale-110'
                )} 
              />
              <span className={cn(
                'text-[10px] font-medium truncate',
                isActive && 'font-semibold'
              )}>
                {item.name}
              </span>
              {isActive && (
                <span className="absolute bottom-1 w-1 h-1 rounded-full bg-primary animate-scale-in" />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
