'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  Plus, 
  Loader2, 
  FolderOpen,
  Users,
  Calendar,
  Settings,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import { AdminLayout, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { toast } from 'sonner';

interface Workspace {
  id: number;
  name: string;
  owner_user_id: number;
  owner_name?: string;
  drive_url?: string;
  members_count: number;
  created_at: string;
}

interface WorkspacesResponse {
  items: Workspace[];
  total: number;
}

export default function WorkspacesPage() {
  return (
    <ProtectedRoute requiredRoles={['admin']}>
      <AdminLayout>
        <WorkspacesContent />
      </AdminLayout>
    </ProtectedRoute>
  );
}

function WorkspacesContent() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [workspaceToDelete, setWorkspaceToDelete] = useState<Workspace | null>(null);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    fetchWorkspaces();
    const storedId = localStorage.getItem('current_workspace_id');
    setCurrentWorkspaceId(storedId);
    
    // Check if user is admin from token
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setIsAdmin(payload.role === 'admin');
      } catch (e) {
        console.error('Failed to parse token');
      }
    }
  }, []);

  const fetchWorkspaces = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch('/api/v1/workspaces', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        const data: WorkspacesResponse = await res.json();
        setWorkspaces(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch workspaces', err);
      toast.error('Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const createWorkspace = async () => {
    if (!newWorkspaceName.trim()) return;
    
    setCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch('/api/v1/workspaces', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newWorkspaceName.trim() }),
      });
      
      if (res.ok) {
        const workspace = await res.json();
        toast.success('Workspace créé !');
        setShowCreateDialog(false);
        setNewWorkspaceName('');
        fetchWorkspaces();
        
        // Set as current workspace
        localStorage.setItem('current_workspace_id', workspace.id.toString());
        setCurrentWorkspaceId(workspace.id.toString());
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur de création');
      }
    } catch (err) {
      toast.error('Erreur de création');
    } finally {
      setCreating(false);
    }
  };

  const selectWorkspace = (workspace: Workspace) => {
    localStorage.setItem('current_workspace_id', workspace.id.toString());
    setCurrentWorkspaceId(workspace.id.toString());
    toast.success(`Workspace "${workspace.name}" sélectionné`);
    router.push('/inbox');
  };

  const deleteWorkspace = async () => {
    if (!workspaceToDelete) return;
    
    setDeleting(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/workspaces/${workspaceToDelete.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        toast.success('Workspace supprimé');
        setShowDeleteDialog(false);
        setWorkspaceToDelete(null);
        fetchWorkspaces();
        
        // Clear current workspace if it was deleted
        if (currentWorkspaceId === workspaceToDelete.id.toString()) {
          localStorage.removeItem('current_workspace_id');
          setCurrentWorkspaceId(null);
        }
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur de suppression');
      }
    } catch (err) {
      toast.error('Erreur de suppression');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FolderOpen className="h-6 w-6" />
            Workspaces
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Gérez vos espaces de travail
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Nouveau Workspace
          </Button>
        )}
      </div>

      {/* Workspaces Grid */}
      {workspaces.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <FolderOpen className="h-12 w-12 mx-auto text-gray-400" />
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Aucun workspace
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  {isAdmin ? 'Créez votre premier workspace pour commencer' : 'Contactez un administrateur pour obtenir l\'accès à un workspace'}
                </p>
              </div>
              {isAdmin && (
                <Button onClick={() => setShowCreateDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Créer un Workspace
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {workspaces.map((workspace) => {
            const isSelected = currentWorkspaceId === workspace.id.toString();
            return (
              <Card 
                key={workspace.id}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  isSelected ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-950/20' : ''
                }`}
                onClick={() => selectWorkspace(workspace)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {workspace.name}
                        {isSelected && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                            Actif
                          </span>
                        )}
                      </CardTitle>
                      <CardDescription>
                        Créé par {workspace.owner_name || 'Vous'}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <Users className="h-4 w-4" />
                        {workspace.members_count} membre{workspace.members_count > 1 ? 's' : ''}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {format(new Date(workspace.created_at), 'dd MMM yyyy', { locale: fr })}
                      </div>
                      {workspace.drive_url && (
                        <a 
                          href={workspace.drive_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-blue-600 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="h-4 w-4" />
                          Drive
                        </a>
                      )}
                    </div>
                    {isAdmin && (
                      <div className="flex items-center gap-2">
                        <Link 
                          href={`/workspaces/${workspace.id}`}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Button variant="outline" size="sm">
                            <Settings className="h-4 w-4 mr-1" />
                            Gérer
                          </Button>
                        </Link>
                        <Button 
                          variant="outline" 
                          size="sm"
                          className="text-red-500 hover:text-red-700 hover:bg-red-50 border-red-200"
                          onClick={(e) => {
                            e.stopPropagation();
                            setWorkspaceToDelete(workspace);
                            setShowDeleteDialog(true);
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouveau Workspace</DialogTitle>
            <DialogDescription>
              Un workspace regroupe vos projets, clients et l'inbox.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nom du workspace</Label>
              <Input
                id="name"
                placeholder="Ex: Mon Agence"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && createWorkspace()}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Annuler
            </Button>
            <Button onClick={createWorkspace} disabled={creating || !newWorkspaceName.trim()}>
              {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Supprimer l&apos;instance</DialogTitle>
            <DialogDescription className="sr-only">
              Confirmer la suppression du workspace
            </DialogDescription>
          </DialogHeader>
          <div className="text-sm text-muted-foreground">
            <p>Êtes-vous sûr de vouloir supprimer le workspace <strong>&quot;{workspaceToDelete?.name}&quot;</strong> ?</p>
            <p className="mt-2">Cette action est <strong className="text-red-600">irréversible</strong> et supprimera :</p>
            <ul className="list-disc list-inside mt-2">
              <li>Tous les emails autorisés</li>
              <li>Tous les membres associés</li>
              <li>Toutes les configurations</li>
            </ul>
          </div>
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
