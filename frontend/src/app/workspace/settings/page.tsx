'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import {
  Settings,
  Users,
  FolderOpen,
  FileText,
  Link2,
  Plus,
  Trash2,
  Check,
  AlertCircle,
  Loader2,
  ExternalLink,
  Crown,
  UserMinus,
  Copy,
  LogIn,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { googleWorkspaceApi } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';

interface WorkspaceMember {
  id: number;
  user_id: number;
  user_email: string;
  user_name: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
}

interface Workspace {
  id: number;
  name: string;
  slug: string;
  drive_root_folder_id?: string;
  brief_template_id?: string;
  report_template_id?: string;
  created_at: string;
  members: WorkspaceMember[];
}

const roleLabels: Record<string, string> = {
  owner: 'Propriétaire',
  admin: 'Admin',
  member: 'Membre',
  viewer: 'Observateur',
};

const roleColors: Record<string, string> = {
  owner: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  admin: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  member: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  viewer: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

export default function WorkspaceSettingsPage() {
  const { user } = useAuthStore();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'member' | 'viewer'>('member');
  const [inviting, setInviting] = useState(false);
  
  // Google connection state
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleEmail, setGoogleEmail] = useState<string | null>(null);
  const [checkingGoogle, setCheckingGoogle] = useState(true);
  const [connectingGoogle, setConnectingGoogle] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [driveRootId, setDriveRootId] = useState('');
  const [briefTemplateId, setBriefTemplateId] = useState('');
  const [reportTemplateId, setReportTemplateId] = useState('');

  // Check Google connection on mount
  useEffect(() => {
    const checkGoogle = async () => {
      try {
        const result = await googleWorkspaceApi.checkGoogleConnection();
        setGoogleConnected(result.connected);
        setGoogleEmail(result.email || null);
      } catch {
        setGoogleConnected(false);
      } finally {
        setCheckingGoogle(false);
      }
    };
    checkGoogle();
  }, []);

  const handleConnectGoogle = async () => {
    setConnectingGoogle(true);
    try {
      const authUrl = await googleWorkspaceApi.getGoogleAuthUrl('/workspace/settings');
      window.location.href = authUrl;
    } catch (err) {
      toast.error('Erreur lors de la connexion Google');
      setConnectingGoogle(false);
    }
  };

  const fetchWorkspace = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch('/api/v1/workspace/current', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setWorkspace(data);
        setName(data.name);
        setDriveRootId(data.drive_root_folder_id || '');
        setBriefTemplateId(data.brief_template_id || '');
        setReportTemplateId(data.report_template_id || '');
      }
    } catch (err) {
      console.error('Error fetching workspace:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, []);

  const handleSave = async () => {
    if (!workspace) return;
    setSaving(true);
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspace/${workspace.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          drive_root_folder_id: driveRootId || null,
          brief_template_id: briefTemplateId || null,
          report_template_id: reportTemplateId || null,
        }),
      });

      if (!res.ok) throw new Error('Erreur de sauvegarde');
      
      const updated = await res.json();
      setWorkspace(updated);
      toast.success('Workspace mis à jour !');
    } catch (err) {
      toast.error('Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  const handleInvite = async () => {
    if (!workspace || !inviteEmail) return;
    setInviting(true);
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspace/${workspace.id}/members`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Erreur d\'invitation');
      }
      
      toast.success(`Invitation envoyée à ${inviteEmail}`);
      setInviteOpen(false);
      setInviteEmail('');
      fetchWorkspace();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    if (!workspace) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspace/${workspace.id}/members/${memberId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('Erreur');
      
      toast.success('Membre retiré');
      fetchWorkspace();
    } catch (err) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleUpdateRole = async (memberId: number, newRole: string) => {
    if (!workspace) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspace/${workspace.id}/members/${memberId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role: newRole }),
      });

      if (!res.ok) throw new Error('Erreur');
      
      toast.success('Rôle mis à jour');
      fetchWorkspace();
    } catch (err) {
      toast.error('Erreur lors de la mise à jour');
    }
  };

  const handleSetupDrive = async () => {
    if (!workspace) return;
    setSaving(true);
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspace/${workspace.id}/setup-drive`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (res.status === 401) {
        toast.error('Connexion Google requise', {
          description: 'Veuillez connecter votre compte Google.',
          action: {
            label: 'Connecter',
            onClick: () => window.location.href = '/settings?tab=integrations',
          },
        });
        return;
      }

      if (!res.ok) throw new Error('Erreur');
      
      const data = await res.json();
      setDriveRootId(data.folder_id);
      toast.success('Structure Drive créée !', {
        action: {
          label: 'Ouvrir',
          onClick: () => window.open(data.folder_url, '_blank'),
        },
      });
      fetchWorkspace();
    } catch (err) {
      toast.error('Erreur lors de la création');
    } finally {
      setSaving(false);
    }
  };

  const copySlug = () => {
    if (workspace) {
      navigator.clipboard.writeText(workspace.slug);
      toast.success('Slug copié !');
    }
  };

  const isOwnerOrAdmin = workspace?.members.find(
    m => m.user_id === user?.id && ['owner', 'admin'].includes(m.role)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <AlertCircle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Aucun workspace</h2>
        <p className="text-gray-500 mb-6">
          Vous n'avez pas encore de workspace. Créez-en un pour commencer.
        </p>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Créer un workspace
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Paramètres du Workspace
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Configurez votre espace de travail et gérez les membres de l'équipe.
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general" className="gap-2">
            <Settings className="h-4 w-4" />
            Général
          </TabsTrigger>
          <TabsTrigger value="google" className="gap-2">
            <FolderOpen className="h-4 w-4" />
            Google Drive
          </TabsTrigger>
          <TabsTrigger value="members" className="gap-2">
            <Users className="h-4 w-4" />
            Membres
          </TabsTrigger>
        </TabsList>

        {/* General Settings */}
        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>Informations générales</CardTitle>
              <CardDescription>
                Nom et identifiant de votre workspace
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Nom du workspace</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Mon agence"
                  disabled={!isOwnerOrAdmin}
                />
              </div>

              <div className="space-y-2">
                <Label>Slug (identifiant unique)</Label>
                <div className="flex gap-2">
                  <Input
                    value={workspace.slug}
                    disabled
                    className="font-mono text-sm"
                  />
                  <Button variant="outline" size="icon" onClick={copySlug}>
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-gray-500">
                  Utilisé dans les URLs et l'API. Non modifiable.
                </p>
              </div>

              {isOwnerOrAdmin && (
                <div className="pt-4">
                  <Button onClick={handleSave} disabled={saving}>
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Check className="h-4 w-4 mr-2" />
                    )}
                    Enregistrer
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Google Drive Settings */}
        <TabsContent value="google">
          {/* Google Connection Status */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Connexion Google</CardTitle>
              <CardDescription>
                Connectez votre compte Google pour utiliser Drive, Docs et Sheets
              </CardDescription>
            </CardHeader>
            <CardContent>
              {checkingGoogle ? (
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Vérification...
                </div>
              ) : googleConnected ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Compte Google connecté</p>
                      {googleEmail && (
                        <p className="text-sm text-gray-500">{googleEmail}</p>
                      )}
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleConnectGoogle}>
                    Reconnecter
                  </Button>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center">
                      <AlertCircle className="h-5 w-5 text-gray-400" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Compte Google non connecté</p>
                      <p className="text-sm text-gray-500">
                        Connectez-vous pour créer des dossiers et documents
                      </p>
                    </div>
                  </div>
                  <Button onClick={handleConnectGoogle} disabled={connectingGoogle}>
                    {connectingGoogle ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <LogIn className="h-4 w-4 mr-2" />
                    )}
                    Connecter Google
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Intégration Google Drive</CardTitle>
              <CardDescription>
                Configurez le dossier racine et les templates pour vos documents
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Root Folder */}
              <div className="space-y-2">
                <Label>Dossier racine Drive</Label>
                <div className="flex gap-2">
                  <Input
                    value={driveRootId}
                    onChange={(e) => setDriveRootId(e.target.value)}
                    placeholder="ID du dossier Google Drive"
                    className="font-mono text-sm"
                    disabled={!isOwnerOrAdmin}
                  />
                  {driveRootId ? (
                    <Button 
                      variant="outline" 
                      size="icon"
                      onClick={() => window.open(`https://drive.google.com/drive/folders/${driveRootId}`, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  ) : (
                    <Button onClick={handleSetupDrive} disabled={saving}>
                      {saving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Plus className="h-4 w-4 mr-2" />
                          Créer
                        </>
                      )}
                    </Button>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  Tous les dossiers clients et projets seront créés dans ce dossier.
                </p>
              </div>

              {/* Brief Template */}
              <div className="space-y-2">
                <Label>Template Brief (Google Docs)</Label>
                <div className="flex gap-2">
                  <Input
                    value={briefTemplateId}
                    onChange={(e) => setBriefTemplateId(e.target.value)}
                    placeholder="ID du document template"
                    className="font-mono text-sm"
                    disabled={!isOwnerOrAdmin}
                  />
                  {briefTemplateId && (
                    <Button 
                      variant="outline" 
                      size="icon"
                      onClick={() => window.open(`https://docs.google.com/document/d/${briefTemplateId}`, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  Ce document sera copié pour chaque nouveau brief de projet.
                </p>
              </div>

              {/* Report Template */}
              <div className="space-y-2">
                <Label>Template Report (Google Sheets)</Label>
                <div className="flex gap-2">
                  <Input
                    value={reportTemplateId}
                    onChange={(e) => setReportTemplateId(e.target.value)}
                    placeholder="ID du spreadsheet template"
                    className="font-mono text-sm"
                    disabled={!isOwnerOrAdmin}
                  />
                  {reportTemplateId && (
                    <Button 
                      variant="outline" 
                      size="icon"
                      onClick={() => window.open(`https://docs.google.com/spreadsheets/d/${reportTemplateId}`, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  Ce spreadsheet sera copié pour chaque nouveau rapport de projet.
                </p>
              </div>

              {isOwnerOrAdmin && (
                <div className="pt-4">
                  <Button onClick={handleSave} disabled={saving}>
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Check className="h-4 w-4 mr-2" />
                    )}
                    Enregistrer
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Members */}
        <TabsContent value="members">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Membres de l'équipe</CardTitle>
                <CardDescription>
                  {workspace.members.length} membre{workspace.members.length > 1 ? 's' : ''}
                </CardDescription>
              </div>
              {isOwnerOrAdmin && (
                <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="h-4 w-4 mr-2" />
                      Inviter
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Inviter un membre</DialogTitle>
                      <DialogDescription>
                        Envoyez une invitation par email pour rejoindre le workspace.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          placeholder="collaborateur@example.com"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Rôle</Label>
                        <Select value={inviteRole} onValueChange={(v: any) => setInviteRole(v)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">Admin</SelectItem>
                            <SelectItem value="member">Membre</SelectItem>
                            <SelectItem value="viewer">Observateur</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setInviteOpen(false)}>
                        Annuler
                      </Button>
                      <Button onClick={handleInvite} disabled={inviting || !inviteEmail}>
                        {inviting ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : null}
                        Envoyer l'invitation
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Membre</TableHead>
                    <TableHead>Rôle</TableHead>
                    <TableHead>Rejoint le</TableHead>
                    {isOwnerOrAdmin && <TableHead className="w-[100px]"></TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workspace.members.map((member) => (
                    <TableRow key={member.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
                            {member.user_name?.charAt(0) || member.user_email?.charAt(0)}
                          </div>
                          <div>
                            <div className="font-medium">{member.user_name || 'Sans nom'}</div>
                            <div className="text-sm text-gray-500">{member.user_email}</div>
                          </div>
                          {member.user_id === user?.id && (
                            <Badge variant="outline" className="text-xs">Vous</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {isOwnerOrAdmin && member.role !== 'owner' && member.user_id !== user?.id ? (
                          <Select 
                            value={member.role} 
                            onValueChange={(v) => handleUpdateRole(member.id, v)}
                          >
                            <SelectTrigger className="w-[140px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="member">Membre</SelectItem>
                              <SelectItem value="viewer">Observateur</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge className={roleColors[member.role]}>
                            {member.role === 'owner' && <Crown className="h-3 w-3 mr-1" />}
                            {roleLabels[member.role]}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-gray-500">
                        {new Date(member.joined_at).toLocaleDateString('fr-FR')}
                      </TableCell>
                      {isOwnerOrAdmin && (
                        <TableCell>
                          {member.role !== 'owner' && member.user_id !== user?.id && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-red-500 hover:text-red-600 hover:bg-red-50"
                              onClick={() => handleRemoveMember(member.id)}
                            >
                              <UserMinus className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
