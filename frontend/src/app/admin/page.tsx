'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { 
  Building2,
  Users,
  Mail,
  Activity,
  Plus,
  Loader2,
  CheckCircle,
} from 'lucide-react';
import Link from 'next/link';
import { ProtectedRoute, AdminLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface DashboardStats {
  total_workspaces: number;
  total_users: number;
  pending_invites: number;
  active_users_today: number;
}

interface Workspace {
  id: number;
  name: string;
  members_count: number;
  owner_name?: string;
}

export default function AdminDashboardPage() {
  return (
    <ProtectedRoute requiredRoles={['admin']}>
      <AdminLayout>
        <AdminDashboardContent />
      </AdminLayout>
    </ProtectedRoute>
  );
}

function AdminDashboardContent() {
  const [stats, setStats] = useState<DashboardStats>({
    total_workspaces: 0,
    total_users: 0,
    pending_invites: 0,
    active_users_today: 0,
  });
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      // Fetch workspaces
      const wsRes = await workspaceFetch('/api/v1/workspaces', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (wsRes.ok) {
        const data = await wsRes.json();
        setWorkspaces(data.items || []);
        setStats(prev => ({ ...prev, total_workspaces: data.total || data.items?.length || 0 }));
      }
      
      // Fetch users count
      const usersRes = await workspaceFetch('/api/v1/users?limit=1', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (usersRes.ok) {
        const data = await usersRes.json();
        setStats(prev => ({ ...prev, total_users: data.total || 0 }));
      }
      
    } catch (err) {
      console.error('Failed to fetch admin data', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-xl">
                <Building2 className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats.total_workspaces}</p>
                <p className="text-sm text-gray-500">Workspaces</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-xl">
                <Users className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats.total_users}</p>
                <p className="text-sm text-gray-500">Utilisateurs</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-xl">
                <Mail className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats.pending_invites}</p>
                <p className="text-sm text-gray-500">Invitations en attente</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats.active_users_today}</p>
                <p className="text-sm text-gray-500">Actifs aujourd'hui</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/workspaces">
          <Card className="cursor-pointer hover:shadow-lg transition-all hover:border-violet-300 h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Building2 className="h-5 w-5 text-blue-600" />
                Gérer les Workspaces
              </CardTitle>
              <CardDescription>
                Créer et configurer les instances des agences
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        
        <Link href="/users">
          <Card className="cursor-pointer hover:shadow-lg transition-all hover:border-violet-300 h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Users className="h-5 w-5 text-green-600" />
                Gérer les Utilisateurs
              </CardTitle>
              <CardDescription>
                Comptes, permissions et accès des utilisateurs
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
        
        <Link href="/admin/activity">
          <Card className="cursor-pointer hover:shadow-lg transition-all hover:border-violet-300 h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Activity className="h-5 w-5 text-purple-600" />
                Logs d'Activité
              </CardTitle>
              <CardDescription>
                Historique des actions sur la plateforme
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>

      {/* Workspaces List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Workspaces Actifs</CardTitle>
            <CardDescription>Toutes les agences utilisant Radar</CardDescription>
          </div>
          <Link href="/workspaces">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {workspaces.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="font-medium">Aucun workspace créé</p>
              <p className="text-sm">Créez votre premier workspace pour commencer</p>
            </div>
          ) : (
            <div className="space-y-3">
              {workspaces.slice(0, 5).map((ws) => (
                <Link key={ws.id} href={`/workspaces/${ws.id}`}>
                  <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                        <Building2 className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 dark:text-white">{ws.name}</p>
                        <p className="text-sm text-gray-500">
                          {ws.members_count} membre{ws.members_count > 1 ? 's' : ''} • Créé par {ws.owner_name || 'Admin'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 text-sm text-green-600">
                        <CheckCircle className="h-4 w-4" />
                        Actif
                      </span>
                      <Button variant="ghost" size="sm">
                        Gérer →
                      </Button>
                    </div>
                  </div>
                </Link>
              ))}
              {workspaces.length > 5 && (
                <Link href="/workspaces">
                  <p className="text-center text-sm text-violet-600 hover:underline py-2">
                    Voir tous les {workspaces.length} workspaces →
                  </p>
                </Link>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
