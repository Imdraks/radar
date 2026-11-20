'use client';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { Button } from '@/components/ui/button';

function Workspaces() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const query = useQuery<{ id: number; name: string; is_suspended: boolean }[]>({ queryKey: ['account-workspaces', user?.id], queryFn: async () => (await api.get('/auth/account/workspaces')).data });
  return <main className="radar-app min-h-screen bg-background px-5 py-10 text-foreground"><div className="mx-auto max-w-2xl space-y-7"><header className="flex items-center justify-between"><RadarLogo /><Button variant="ghost" onClick={logout}>Déconnexion</Button></header><div><h1 className="text-3xl font-semibold tracking-tight">Vos espaces de travail</h1><p className="mt-3 text-sm leading-7 text-muted-foreground">Choisissez l’entreprise dans laquelle vous souhaitez travailler.</p></div>
    {query.isPending ? <p role="status">Chargement…</p> : query.isError ? <div role="alert"><p>Vos espaces n’ont pas pu être chargés.</p><Button variant="outline" onClick={() => query.refetch()}>Réessayer</Button></div> : query.data?.length ? <ul className="space-y-4">{query.data.map(ws => <li key={ws.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card p-5"><div><h2 className="break-words font-semibold">{ws.name}</h2>{ws.is_suspended && <p className="mt-2 text-sm text-muted-foreground">Espace suspendu. Contactez votre interlocuteur Radar pour sa réactivation.</p>}</div><Button disabled={ws.is_suspended} onClick={() => { localStorage.setItem('current_workspace_id', String(ws.id)); useSubscriptionStore.getState().reset(); window.dispatchEvent(new Event('workspace-changed')); router.replace('/today'); }}>Ouvrir l’espace</Button></li>)}</ul> : <p>Aucun espace disponible. Contactez votre interlocuteur Radar.</p>}
  </div></main>;
}
export default function AccountWorkspacesPage() { return <ProtectedRoute><Workspaces /></ProtectedRoute>; }
