'use client';

import { useState, useEffect, useCallback } from 'react';
import { 
  Users, UserPlus, Mail, Trash2, CheckCircle, Clock, 
  Building2, Shield, Eye, Search, RefreshCw,
  AlertCircle, Copy, Check, Settings
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { ProtectedRoute, AdminLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import api from "@/lib/api";

interface Workspace {
  id: number;
  name: string;
  members_count: number;
  owner_name?: string;
  owner_user_id: number;
}

interface WorkspaceMember {
  id: number;
  user_id: number;
  role: string;
  user_name?: string;
  user_email?: string;
  invited_at?: string;
  accepted_at?: string;
}

interface WorkspaceInvite {
  id: number;
  workspace_id: number;
  email: string;
  role: string;
  claimed: boolean;
  claimed_at?: string;
  created_at: string;
}

interface User {
  id: number;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

export default function AdminMembersPage() {
  return (
    <ProtectedRoute requiredRoles={['admin']}>
      <AdminLayout>
        <AdminMembersContent />
      </AdminLayout>
    </ProtectedRoute>
  );
}

function AdminMembersContent() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<number | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invites, setInvites] = useState<WorkspaceInvite[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMembers, setLoadingMembers] = useState(false);
  
  // Admin settings
  const [sendEmails, setSendEmails] = useState(true);
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [updatingSettings, setUpdatingSettings] = useState(false);
  
  // Dialog states
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [newInviteEmail, setNewInviteEmail] = useState('');
  const [newInviteRole, setNewInviteRole] = useState('member');
  const [inviting, setInviting] = useState(false);

  // Fetch workspaces
  const fetchWorkspaces = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/workspaces');
      setWorkspaces(response.data.items || []);
      if (response.data.items?.length > 0 && !selectedWorkspace) {
        setSelectedWorkspace(response.data.items[0].id);
      }
    } catch (error) {
      console.error('Error fetching workspaces:', error);
      toast.error('Erreur lors du chargement des workspaces');
    }
  }, [selectedWorkspace]);

  // Fetch all users
  const fetchAllUsers = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/users');
      setAllUsers(response.data.items || response.data || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  }, []);

  // Fetch members and invites for selected workspace
  const fetchWorkspaceData = useCallback(async () => {
    if (!selectedWorkspace) return;
    
    setLoadingMembers(true);
    try {
      const [workspaceRes, invitesRes] = await Promise.all([
        api.get(`/api/v1/workspaces/${selectedWorkspace}`),
        api.get(`/api/v1/workspaces/${selectedWorkspace}/invites`),
      ]);
      
      setMembers(workspaceRes.data.members || []);
      setInvites(invitesRes.data.items || []);
    } catch (error) {
      console.error('Error fetching workspace data:', error);
      toast.error('Erreur lors du chargement des données');
    } finally {
      setLoadingMembers(false);
    }
  }, [selectedWorkspace]);

  // Initial load
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([fetchWorkspaces(), fetchAllUsers(), fetchAdminSettings()]);
      setLoading(false);
    };
    load();
  }, [fetchWorkspaces, fetchAllUsers]);

  // Fetch admin settings
  const fetchAdminSettings = async () => {
    try {
      const response = await api.get('/api/v1/users/admin/settings');
      setSendEmails(response.data.send_invitation_emails ?? true);
      setEmailConfigured(response.data.email_configured ?? false);
    } catch (error) {
      console.error('Error fetching admin settings:', error);
    }
  };

  // Update email toggle
  const handleToggleEmails = async (enabled: boolean) => {
    setUpdatingSettings(true);
    try {
      await api.put('/api/v1/users/admin/settings', {
        send_invitation_emails: enabled,
      });
      setSendEmails(enabled);
      toast.success(enabled ? 'Emails d\'invitation activés' : 'Emails d\'invitation désactivés');
    } catch (error) {
      console.error('Error updating settings:', error);
      toast.error('Erreur lors de la mise à jour');
    } finally {
      setUpdatingSettings(false);
    }
  };

  // Load workspace data when selection changes
  useEffect(() => {
    if (selectedWorkspace) {
      fetchWorkspaceData();
    }
  }, [selectedWorkspace, fetchWorkspaceData]);

  // Add invite
  const handleAddInvite = async () => {
    if (!newInviteEmail.trim() || !selectedWorkspace) return;
    
    setInviting(true);
    try {
      await api.post(`/api/v1/workspaces/${selectedWorkspace}/invites`, {
        email: newInviteEmail.toLowerCase().trim(),
        role: newInviteRole,
      });
      
      toast.success(`Invitation envoyée à ${newInviteEmail}`);
      setNewInviteEmail('');
      setInviteDialogOpen(false);
      fetchWorkspaceData();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erreur lors de l\'invitation';
      toast.error(message);
    } finally {
      setInviting(false);
    }
  };

  // Delete invite
  const handleDeleteInvite = async (inviteId: number) => {
    if (!selectedWorkspace) return;
    
    try {
      await api.delete(`/api/v1/workspaces/${selectedWorkspace}/invites/${inviteId}`);
      toast.success('Invitation supprimée');
      fetchWorkspaceData();
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  // Remove member
  const handleRemoveMember = async (memberId: number) => {
    if (!selectedWorkspace) return;
    
    try {
      await api.delete(`/api/v1/workspaces/${selectedWorkspace}/members/${memberId}`);
      toast.success('Membre retiré');
      fetchWorkspaceData();
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  // Update member role
  const handleUpdateRole = async (memberId: number, newRole: string) => {
    if (!selectedWorkspace) return;
    
    try {
      await api.patch(`/api/v1/workspaces/${selectedWorkspace}/members/${memberId}`, {
        role: newRole,
      });
      toast.success('Rôle mis à jour');
      fetchWorkspaceData();
    } catch (error) {
      toast.error('Erreur lors de la mise à jour');
    }
  };

  const currentWorkspace = workspaces.find(w => w.id === selectedWorkspace);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Gestion des membres
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Gérez les membres et les invitations de vos workspaces
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Email toggle */}
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <Mail className={`h-4 w-4 ${emailConfigured ? 'text-green-500' : 'text-gray-400'}`} />
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Emails d'invitation
              </span>
              {!emailConfigured && (
                <span className="text-xs text-amber-500">Non configuré</span>
              )}
            </div>
            <Switch
              checked={sendEmails}
              onCheckedChange={handleToggleEmails}
              disabled={updatingSettings || !emailConfigured}
            />
          </div>
          
          <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
            <DialogTrigger asChild>
              <Button disabled={!selectedWorkspace}>
                <UserPlus className="h-4 w-4 mr-2" />
                Inviter
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Inviter un membre</DialogTitle>
              <DialogDescription>
                L'utilisateur recevra un accès au workspace dès qu'il se connectera avec cet email.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="nom@exemple.com"
                  value={newInviteEmail}
                  onChange={(e) => setNewInviteEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Rôle</Label>
                <Select value={newInviteRole} onValueChange={setNewInviteRole}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        Admin
                      </div>
                    </SelectItem>
                    <SelectItem value="member">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        Membre
                      </div>
                    </SelectItem>
                    <SelectItem value="viewer">
                      <div className="flex items-center gap-2">
                        <Eye className="h-4 w-4" />
                        Lecture seule
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
                Annuler
              </Button>
              <Button onClick={handleAddInvite} disabled={inviting || !newInviteEmail.trim()}>
                {inviting && <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />}
                Envoyer l'invitation
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {/* Workspace selector */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Workspace
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={selectedWorkspace?.toString() || ''}
            onValueChange={(v) => setSelectedWorkspace(parseInt(v))}
          >
            <SelectTrigger className="w-full md:w-80">
              <SelectValue placeholder="Sélectionner un workspace" />
            </SelectTrigger>
            <SelectContent>
              {workspaces.map((ws) => (
                <SelectItem key={ws.id} value={ws.id.toString()}>
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    {ws.name}
                    <Badge variant="secondary" className="ml-2">
                      {ws.members_count} membre{ws.members_count > 1 ? 's' : ''}
                    </Badge>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Members & Invites tabs */}
      {selectedWorkspace && (
        <Tabs defaultValue="members" className="space-y-4">
          <TabsList>
            <TabsTrigger value="members" className="gap-2">
              <Users className="h-4 w-4" />
              Membres ({members.length})
            </TabsTrigger>
            <TabsTrigger value="invites" className="gap-2">
              <Mail className="h-4 w-4" />
              Invitations ({invites.filter(i => !i.claimed).length} en attente)
            </TabsTrigger>
            <TabsTrigger value="all-users" className="gap-2">
              <Users className="h-4 w-4" />
              Tous les utilisateurs ({allUsers.length})
            </TabsTrigger>
          </TabsList>

          {/* Members tab */}
          <TabsContent value="members">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Membres du workspace</CardTitle>
                  <Button variant="ghost" size="sm" onClick={fetchWorkspaceData}>
                    <RefreshCw className={`h-4 w-4 ${loadingMembers ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {loadingMembers ? (
                  <div className="flex justify-center py-8">
                    <RadarSpinner className="h-6 w-6 animate-spin" />
                  </div>
                ) : members.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    Aucun membre pour l'instant
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Utilisateur</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Rôle</TableHead>
                        <TableHead>Depuis</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {members.map((member) => (
                        <TableRow key={member.id}>
                          <TableCell className="font-medium">
                            {member.user_name || 'Sans nom'}
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {member.user_email}
                          </TableCell>
                          <TableCell>
                            <Select
                              value={member.role}
                              onValueChange={(v) => handleUpdateRole(member.id, v)}
                            >
                              <SelectTrigger className="w-32">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="admin">Admin</SelectItem>
                                <SelectItem value="member">Membre</SelectItem>
                                <SelectItem value="viewer">Lecture seule</SelectItem>
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {member.invited_at 
                              ? new Date(member.invited_at).toLocaleDateString('fr-FR')
                              : '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleRemoveMember(member.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Invites tab */}
          <TabsContent value="invites">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Invitations par email</CardTitle>
                    <CardDescription>
                      Les utilisateurs avec ces emails seront automatiquement ajoutés au workspace lors de leur connexion.
                    </CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" onClick={fetchWorkspaceData}>
                    <RefreshCw className={`h-4 w-4 ${loadingMembers ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {invites.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Mail className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>Aucune invitation en cours</p>
                    <Button className="mt-4" onClick={() => setInviteDialogOpen(true)}>
                      <UserPlus className="h-4 w-4 mr-2" />
                      Inviter un membre
                    </Button>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Email</TableHead>
                        <TableHead>Rôle</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {invites.map((invite) => (
                        <TableRow key={invite.id}>
                          <TableCell className="font-medium">
                            {invite.email}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {invite.role === 'admin' && <Shield className="h-3 w-3 mr-1" />}
                              {invite.role === 'viewer' && <Eye className="h-3 w-3 mr-1" />}
                              {invite.role}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {invite.claimed ? (
                              <Badge className="bg-green-100 text-green-700">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Acceptée
                              </Badge>
                            ) : (
                              <Badge className="bg-yellow-100 text-yellow-700">
                                <Clock className="h-3 w-3 mr-1" />
                                En attente
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {new Date(invite.created_at).toLocaleDateString('fr-FR')}
                          </TableCell>
                          <TableCell className="text-right">
                            {!invite.claimed && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                onClick={() => handleDeleteInvite(invite.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* All users tab */}
          <TabsContent value="all-users">
            <Card>
              <CardHeader>
                <CardTitle>Tous les utilisateurs</CardTitle>
                <CardDescription>
                  Liste de tous les utilisateurs inscrits sur la plateforme
                </CardDescription>
              </CardHeader>
              <CardContent>
                {allUsers.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    Aucun utilisateur
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nom</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Rôle global</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>Inscription</TableHead>
                        <TableHead>Dernière connexion</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {allUsers.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">
                            {user.full_name || 'Sans nom'}
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {user.email}
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                              {user.role}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {user.is_active ? (
                              <Badge className="bg-green-100 text-green-700">Actif</Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-700">Inactif</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {new Date(user.created_at).toLocaleDateString('fr-FR')}
                          </TableCell>
                          <TableCell className="text-gray-500">
                            {user.last_login_at 
                              ? new Date(user.last_login_at).toLocaleDateString('fr-FR')
                              : 'Jamais'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
