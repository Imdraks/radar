'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, LogOut, Settings } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useAuthStore } from '@/store/auth';
import type { User } from '@/lib/types';
import type { Plan } from '@/store/subscriptionStore';
import './public-account.css';

type Account = { user: User; plan: Plan | null };

/** Verify an optional session without redirecting visitors or trusting cached rights. */
export function usePublicAccount() {
  const pathname = usePathname();
  const identity = useAuthStore(state => state.user?.id);
  const authenticated = useAuthStore(state => state.isAuthenticated);
  const avatar = useAuthStore(state => state.user?.avatar_url);
  const logout = useAuthStore(state => state.logout);
  const [account, setAccount] = useState<Account | null>(null);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    let active: AbortController | undefined;
    const refresh = async () => {
      active?.abort();
      const controller = new AbortController();
      active = controller;
      let token = localStorage.getItem('access_token');
      if (!token) { setAccount(null); setChecking(false); return; }
      setChecking(true);
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const request = (path: string) => fetch(path, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: 'no-store' });
        let response = await request('/api/v1/auth/me');
        if (response.status === 401) {
          const credential = localStorage.getItem('refresh_token');
          if (credential) {
            const renewed = await fetch('/api/v1/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: credential }), signal: controller.signal, cache: 'no-store' });
            if (renewed.ok && localStorage.getItem('refresh_token') === credential) {
              const tokens = await renewed.json();
              if (typeof tokens.access_token === 'string' && !controller.signal.aborted) {
                token = tokens.access_token;
                localStorage.setItem('access_token', token!);
                if (tokens.refresh_token) localStorage.setItem('refresh_token', tokens.refresh_token);
                response = await request('/api/v1/auth/me');
              }
            }
          }
        }
        if (!response.ok) throw new Error('Session unavailable');
        const user = await response.json() as User;
        if (!Number.isSafeInteger(user.id) || !user.is_active) throw new Error('Invalid account');
        if (controller.signal.aborted || localStorage.getItem('access_token') !== token) return;
        setAccount({ user, plan: null });
        setChecking(false);
        let plan: Plan | null = null;
        const workspace = Number(localStorage.getItem('current_workspace_id'));
        const selected = Number.isSafeInteger(workspace) && workspace > 0 ? workspace : null;
        // This endpoint enforces workspace membership and expiration in the backend.
        try {
          const subscriptionResponse = await request(`/api/v1/subscription/current${selected ? `?workspace_id=${selected}` : ''}`);
          if (subscriptionResponse.ok) {
            const subscription = await subscriptionResponse.json();
            const expired = subscription.plan_expires_at && new Date(subscription.plan_expires_at.endsWith('Z') || /[+-]\d\d:\d\d$/.test(subscription.plan_expires_at) ? subscription.plan_expires_at : subscription.plan_expires_at + 'Z').getTime() <= Date.now();
            if ((!selected || subscription.workspace_id === selected) && ['core', 'premium', 'business'].includes(subscription.plan)) plan = expired ? 'core' : subscription.plan;
          }
        } catch { /* Keep the verified identity with an unknown tier if billing is unavailable. */ }
        if (!controller.signal.aborted && localStorage.getItem('access_token') === token) setAccount({ user, plan });
      } catch {
        if (!controller.signal.aborted) setAccount(null);
      } finally {
        clearTimeout(timeout);
        if (active === controller) setChecking(false);
      }
    };
    const changed = () => { setAccount(null); void refresh(); };
    void refresh();
    window.addEventListener('storage', changed);
    window.addEventListener('workspace-changed', changed);
    window.addEventListener('focus', changed);
    return () => { active?.abort(); window.removeEventListener('storage', changed); window.removeEventListener('workspace-changed', changed); window.removeEventListener('focus', changed); };
  }, [pathname, identity, authenticated, avatar]);
  return { account, checking, signOut: () => { setAccount(null); logout(); } };
}

export function AccountPhoto({ user, className = '' }: { user: Pick<User, 'avatar_url' | 'full_name' | 'email'>; className?: string }) {
  const initials = (user.full_name?.trim() || user.email?.trim() || 'Radar').split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  const source = user.avatar_url;
  const safe = source && (source.startsWith('https://') || /^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(source));
  return <Avatar className={`bg-white ${className}`}><AvatarImage src={safe ? source : undefined} alt="" referrerPolicy="no-referrer" className="object-cover" /><AvatarFallback className="bg-primary/10 text-sm font-semibold text-primary">{initials}</AvatarFallback></Avatar>;
}

export function PublicAccountMenu({ account, onLogout }: { account: Account; onLogout: () => void }) {
  const plan = account.plan ? `Radar ${account.plan[0].toUpperCase()}${account.plan.slice(1)}` : 'Consulter mon abonnement';
  return <DropdownMenu><DropdownMenuTrigger asChild><button type="button" aria-label={`Ouvrir le menu du compte ${account.user.full_name || ''}`.trim()} title={plan} className="radar-account-trigger rounded-full outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-4">
    <span className="radar-account-ring" data-tier={account.plan || 'unknown'}><AccountPhoto user={account.user} className="h-[44px] w-[44px] border-2 border-white" /></span>
  </button></DropdownMenuTrigger><DropdownMenuContent align="end" sideOffset={12} className="radar-public w-64 max-w-[calc(100vw-2rem)] rounded-2xl bg-white p-2">
    <DropdownMenuLabel className="min-w-0 px-3 py-2"><span className="block truncate text-sm font-semibold">{account.user.full_name || 'Mon compte'}</span><span className="mt-1 block text-xs font-normal text-primary">{plan}</span></DropdownMenuLabel><DropdownMenuSeparator />
    <DropdownMenuItem asChild><Link href="/today" className="gap-2 rounded-lg p-3"><ArrowUpRight size={16} />Ouvrir mon espace</Link></DropdownMenuItem>
    <DropdownMenuItem asChild><Link href="/settings" className="gap-2 rounded-lg p-3"><Settings size={16} />Paramètres du compte</Link></DropdownMenuItem>
    <DropdownMenuItem onSelect={onLogout} className="gap-2 rounded-lg p-3"><LogOut size={16} />Se déconnecter</DropdownMenuItem>
  </DropdownMenuContent></DropdownMenu>;
}
