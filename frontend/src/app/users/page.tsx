'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Pencil, ShieldCheck, Users, UserRound, ArrowRightLeft, Power } from 'lucide-react';
import { AdminLayout, ProtectedRoute } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { PasswordFields, passwordChecks, usePasswordPolicy } from '@/components/auth/PasswordFields';
import { usersApi } from '@/lib/api';
import { clientError, clientDate } from '@/lib/platform-clients';
import { useAuthStore } from '@/store/auth';
import type { User, UserRole } from '@/lib/types';
import { toast } from 'sonner';

const roles: Record<UserRole, string> = { admin: 'Administrateur', bizdev: 'Commercial', pm: 'Chef de projet', viewer: 'Lecture seule' };
type Action = { kind: 'create' } | { kind: 'edit' | 'status'; user: User };

function UserAvatar({ user }: { user: User }) {
  const [failed, setFailed] = useState(false);
  return <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary/10 text-sm font-semibold text-primary">
    {user.avatar_url && !failed ? <img src={user.avatar_url} alt="" className="h-full w-full object-cover" onError={() => setFailed(true)} /> : (user.full_name || user.email).slice(0, 1).toLocaleUpperCase('fr-FR')}
  </div>;
}

function AccountMode({ user }: { user: User }) {
  return <div className="space-y-2"><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${user.is_collaborator ? 'bg-primary/10 text-primary' : 'bg-secondary text-secondary-foreground'}`}>
    {user.is_collaborator ? <ArrowRightLeft size={12} /> : <UserRound size={12} />}{user.is_collaborator ? 'Collaborateur' : 'Compte classique'}
  </span><p className="text-xs leading-5 text-muted-foreground">{user.is_collaborator ? 'Choix du workspace à la connexion' : user.is_superuser ? 'Accueil de l’administration' : 'Accès direct si un seul workspace actif'}</p></div>;
}
function AccountStatus({ user }: { user: User }) {
  return <span className={`inline-flex items-center gap-2 text-xs font-medium ${user.is_active ? 'text-emerald-700 dark:text-emerald-300' : 'text-muted-foreground'}`}><span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${user.is_active ? 'bg-emerald-500' : 'bg-muted-foreground'}`} />{user.is_active ? 'Actif' : 'Désactivé'}</span>;
}
function Identity({ user }: { user: User }) {
  const providers = [...new Set([...(user.linked_accounts || []).map(account => account.provider), user.auth_provider].filter((value): value is string => Boolean(value) && value !== 'credentials'))];
  return <div className="flex min-w-0 items-start gap-3"><UserAvatar user={user} /><div className="min-w-0 space-y-1"><p className="break-words font-semibold">{user.full_name || 'Nom non renseigné'}</p><p className="break-all text-xs text-muted-foreground">{user.email}</p><div className="flex flex-wrap gap-2">{user.is_superuser && <span className="inline-flex items-center gap-1 text-xs text-primary"><ShieldCheck size={13} />Super-admin</span>}{providers.map(provider => <span key={provider} className="text-xs text-muted-foreground">{provider === 'google' ? 'Google' : provider === 'apple' ? 'Apple' : provider}</span>)}</div></div></div>;
}

