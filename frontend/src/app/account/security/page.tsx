'use client';
import Link from 'next/link';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { useAuthStore } from '@/store/auth';
import { PasswordSettings } from '@/components/settings/PasswordSettings';
import { TwoFactorSettings } from '@/components/settings/TwoFactorSettings';
import { PasskeySettings } from '@/components/settings/PasskeySettings';
import { SessionSettings } from '@/components/settings/SessionSettings';
import { RadarLogo } from '@/components/brand/RadarBrand';
function Content() {
  const user = useAuthStore(state => state.user);
  return <main className="radar-app min-h-screen bg-background px-5 py-8 text-foreground"><div className="mx-auto max-w-3xl space-y-7"><RadarLogo /><Link href={user?.is_superuser ? '/admin/clients' : '/account/workspaces'} className="block text-sm text-primary underline">Retour</Link><h1 className="text-3xl font-semibold">Sécurité de mon compte</h1><PasswordSettings /><TwoFactorSettings /><PasskeySettings /><SessionSettings /></div></main>;
}
export default function AccountSecurityPage() { return <ProtectedRoute><Content /></ProtectedRoute>; }
