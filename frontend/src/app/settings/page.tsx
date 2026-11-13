'use client';
import Link from 'next/link';
import { Archive, ArrowUpRight, Bell, User, Lock, Palette } from 'lucide-react';
import { AppLayout, ProtectedRoute } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { NotificationSettings } from '@/components/settings/NotificationSettings';
import { TwoFactorSettings } from '@/components/settings/TwoFactorSettings';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { useAuthStore } from '@/store/auth';
import { useSubscriptionStore } from '@/store/subscriptionStore';

function SettingsContent() {
  const user = useAuthStore(state => state.user);
  const showWorkspaceSettings = useSubscriptionStore(state => Object.values(state.navigation || {}).flat().some(item => item.path === '/workspace/settings'));
  return <div className="space-y-7"><div><p className="radar-eyebrow mb-2">Administration</p><h1 className="text-3xl font-semibold tracking-tight">Paramètres</h1><p className="mt-2 text-sm text-muted-foreground">Votre compte, vos notifications et vos préférences.</p></div>
    <Tabs defaultValue="profile" className="space-y-5"><TabsList className="flex-wrap h-auto gap-1"><TabsTrigger value="profile"><User size={15} className="mr-2" />Compte</TabsTrigger><TabsTrigger value="notifications"><Bell size={15} className="mr-2" />Notifications</TabsTrigger><TabsTrigger value="security"><Lock size={15} className="mr-2" />Sécurité</TabsTrigger><TabsTrigger value="appearance"><Palette size={15} className="mr-2" />Apparence</TabsTrigger></TabsList>
      <TabsContent value="profile"><Card><CardHeader><CardTitle className="text-lg">Informations du compte</CardTitle><CardDescription>Les informations associées à votre connexion.</CardDescription></CardHeader><CardContent><dl className="grid gap-6 sm:grid-cols-2"><div><dt className="text-xs text-muted-foreground">Nom</dt><dd className="mt-1 font-medium">{user?.full_name || 'Non renseigné'}</dd></div><div><dt className="text-xs text-muted-foreground">Email</dt><dd className="mt-1 break-all font-medium">{user?.email || 'Non renseigné'}</dd></div></dl></CardContent></Card></TabsContent>
      <TabsContent value="notifications"><NotificationSettings /></TabsContent>
      <TabsContent value="security"><TwoFactorSettings /></TabsContent>
      <TabsContent value="appearance"><Card><CardHeader><CardTitle className="text-lg">Apparence</CardTitle><CardDescription>Choisissez le thème de votre espace de travail.</CardDescription></CardHeader><CardContent className="flex items-center justify-between"><p className="text-sm">Thème de l’interface</p><ThemeToggle /></CardContent></Card></TabsContent>
    </Tabs>
    {showWorkspaceSettings && <Link href="/workspace/settings" className="flex items-center justify-between gap-4 rounded-2xl border bg-card p-5"><div><h2 className="text-sm font-semibold">Équipe et intégrations</h2><p className="mt-1 text-xs text-muted-foreground">Retrouvez la configuration de votre espace de travail.</p></div><ArrowUpRight size={17} /></Link>}
    <Link href="/settings/privacy" className="flex items-center justify-between gap-4 rounded-2xl border bg-card p-5"><div><h2 className="text-sm font-semibold">Données et droits</h2><p className="mt-1 text-xs text-muted-foreground">Export du compte, demandes de droits, résiliation et réversibilité.</p></div><ArrowUpRight size={17} /></Link>
    <Link href="/settings/tools" className="flex items-start gap-4 rounded-2xl border bg-card p-5"><Archive size={20} className="shrink-0 text-muted-foreground" /><div className="flex-1"><h2 className="text-sm font-semibold">Historique et outils secondaires</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Accéder aux anciennes analyses, profils de recherche et documents conservés.</p></div><ArrowUpRight size={17} /></Link>
  </div>;
}
export default function SettingsPage() { return <ProtectedRoute><AppLayout><SettingsContent /></AppLayout></ProtectedRoute>; }
