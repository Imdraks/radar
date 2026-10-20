import { Home, Inbox, FolderOpen, Clapperboard, Calendar, Image, CalendarDays, Search, GitCompare, Users, TrendingUp, Receipt, FileCheck, CreditCard, Settings, type LucideIcon } from 'lucide-react';
const icons: Record<string, LucideIcon> = { Home, Inbox, FolderOpen, Clapperboard, Calendar, Image, CalendarDays, Search, GitCompare, Users, TrendingUp, Receipt, FileCheck, CreditCard, Settings };
export function NavigationIcon({ name, className = 'h-[18px] w-[18px]' }: { name: string; className?: string }) {
  const Icon = icons[name] || FolderOpen;
  return <Icon className={className} aria-hidden="true" strokeWidth={1.7} />;
}