function UsersContent() {
  const current = useAuthStore(state => state.user);
  const cache = useQueryClient();
  const query = useQuery<User[]>({ queryKey: ['users'], queryFn: () => usersApi.getAll(), retry: false });
  const [search, setSearch] = useState('');
  const [mode, setMode] = useState('all');
  const [status, setStatus] = useState('all');
  const [action, setAction] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const filtered = useMemo(() => (query.data || []).filter(user => {
    const match = `${user.full_name || ''} ${user.email}`.toLocaleLowerCase('fr-FR').includes(search.trim().toLocaleLowerCase('fr-FR'));
    return match && (mode === 'all' || Boolean(user.is_collaborator) === (mode === 'collaborator')) && (status === 'all' || user.is_active === (status === 'active'));
  }), [query.data, search, mode, status]);
  const open = (value: Action) => { setError(''); setAction(value); };
  const save = async (data: Record<string, unknown>) => {
    if (!action || busy) return;
    setBusy(true); setError('');
    try {
      if (action.kind === 'create') await usersApi.create(data);
      else await usersApi.update(action.user.id, data);
      toast.success(action.kind === 'create' ? 'Compte créé' : 'Modifications enregistrées');
      if (action.kind !== 'create' && action.user.id === current?.id) await useAuthStore.getState().fetchUser();
      setAction(null);
      await cache.invalidateQueries({ queryKey: ['users'] });
    } catch (failure) { setError(clientError(failure)); }
    finally { setBusy(false); }
  };
  const actions = (user: User) => <div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" className="gap-2" onClick={() => open({ kind: 'edit', user })} aria-label={`Modifier ${user.full_name || user.email}`}><Pencil size={14} />Modifier</Button><Button variant="ghost" size="sm" className="gap-2" disabled={user.id === current?.id} onClick={() => open({ kind: 'status', user })} aria-label={`${user.is_active ? 'Désactiver' : 'Réactiver'} ${user.full_name || user.email}`}><Power size={14} />{user.is_active ? 'Désactiver' : 'Réactiver'}</Button></div>;
  return <div className="mx-auto max-w-[1440px] space-y-7 p-4 sm:p-8">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="radar-eyebrow">Administration Radar</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Utilisateurs</h1><p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">Gérez les comptes, leurs rôles et leur arrivée dans Radar. Les accès aux entreprises se gèrent depuis leurs fiches.</p></div><Button className="gap-2" onClick={() => open({ kind: 'create' })}><Plus size={16} />Nouvel utilisateur</Button></header>
    <section className="grid gap-4 rounded-2xl border bg-card p-4 lg:grid-cols-[minmax(0,1fr)_220px_180px]" aria-label="Rechercher et filtrer les utilisateurs">
      <div className="space-y-2"><Label htmlFor="user-search">Nom ou adresse e-mail</Label><div className="relative"><Search size={16} className="absolute left-3 top-3 text-muted-foreground" /><Input id="user-search" value={search} maxLength={255} onChange={event => setSearch(event.target.value)} placeholder="Rechercher un compte…" className="pl-9" /></div></div>
      <div className="space-y-2"><Label htmlFor="user-mode-filter">Mode du compte</Label><select id="user-mode-filter" className="h-10 w-full rounded-xl border bg-background px-3 text-sm" value={mode} onChange={event => setMode(event.target.value)}><option value="all">Tous les modes</option><option value="classic">Compte classique</option><option value="collaborator">Collaborateur</option></select></div>
      <div className="space-y-2"><Label htmlFor="user-status-filter">État du compte</Label><select id="user-status-filter" className="h-10 w-full rounded-xl border bg-background px-3 text-sm" value={status} onChange={event => setStatus(event.target.value)}><option value="all">Tous les états</option><option value="active">Actif</option><option value="inactive">Désactivé</option></select></div>
    </section>
    {query.isPending ? <p role="status" className="rounded-2xl border bg-card p-6 text-sm">Chargement des utilisateurs…</p> : query.isError ? <section role="alert" className="space-y-4 rounded-2xl border bg-card p-6"><p className="text-sm">Les comptes n’ont pas pu être chargés.</p><Button variant="outline" onClick={() => query.refetch()}>Réessayer</Button></section> : <>
      <div className="flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-sm text-muted-foreground">{filtered.length} compte{filtered.length === 1 ? '' : 's'} affiché{filtered.length === 1 ? '' : 's'} sur {query.data?.length || 0}</p><Link href="/admin/clients" className="text-sm text-primary hover:underline">Gérer les entreprises clientes</Link></div>
      {filtered.length === 0 ? <section className="rounded-2xl border bg-card p-10 text-center"><Users className="mx-auto mb-4 text-primary" /><h2 className="font-semibold">Aucun compte trouvé</h2><p className="mt-2 text-sm text-muted-foreground">Ajustez les filtres ou créez un utilisateur.</p></section> : <>
        <div className="hidden overflow-x-auto rounded-2xl border bg-card xl:block"><table className="w-full text-left text-sm"><thead className="border-b bg-secondary/40 text-xs text-muted-foreground"><tr>{['Compte', 'Rôle et accès', 'Arrivée dans Radar', 'Dernière connexion', 'Actions'].map(label => <th key={label} className="p-4 font-medium">{label}</th>)}</tr></thead><tbody>{filtered.map(user => <tr key={user.id} className="border-b last:border-0"><td className="max-w-xs p-4"><Identity user={user} /></td><td className="p-4"><p className="mb-2 text-xs">{roles[user.role] || user.role}</p><AccountStatus user={user} /></td><td className="p-4"><AccountMode user={user} /></td><td className="p-4 text-xs text-muted-foreground">{user.last_login_at ? clientDate(user.last_login_at) : 'Aucune connexion enregistrée'}</td><td className="p-4">{actions(user)}</td></tr>)}</tbody></table></div>
        <ul className="grid gap-4 xl:hidden">{filtered.map(user => <li key={user.id} className="space-y-5 rounded-2xl border bg-card p-5"><Identity user={user} /><div className="grid gap-4 sm:grid-cols-2"><div><p className="mb-2 text-xs text-muted-foreground">{roles[user.role] || user.role}</p><AccountStatus user={user} /></div><AccountMode user={user} /></div><p className="text-xs text-muted-foreground">Dernière connexion : {user.last_login_at ? clientDate(user.last_login_at) : 'aucune enregistrée'}</p><div className="border-t pt-4">{actions(user)}</div></li>)}</ul>
      </>}
    </>}
    <Dialog open={Boolean(action)} onOpenChange={visible => { if (!visible && !busy) setAction(null); }}><DialogContent className="max-h-[90dvh] w-[calc(100%-2rem)] overflow-y-auto sm:max-w-2xl"><DialogTitle>{action?.kind === 'create' ? 'Nouvel utilisateur' : action?.kind === 'status' ? `${action.user.is_active ? 'Désactiver' : 'Réactiver'} le compte` : 'Modifier l’utilisateur'}</DialogTitle><DialogDescription>{action && action.kind !== 'create' ? action.user.email : 'Créer un compte Radar. Pour inviter le responsable d’une entreprise par e-mail, utilisez sa fiche entreprise.'}</DialogDescription>
      {action?.kind === 'status' ? <form className="space-y-5" onSubmit={event => { event.preventDefault(); void save({ is_active: !action.user.is_active }); }}><p className="text-sm leading-7">{action.user.is_active ? 'La désactivation bloque ce compte sur tous ses workspaces et conserve ses données. Vous pourrez le réactiver ici.' : 'La réactivation rend le compte actif ; ses appartenances aux workspaces et les éventuelles suspensions d’entreprises restent inchangées.'}</p>{error && <p role="alert" className="text-sm text-destructive">{error}</p>}<div className="flex flex-wrap justify-end gap-3"><Button type="button" variant="outline" disabled={busy} onClick={() => setAction(null)}>Annuler</Button><Button disabled={busy} variant={action.user.is_active ? 'destructive' : 'default'}>{busy ? 'Enregistrement…' : action.user.is_active ? 'Confirmer la désactivation' : 'Confirmer la réactivation'}</Button></div></form> : action && <UserForm key={action.kind === 'edit' ? action.user.id : 'new'} user={action.kind === 'edit' ? action.user : null} ownAccount={action.kind === 'edit' && action.user.id === current?.id} busy={busy} error={error} onSubmit={save} onCancel={() => setAction(null)} />}
    </DialogContent></Dialog>
  </div>;
}

