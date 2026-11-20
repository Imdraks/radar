'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { clientRequest, clientError, type ClientDetail } from '@/lib/platform-clients';
import { useSubscriptionStore } from '@/store/subscriptionStore';
import { toast } from 'sonner';

export function DeleteClientWorkspace({ client }: { client: ClientDetail }) {
  const router = useRouter();
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!client.is_suspended) return null;
  return <section className="space-y-4 rounded-2xl border border-destructive/30 bg-card p-5 sm:p-6"><div><h2 className="font-semibold">Supprimer cet espace suspendu</h2><p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">Retirez cet espace des listes et du choix des workspaces. Les comptes utilisateurs et les données sont conservés ; les documents et intégrations externes ne sont pas effacés.</p></div><Button variant="destructive" onClick={() => { setName(''); setError(''); setOpen(true); }}>Supprimer l’espace</Button>
    <Dialog open={open} onOpenChange={value => { if (!busy) setOpen(value); }}><DialogContent className="max-h-[90dvh] w-[calc(100%-2rem)] overflow-y-auto sm:max-w-lg"><DialogTitle>Confirmer la suppression de l’espace</DialogTitle><DialogDescription>L’espace doit rester suspendu pour permettre cette action. Il sera retiré du produit et ne pourra pas être réactivé depuis cette fiche. Ses données sont conservées.</DialogDescription><form className="space-y-5" onSubmit={async event => {
      event.preventDefault(); if (busy || name.trim() !== client.name.trim()) return;
      setBusy(true); setError('');
      const form = new FormData(event.currentTarget);
      try {
        await clientRequest(`/${client.id}`, 'DELETE', { confirm_name: name.trim(), reason: form.get('reason'), acknowledged: form.get('acknowledged') === 'on' });
        if (localStorage.getItem('current_workspace_id') === String(client.id)) {
          localStorage.removeItem('current_workspace_id');
          useSubscriptionStore.getState().reset();
          window.dispatchEvent(new Event('workspace-changed'));
        }
        cache.removeQueries({ queryKey: ['platform-client', String(client.id)] });
        await cache.invalidateQueries({ queryKey: ['platform-clients'] });
        await cache.invalidateQueries({ queryKey: ['platform-orders'] });
        await cache.invalidateQueries({ queryKey: ['account-workspaces'] });
        toast.success('Espace retiré. Les données sont conservées.');
        router.replace('/admin/clients');
      } catch (failure) { setError(clientError(failure)); } finally { setBusy(false); }
    }}><p className="break-words rounded-xl bg-secondary p-3 text-sm font-medium">{client.name}</p><div className="space-y-2"><Label htmlFor="delete-workspace-name">Retapez le nom de l’espace</Label><Input id="delete-workspace-name" value={name} required maxLength={255} autoComplete="off" disabled={busy} onChange={event => setName(event.target.value)} /></div><div className="space-y-2"><Label htmlFor="delete-workspace-reason">Motif de suppression</Label><textarea id="delete-workspace-reason" name="reason" required minLength={5} maxLength={1000} disabled={busy} className="min-h-24 w-full rounded-xl border bg-background p-3 text-sm" /></div><label className="flex items-start gap-3 text-sm leading-6"><input name="acknowledged" type="checkbox" required disabled={busy} className="mt-1 accent-violet-600" /><span>Je confirme le retrait de cet espace suspendu, avec conservation de ses comptes et de ses données.</span></label>{error && <p role="alert" className="text-sm text-destructive">{error}</p>}<div className="flex flex-wrap justify-end gap-3"><Button type="button" variant="outline" disabled={busy} onClick={() => setOpen(false)}>Annuler</Button><Button variant="destructive" disabled={busy || name.trim() !== client.name.trim()}>{busy ? 'Suppression…' : 'Confirmer la suppression'}</Button></div></form></DialogContent></Dialog>
  </section>;
}
