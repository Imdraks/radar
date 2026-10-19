'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft,
  Plus, 
  Loader2, 
  Mail,
  Trash2,
  Check,
  Clock,
  Users,
  Shield,
  Eye,
  User,
  Package,
  Zap,
  Building2,
  Rocket,
  Crown,
  Save,
  RefreshCw,
  Lock,
  KeyRound,
  Copy,
  CheckCircle,
  MoreVertical,
  UserPlus,
  AlertTriangle,
} from 'lucide-react';
import Link from 'next/link';
import { AdminLayout, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useSubscriptionStore } from "@/store/subscriptionStore";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { toast } from 'sonner';

interface WorkspaceInvite {
  id: number;
  workspace_id: number;
  email: string;
  role: 'admin' | 'member' | 'viewer';
  claimed: boolean;
  claimed_at?: string;
  created_at: string;
}

interface WorkspaceMember {
  id: number;
  user_id: number;
  role: 'admin' | 'member' | 'viewer';
  user_name: string | null;
  user_email: string | null;
  user_avatar: string | null;
  invited_at: string | null;
  accepted_at: string | null;
}

interface WorkspaceDetailFull {
  id: number;
  name: string;
  owner_user_id: number;
  owner_name: string | null;
  drive_root_folder_id: string | null;
  drive_url: string | null;
  members_count: number;
  members: WorkspaceMember[];
  created_at: string;
  updated_at: string;
}

interface Workspace {
  id: number;
  name: string;
  owner_user_id: number;
  owner_name?: string;
  drive_url?: string;
  members_count: number;
  created_at: string;
}

interface WorkspaceSubscription {
  workspace_id: number;
  workspace_name: string;
  plan: string;
  plan_display_name: string;
  enabled_packs: string[];
  addons: string[];
  max_seats: number;
  current_seats: number;
  available_features: string[];
}

const roleLabels: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  admin: { label: 'Admin', icon: <Shield className="h-3 w-3" />, color: 'bg-red-100 text-red-700' },
  member: { label: 'Membre', icon: <User className="h-3 w-3" />, color: 'bg-blue-100 text-blue-700' },
  viewer: { label: 'Viewer', icon: <Eye className="h-3 w-3" />, color: 'bg-gray-100 text-gray-700' },
};

export default function WorkspaceDetailPage() {
  return (
    <ProtectedRoute requiredRoles={['admin']}>
      <AdminLayout>
        <WorkspaceDetailContent />
      </AdminLayout>
    </ProtectedRoute>
  );
}

