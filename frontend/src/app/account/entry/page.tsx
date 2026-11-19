'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { Button } from '@/components/ui/button';

function Entry() {
  const router = useRouter();
  const user = useAuthStore(state => state.user);
  const query = useQuery<{ id: number; name: string; is_suspended: boolean }[]>({
    queryKey: ['login-workspaces', user?.id],
    queryFn: async () => (await api.get('/auth/account/workspaces')).data,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (user?.is_collaborator) { router.replace('/account/workspaces'); return; }
    if (!query.data) return;
    const workspaces = query.data;
    if (workspaces.length === 1 && !workspaces[0].is_suspended) {
      localStorage.setItem('current_workspace_id', String(workspaces[0].id));
      useSubscriptionStore.getState().reset();
      window.dispatchEvent(new Event('workspace-changed'));
      router.replace('/today');
    } else router.replace('/account/workspaces');
  }, [query.data, user?.is_collaborator, router]);
  return <main className="radar-app flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
    {query.isError ? <section role="alert" className="max-w-md space-y-4 rounded-2xl border bg-card p-6"><h1 className="text-xl font-semibold">Vos espaces sont indisponibles</h1><p className="text-sm text-muted-foreground">La connexion est établie, mais vos accès n’ont pas pu être vérifiés.</p><Button onClick={() => query.refetch()}>Réessayer</Button></section> : <p role="status">Ouverture de votre espace de travail…</p>}
  </main>;
}
export default function AccountEntryPage() { return <ProtectedRoute><Entry /></ProtectedRoute>; }
