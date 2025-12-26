'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import {
  Activity,
  Users,
  Eye,
  LogIn,
  LogOut,
  Search,
  FileText,
  Settings,
  RefreshCw,
  Filter,
  Clock,
  User,
  ChevronDown,
  AlertCircle,
} from 'lucide-react';
import { adminApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';

interface ActivityLog {
  id: string;
  user_tracking_id: string;
  user_email: string | null;
  user_name: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

interface UserTracking {
  id: string;
  tracking_id: string;
  email: string | null;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_whitelisted: boolean;
  last_login_at: string | null;
  created_at: string;
}

const actionIcons: Record<string, React.ReactNode> = {
  login: <LogIn className="h-4 w-4 text-green-500" />,
  logout: <LogOut className="h-4 w-4 text-gray-500" />,
  view: <Eye className="h-4 w-4 text-blue-500" />,
  create: <FileText className="h-4 w-4 text-purple-500" />,
  update: <Settings className="h-4 w-4 text-orange-500" />,
  delete: <AlertCircle className="h-4 w-4 text-red-500" />,
  search: <Search className="h-4 w-4 text-cyan-500" />,
  analyze: <Activity className="h-4 w-4 text-pink-500" />,
};

const actionLabels: Record<string, string> = {
  login: 'Connexion',
  logout: 'Déconnexion',
  view: 'Consultation',
  create: 'Création',
  update: 'Modification',
  delete: 'Suppression',
  search: 'Recherche',
  analyze: 'Analyse',
  radar_trigger: 'Déclenchement Radar',
  user_create: 'Création utilisateur',
  whitelist: 'Whitelist',
};

export default function ActivityLogsPage() {
  const { user } = useAuth();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Check if superuser
  if (user && !user.is_superuser) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Accès Refusé</h1>
          <p className="text-gray-400">Cette page est réservée aux super administrateurs.</p>
        </div>
      </div>
    );
  }

  // Fetch users with tracking IDs
  const { data: users = [] } = useQuery<UserTracking[]>({
    queryKey: ['admin-users-tracking'],
    queryFn: async () => {
      const response = await adminApi.getUsersTracking();
      return response;
    },
    staleTime: 60000,
  });

  // Fetch activity logs
  const { data: logs = [], refetch, isLoading } = useQuery<ActivityLog[]>({
    queryKey: ['activity-logs', selectedUser, selectedAction],
    queryFn: async () => {
      const params: Record<string, string> = { limit: '100' };
      if (selectedUser) params.user_tracking_id = selectedUser;
      if (selectedAction) params.action = selectedAction;
      const response = await adminApi.getLogs(params);
      return response;
    },
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['activity-stats'],
    queryFn: () => adminApi.getStats(24),
    refetchInterval: autoRefresh ? 30000 : false,
  });

  useEffect(() => {
    if (autoRefresh) {
      setLastUpdate(new Date());
    }
  }, [logs, autoRefresh]);

  const handleRefresh = useCallback(() => {
    refetch();
    setLastUpdate(new Date());
  }, [refetch]);

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <Activity className="h-7 w-7 text-purple-500" />
              Logs d'Activité en Temps Réel
            </h1>
            <p className="text-gray-400 mt-1">
              Surveillance des actions utilisateurs • Superadmin uniquement
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Dernière mise à jour: {format(lastUpdate, 'HH:mm:ss', { locale: fr })}
            </div>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                autoRefresh 
                  ? 'bg-green-600 text-white' 
                  : 'bg-gray-700 text-gray-300'
              }`}
            >
              <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
            </button>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg flex items-center gap-2 hover:bg-purple-700"
            >
              <RefreshCw className="h-4 w-4" />
              Rafraîchir
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="text-3xl font-bold text-white">{stats.total_logs}</div>
              <div className="text-gray-400 text-sm">Actions (24h)</div>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="text-3xl font-bold text-green-500">{stats.active_users}</div>
              <div className="text-gray-400 text-sm">Utilisateurs actifs</div>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="text-3xl font-bold text-blue-500">{stats.actions?.login || 0}</div>
              <div className="text-gray-400 text-sm">Connexions</div>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="text-3xl font-bold text-purple-500">{stats.actions?.view || 0}</div>
              <div className="text-gray-400 text-sm">Consultations</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-4 gap-6">
          {/* Users Panel */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="p-4 border-b border-gray-700">
              <h2 className="font-semibold text-white flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-500" />
                Utilisateurs ({users.length})
              </h2>
            </div>
            <div className="max-h-[500px] overflow-y-auto">
              <button
                onClick={() => setSelectedUser(null)}
                className={`w-full p-3 text-left hover:bg-gray-700 transition-colors ${
                  !selectedUser ? 'bg-purple-600/20 border-l-2 border-purple-500' : ''
                }`}
              >
                <div className="text-white font-medium">Tous les utilisateurs</div>
              </button>
              {users.map((u) => (
                <button
                  key={u.id}
                  onClick={() => setSelectedUser(u.tracking_id)}
                  className={`w-full p-3 text-left hover:bg-gray-700 transition-colors ${
                    selectedUser === u.tracking_id 
                      ? 'bg-purple-600/20 border-l-2 border-purple-500' 
                      : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium text-sm">
                        {u.full_name || u.email || 'Sans nom'}
                      </div>
                      <div className="text-xs text-purple-400 font-mono">
                        {u.tracking_id}
                      </div>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${
                      u.is_active && u.is_whitelisted ? 'bg-green-500' : 'bg-gray-500'
                    }`} />
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Logs Panel */}
          <div className="col-span-3 bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <h2 className="font-semibold text-white flex items-center gap-2">
                <Activity className="h-5 w-5 text-purple-500" />
                Historique des Actions
                {isLoading && <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />}
              </h2>
              
              {/* Action Filter */}
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-gray-400" />
                <select
                  value={selectedAction || ''}
                  onChange={(e) => setSelectedAction(e.target.value || null)}
                  className="bg-gray-700 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-600"
                >
                  <option value="">Toutes les actions</option>
                  <option value="login">Connexion</option>
                  <option value="logout">Déconnexion</option>
                  <option value="view">Consultation</option>
                  <option value="create">Création</option>
                  <option value="update">Modification</option>
                  <option value="delete">Suppression</option>
                  <option value="analyze">Analyse</option>
                  <option value="radar_trigger">Radar</option>
                </select>
              </div>
            </div>

            <div className="max-h-[550px] overflow-y-auto">
              {logs.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>Aucune activité enregistrée</p>
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-900/50 sticky top-0">
                    <tr className="text-left text-xs text-gray-400 uppercase">
                      <th className="p-3">Heure</th>
                      <th className="p-3">Utilisateur</th>
                      <th className="p-3">ID Tracking</th>
                      <th className="p-3">Action</th>
                      <th className="p-3">Ressource</th>
                      <th className="p-3">IP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-700/50">
                        <td className="p-3 text-sm text-gray-400">
                          {format(new Date(log.created_at), 'HH:mm:ss', { locale: fr })}
                          <div className="text-xs text-gray-500">
                            {format(new Date(log.created_at), 'dd/MM', { locale: fr })}
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="text-white text-sm font-medium">
                            {log.user_name || log.user_email || '-'}
                          </div>
                          <div className="text-xs text-gray-500">{log.user_email}</div>
                        </td>
                        <td className="p-3">
                          <span className="font-mono text-xs px-2 py-1 bg-purple-600/20 text-purple-400 rounded">
                            {log.user_tracking_id}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            {actionIcons[log.action] || <Activity className="h-4 w-4 text-gray-500" />}
                            <span className="text-white text-sm">
                              {actionLabels[log.action] || log.action}
                            </span>
                          </div>
                        </td>
                        <td className="p-3 text-sm text-gray-400">
                          {log.resource_type && (
                            <span className="px-2 py-0.5 bg-gray-700 rounded text-xs">
                              {log.resource_type}
                            </span>
                          )}
                          {log.resource_id && (
                            <span className="ml-1 text-xs text-gray-500">
                              #{log.resource_id.slice(0, 8)}
                            </span>
                          )}
                        </td>
                        <td className="p-3 text-xs text-gray-500 font-mono">
                          {log.ip_address || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