function WorkspaceDetailContent() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const { fetchSubscription: refreshGlobalSubscription } = useSubscriptionStore();
  
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [subscription, setSubscription] = useState<WorkspaceSubscription | null>(null);
  // Local edit state for subscription changes
  const [editPlan, setEditPlan] = useState<string | null>(null);
  const [editAddons, setEditAddons] = useState<string[] | null>(null);
  const [invites, setInvites] = useState<WorkspaceInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [savingSubscription, setSavingSubscription] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'member' | 'viewer'>('member');
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null); // null = loading

  // Members management
  const [wsDetail, setWsDetail] = useState<WorkspaceDetailFull | null>(null);
  const [showAddMemberDialog, setShowAddMemberDialog] = useState(false);
  const [memberEmail, setMemberEmail] = useState('');
  const [memberRole, setMemberRole] = useState<'admin' | 'member' | 'viewer'>('member');
  const [memberAuthProvider, setMemberAuthProvider] = useState<'credentials' | 'google'>('credentials');
  const [memberPassword, setMemberPassword] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [memberError, setMemberError] = useState<string | null>(null);

  // Reset password
  const [showResetPwDialog, setShowResetPwDialog] = useState(false);
  const [resetTarget, setResetTarget] = useState<WorkspaceMember | null>(null);
  const [resettingPw, setResettingPw] = useState(false);
  const [generatedPw, setGeneratedPw] = useState<string | null>(null);
  const [resetPwError, setResetPwError] = useState<string | null>(null);
  const [pwCopied, setPwCopied] = useState(false);

  useEffect(() => {
    // Check admin role
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setIsAdmin(payload.role === 'admin');
      } catch (e) {}
    }
    
    fetchWorkspace();
    fetchInvites();
    fetchSubscription();
    fetchMembers();
  }, [workspaceId]);

  const fetchWorkspace = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setWorkspace(data);
      }
    } catch (err) {
      console.error('Failed to fetch workspace', err);
    }
  };

  const fetchSubscription = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/subscription/admin/workspace/${workspaceId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSubscription(data);
        // Reset local edit states
        setEditPlan(null);
        setEditAddons(null);
      }
    } catch (err) {
      console.error('Failed to fetch subscription', err);
    }
  };

  const fetchInvites = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}/invites`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setInvites(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch invites', err);
    } finally {
      setLoading(false);
    }
  };

  const addInvite = async () => {
    if (!newEmail.trim()) return;
    
    setAdding(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}/invites`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: newEmail.trim().toLowerCase(), role: newRole }),
      });
      
      if (res.ok) {
        toast.success('Email autorisé ajouté !');
        setShowAddDialog(false);
        setNewEmail('');
        setNewRole('member');
        fetchInvites();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
      }
    } catch (err) {
      toast.error('Erreur');
    } finally {
      setAdding(false);
    }
  };

  const removeInvite = async (inviteId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}/invites/${inviteId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        toast.success('Email retiré');
        fetchInvites();
      } else {
        toast.error('Erreur');
      }
    } catch (err) {
      toast.error('Erreur');
    }
  };

  // ---- Members management ----

  const fetchMembers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setWsDetail(data);
      }
    } catch (err) {
      console.error('Failed to fetch members', err);
    }
  };

  const addMember = async () => {
    if (!memberEmail.trim()) return;
    if (memberAuthProvider === 'credentials' && memberPassword.length < 6) {
      setMemberError('Le mot de passe doit contenir au moins 6 caractères');
      return;
    }
    setAddingMember(true);
    setMemberError(null);
    try {
      const token = localStorage.getItem('access_token');
      const payload: Record<string, string> = {
        user_email: memberEmail.trim().toLowerCase(),
        role: memberRole,
        auth_provider: memberAuthProvider,
      };
      if (memberAuthProvider === 'credentials') {
        payload.password = memberPassword;
      }
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}/members`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        toast.success('Membre ajouté !');
        setShowAddMemberDialog(false);
        setMemberEmail('');
        setMemberRole('member');
        setMemberAuthProvider('credentials');
        setMemberPassword('');
        fetchMembers();
        fetchWorkspace();
      } else {
        const error = await res.json();
        setMemberError(error.detail || 'Erreur');
      }
    } catch (err) {
      setMemberError("Erreur lors de l'ajout");
    } finally {
      setAddingMember(false);
    }
  };

  const updateMemberRole = async (memberId: number, newRole: string) => {
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/workspaces/${workspaceId}/members/${memberId}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      });
      fetchMembers();
    } catch (err) {
      console.error(err);
    }
  };

  const removeMember = async (memberId: number) => {
    if (!confirm('Retirer ce membre ?')) return;
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/workspaces/${workspaceId}/members/${memberId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      toast.success('Membre retiré');
      fetchMembers();
      fetchWorkspace();
    } catch (err) {
      console.error(err);
    }
  };

  const openResetPw = (member: WorkspaceMember) => {
    setResetTarget(member);
    setGeneratedPw(null);
    setResetPwError(null);
    setPwCopied(false);
    setShowResetPwDialog(true);
  };

  const confirmResetPw = async () => {
    if (!resetTarget) return;
    setResettingPw(true);
    setResetPwError(null);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}/members/${resetTarget.id}/reset-password`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedPw(data.generated_password);
      } else {
        const error = await res.json();
        setResetPwError(error.detail || 'Erreur');
      }
    } catch (err) {
      setResetPwError('Erreur lors de la réinitialisation');
    } finally {
      setResettingPw(false);
    }
  };

  const copyPw = () => {
    if (generatedPw) {
      navigator.clipboard.writeText(generatedPw);
      setPwCopied(true);
      setTimeout(() => setPwCopied(false), 2000);
    }
  };

  const deleteWorkspace = async () => {
    setDeleting(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        toast.success('Workspace supprimé');
        router.push('/workspaces');
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur de suppression');
      }
    } catch (err) {
      toast.error('Erreur de suppression');
    } finally {
      setDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  // Show loading while checking admin status
  if (isAdmin === null || loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="text-center">
              <Shield className="h-12 w-12 mx-auto text-red-500 mb-4" />
              <h2 className="text-xl font-semibold text-red-800">Accès réservé aux administrateurs</h2>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/workspaces">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {workspace?.name || 'Workspace'}
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Gérer les emails autorisés
            </p>
          </div>
        </div>
        <Button 
          variant="destructive" 
          onClick={() => setShowDeleteDialog(true)}
        >
          <Trash2 className="h-4 w-4 mr-2" />
          Supprimer l'instance
        </Button>
      </div>

      <Card><CardHeader><CardTitle>Abonnement</CardTitle></CardHeader><CardContent>
        <p>{subscription?.plan_display_name || 'Consultez les demandes d’abonnement pour ce workspace.'}</p>
        <a href="/admin/subscription-requests" className="underline">Examiner les demandes et autorisations d’activation</a>
      </CardContent></Card>

      {/* Membres & Accès */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-600" />
                Membres & Accès
              </CardTitle>
              <CardDescription>
                Gérez les membres et les emails autorisés de ce workspace
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setShowAddDialog(true)}>
                <Mail className="h-4 w-4 mr-2" />
                Email autorisé
              </Button>
              <Button size="sm" onClick={() => setShowAddMemberDialog(true)}>
                <UserPlus className="h-4 w-4 mr-2" />
                Ajouter un membre
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* === Membres actifs === */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <User className="h-3.5 w-3.5" />
              Membres actifs ({(wsDetail?.members_count ?? 0)})
            </h4>

            {/* Owner row */}
            {wsDetail ? (
              <div className="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-950/20 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
                    <Crown className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <p className="font-medium">{wsDetail.owner_name || 'Propriétaire'}</p>
                    <p className="text-xs text-gray-400">Propriétaire</p>
                  </div>
                </div>
                <Badge variant="outline" className="bg-amber-100 text-amber-700 border-amber-200">
                  <Crown className="h-3 w-3 mr-1" />
                  Propriétaire
                </Badge>
              </div>
            ) : null}

            {/* Members list */}
            {(wsDetail?.members ?? []).map((member) => (
              <div key={member.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-slate-700 flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-500">
                      {(member.user_name || member.user_email || '?').charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium">{member.user_name || member.user_email}</p>
                    {member.user_email && member.user_name && (
                      <p className="text-xs text-gray-400">{member.user_email}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Select
                    value={member.role}
                    onValueChange={(v: string) => updateMemberRole(member.id, v)}
                  >
                    <SelectTrigger className="w-32 h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">
                        <span className="flex items-center gap-1"><Shield className="h-3 w-3 text-red-500" /> Admin</span>
                      </SelectItem>
                      <SelectItem value="member">
                        <span className="flex items-center gap-1"><User className="h-3 w-3 text-blue-500" /> Membre</span>
                      </SelectItem>
                      <SelectItem value="viewer">
                        <span className="flex items-center gap-1"><Eye className="h-3 w-3 text-gray-400" /> Lecteur</span>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                    onClick={() => openResetPw(member)}
                    title="Réinitialiser le mot de passe"
                  >
                    <KeyRound className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                    onClick={() => removeMember(member.id)}
                    title="Retirer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}

            {(!wsDetail || !wsDetail.members || wsDetail.members.length === 0) && (
              <div className="text-center py-4 text-gray-400 text-sm">
                Aucun membre ajouté
              </div>
            )}
          </div>

          {/* === Divider === */}
          <div className="border-t" />

          {/* === Emails autorisés === */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <Mail className="h-3.5 w-3.5" />
              Emails autorisés ({invites.length})
            </h4>
            <p className="text-xs text-gray-400">
              Ces utilisateurs seront automatiquement ajoutés au workspace lors de leur connexion.
            </p>

            {invites.length === 0 ? (
              <div className="text-center py-4 text-gray-400 text-sm">
                Aucun email autorisé
              </div>
            ) : (
              <div className="space-y-2">
                {invites.map((invite) => (
                  <div
                    key={invite.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-blue-100 dark:bg-blue-950 flex items-center justify-center">
                        <Mail className="h-4 w-4 text-blue-500" />
                      </div>
                      <div>
                        <p className="font-medium">{invite.email}</p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Badge variant="outline" className={roleLabels[invite.role]?.color || ''}>
                            {roleLabels[invite.role]?.icon}
                            <span className="ml-1">{roleLabels[invite.role]?.label || invite.role}</span>
                          </Badge>
                          {invite.claimed ? (
                            <span className="flex items-center gap-1 text-green-600">
                              <Check className="h-3 w-3" />
                              Utilisé
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-orange-500">
                              <Clock className="h-3 w-3" />
                              En attente
                            </span>
                          )}
                          <span className="text-gray-400">
                            {format(new Date(invite.created_at), 'dd MMM yyyy', { locale: fr })}
                          </span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                      onClick={() => removeInvite(invite.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Add Member Dialog */}
      <Dialog open={showAddMemberDialog} onOpenChange={setShowAddMemberDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-blue-600" />
              Ajouter un membre
            </DialogTitle>
            <DialogDescription>
              Invitez un utilisateur existant ou créez un nouveau compte.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                placeholder="utilisateur@email.com"
                value={memberEmail}
                onChange={(e) => setMemberEmail(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Rôle</Label>
              <Select value={memberRole} onValueChange={(v: any) => setMemberRole(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2"><Shield className="h-4 w-4 text-red-500" /> Admin</div>
                  </SelectItem>
                  <SelectItem value="member">
                    <div className="flex items-center gap-2"><User className="h-4 w-4 text-blue-500" /> Membre</div>
                  </SelectItem>
                  <SelectItem value="viewer">
                    <div className="flex items-center gap-2"><Eye className="h-4 w-4 text-gray-500" /> Lecteur</div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Type de compte</Label>
              <Select value={memberAuthProvider} onValueChange={(v: any) => setMemberAuthProvider(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="credentials">
                    <div className="flex items-center gap-2"><Lock className="h-4 w-4" /> Email & mot de passe</div>
                  </SelectItem>
                  <SelectItem value="google">
                    <div className="flex items-center gap-2"><Mail className="h-4 w-4" /> Compte Google (SSO)</div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-400">
                {memberAuthProvider === 'google'
                  ? "L'utilisateur se connectera via Google Sign-In."
                  : "L'utilisateur se connectera avec un email et un mot de passe."}
              </p>
            </div>
            {memberAuthProvider === 'credentials' && (
              <div className="space-y-2">
                <Label>Mot de passe temporaire</Label>
                <Input
                  type="password"
                  placeholder="Min. 6 caractères"
                  value={memberPassword}
                  onChange={(e) => setMemberPassword(e.target.value)}
                />
              </div>
            )}
            {memberError && (
              <p className="text-sm text-red-500 flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                {memberError}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddMemberDialog(false)}>Annuler</Button>
            <Button onClick={addMember} disabled={!memberEmail.trim() || addingMember}>
              {addingMember ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserPlus className="h-4 w-4 mr-2" />}
              Ajouter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={showResetPwDialog} onOpenChange={(open) => {
        if (!open) { setShowResetPwDialog(false); setGeneratedPw(null); setResetPwError(null); }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-amber-600" />
              Réinitialiser le mot de passe
            </DialogTitle>
            <DialogDescription>
              {generatedPw
                ? "Le nouveau mot de passe a été généré. Transmettez-le à l'utilisateur."
                : `Générer un nouveau mot de passe pour ${resetTarget?.user_name || resetTarget?.user_email || 'cet utilisateur'} ?`}
            </DialogDescription>
          </DialogHeader>

          {!generatedPw && !resetPwError && (
            <p className="text-sm text-gray-500 py-2">
              Un mot de passe aléatoire sera généré. L'utilisateur devra l'utiliser pour se reconnecter.
            </p>
          )}

          {generatedPw && (
            <div className="space-y-3">
              <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-4">
                <p className="text-xs text-amber-600 mb-1 font-medium">Nouveau mot de passe :</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-lg font-mono font-bold text-amber-800 dark:text-amber-300 select-all">
                    {generatedPw}
                  </code>
                  <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" onClick={copyPw}>
                    {pwCopied ? <CheckCircle className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Ce mot de passe ne sera plus affiché après fermeture.
              </p>
            </div>
          )}

          {resetPwError && (
            <p className="text-sm text-red-500 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              {resetPwError}
            </p>
          )}

          <DialogFooter>
            {!generatedPw ? (
              <>
                <Button variant="outline" onClick={() => setShowResetPwDialog(false)}>Annuler</Button>
                <Button onClick={confirmResetPw} disabled={resettingPw} className="bg-amber-600 hover:bg-amber-700 text-white">
                  {resettingPw ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <KeyRound className="h-4 w-4 mr-2" />}
                  Générer un nouveau mot de passe
                </Button>
              </>
            ) : (
              <Button onClick={() => setShowResetPwDialog(false)}>Fermer</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Invite Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ajouter un Email Autorisé</DialogTitle>
            <DialogDescription>
              L'utilisateur avec cet email sera automatiquement ajouté au workspace lors de sa connexion.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="exemple@email.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Rôle dans le workspace</Label>
              <Select value={newRole} onValueChange={(v: any) => setNewRole(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-red-500" />
                      Admin - Accès complet
                    </div>
                  </SelectItem>
                  <SelectItem value="member">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-blue-500" />
                      Membre - Lecture/Écriture
                    </div>
                  </SelectItem>
                  <SelectItem value="viewer">
                    <div className="flex items-center gap-2">
                      <Eye className="h-4 w-4 text-gray-500" />
                      Viewer - Lecture seule
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Annuler
            </Button>
            <Button onClick={addInvite} disabled={adding || !newEmail.trim()}>
              {adding && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Ajouter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Supprimer l'instance</DialogTitle>
            <DialogDescription>
              Êtes-vous sûr de vouloir supprimer le workspace <strong>"{workspace?.name}"</strong> ?
              <br /><br />
              Cette action est <strong className="text-red-600">irréversible</strong> et supprimera :
              <ul className="list-disc list-inside mt-2 text-sm">
                <li>Tous les emails autorisés</li>
                <li>Tous les membres associés</li>
                <li>Toutes les configurations</li>
              </ul>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Annuler
            </Button>
            <Button variant="destructive" onClick={deleteWorkspace} disabled={deleting}>
              {deleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Supprimer définitivement
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