function UserForm({ user, ownAccount, busy, error, onSubmit, onCancel }: { user: User | null; ownAccount: boolean; busy: boolean; error: string; onSubmit: (data: Record<string, unknown>) => Promise<void>; onCancel: () => void }) {
  const [email, setEmail] = useState(user?.email || '');
  const [name, setName] = useState(user?.full_name || '');
  const [role, setRole] = useState<UserRole>(user?.role || 'viewer');
  const [active, setActive] = useState(user?.is_active ?? true);
  const [collaborator, setCollaborator] = useState(Boolean(user?.is_collaborator));
  const [resetPassword, setResetPassword] = useState(!user);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const policy = usePasswordPolicy();
  const validPassword = !resetPassword || (policy.data && password === confirm && passwordChecks(policy.data, password).every(check => check.valid));
  return <form className="space-y-6" autoComplete="off" onSubmit={event => { event.preventDefault(); if (busy || !validPassword) return; void onSubmit({ email: email.trim(), full_name: name.trim(), role, is_active: active, is_collaborator: collaborator, ...(resetPassword ? { password } : {}) }); }}>
    <fieldset disabled={busy} className="space-y-4"><legend className="mb-4 text-sm font-semibold">Identité du compte</legend><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="user-full-name">Nom complet</Label><Input id="user-full-name" value={name} maxLength={100} onChange={event => setName(event.target.value)} autoComplete="name" /></div><div className="space-y-2"><Label htmlFor="user-email">Adresse e-mail</Label><Input id="user-email" type="email" value={email} required maxLength={255} onChange={event => setEmail(event.target.value)} autoComplete="off" /></div></div></fieldset>
    <fieldset disabled={busy} className="space-y-4 rounded-xl border p-4"><legend className="px-1 text-sm font-semibold">Accès et arrivée dans Radar</legend><div className="space-y-2"><Label htmlFor="user-role">Rôle</Label><select id="user-role" className="h-10 w-full rounded-xl border bg-background px-3 text-sm" value={role} onChange={event => setRole(event.target.value as UserRole)}>{Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><p className="text-xs leading-6 text-muted-foreground">Le rôle ne confère pas les droits super-admin. Les appartenances et rôles dans les entreprises se gèrent sur leurs fiches.</p></div><div className="flex items-start justify-between gap-4 border-t pt-4"><div><Label htmlFor="user-collaborator">Compte collaborateur</Label><p className="mt-2 text-xs leading-6 text-muted-foreground">Activé : choix du workspace après chaque connexion, même avec un seul espace. Désactivé : ouverture directe si un seul workspace est lié et actif. Aucun accès supplémentaire n’est accordé.</p></div><Switch id="user-collaborator" checked={collaborator} onCheckedChange={setCollaborator} /></div><div className="flex items-start justify-between gap-4 border-t pt-4"><div><Label htmlFor="user-active">Compte actif</Label><p className="mt-2 text-xs leading-6 text-muted-foreground">Un compte désactivé ne peut plus accéder à Radar. Ses données sont conservées.</p></div><Switch id="user-active" checked={active} disabled={ownAccount} onCheckedChange={setActive} /></div></fieldset>
    <fieldset disabled={busy} className="space-y-4"><legend className="mb-3 text-sm font-semibold">Sécurité</legend>{ownAccount ? <p className="text-sm leading-7 text-muted-foreground">Pour changer votre propre mot de passe avec les vérifications requises, ouvrez <Link href="/account/security" className="text-primary underline">la sécurité de votre compte</Link>.</p> : <>{user && <div className="flex items-start justify-between gap-4"><div><Label htmlFor="user-reset-password">Réinitialiser le mot de passe Radar</Label><p className="mt-2 text-xs leading-6 text-muted-foreground">Laissez désactivé pour conserver le mot de passe. La modification des coordonnées ou du mode collaborateur n’envoie aucun nouveau mot de passe.</p></div><Switch id="user-reset-password" checked={resetPassword} onCheckedChange={value => { setResetPassword(value); setPassword(''); setConfirm(''); }} /></div>}{resetPassword && (policy.isError ? <p role="alert" className="text-sm text-destructive">Impossible de charger les critères de sécurité. Réessayez avant de modifier le mot de passe.</p> : policy.data ? <PasswordFields prefix="admin-user" password={password} confirm={confirm} onPassword={setPassword} onConfirm={setConfirm} disabled={busy} policy={policy.data} /> : <p role="status" className="text-sm">Chargement des critères de sécurité…</p>)}</>}</fieldset>
    {error && <p role="alert" className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
    <footer className="flex flex-wrap justify-end gap-3 border-t pt-4"><Button type="button" variant="outline" disabled={busy} onClick={onCancel}>Annuler</Button><Button disabled={busy || !validPassword}>{busy ? 'Enregistrement…' : user ? 'Appliquer les modifications' : 'Créer le compte'}</Button></footer>
  </form>;
}

export default function UsersPage() { return <ProtectedRoute><AdminLayout><UsersContent /></AdminLayout></ProtectedRoute>; }
