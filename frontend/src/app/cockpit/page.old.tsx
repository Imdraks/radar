'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp,
  Clock,
  Users,
  Euro,
  ArrowRight,
  Loader2,
  RefreshCw,
  Inbox,
  FolderKanban,
  Sparkles,
  Plus,
  Building2,
  Mail,
  FileText,
  Zap
} from 'lucide-react';
import Link from 'next/link';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { format, formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';

interface TodoItem {
  id: number;
  type: string;
  title: string;
  subtitle?: string;
  due_date?: string;
  priority?: string;
  client_name?: string;
  project_name?: string;
  link?: string;
}

interface UrgencyItem {
  id: number;
  type: string;
  title: string;
  subtitle?: string;
  deadline?: string;
  days_remaining?: number;
  client_name?: string;
  project_name?: string;
  severity: string;
}

interface BusinessItem {
  id: number;
  type: string;
  title: string;
  subtitle?: string;
  value?: number;
  client_name?: string;
  status?: string;
  days_waiting?: number;
}

interface InboxItemPreview {
  id: number;
  text: string;
  type: string;
  created_at: string;
  age_hours: number;
}

interface UserWorkspace {
  id: number;
  name: string;
  role: string;
  members_count: number;
}

interface DashboardData {
  todos: TodoItem[];
  todos_count: number;
  urgencies: UrgencyItem[];
  urgencies_count: number;
  business: BusinessItem[];
  business_count: number;
  active_projects: number;
  pending_validations: number;
  hot_leads: number;
  monthly_revenue: number;
}

export default function CockpitPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <CockpitContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function CockpitContent() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [inboxItems, setInboxItems] = useState<InboxItemPreview[]>([]);
  const [workspaces, setWorkspaces] = useState<UserWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      
      const dashboardRes = await workspaceFetch('/api/v1/agency/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!dashboardRes.ok) throw new Error('Failed to fetch dashboard');
      const dashboardData = await dashboardRes.json();
      setData(dashboardData);
      
      let userWorkspaces: UserWorkspace[] = [];
      try {
        const wsRes = await workspaceFetch('/api/v1/workspaces', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (wsRes.ok) {
          const wsData = await wsRes.json();
          userWorkspaces = wsData.items || [];
          setWorkspaces(userWorkspaces);
          
          if (userWorkspaces.length > 0) {
            const currentWsId = localStorage.getItem('current_workspace_id');
            const hasAccess = userWorkspaces.some(ws => ws.id.toString() === currentWsId);
            if (!hasAccess) {
              localStorage.setItem('current_workspace_id', userWorkspaces[0].id.toString());
            }
          }
        }
      } catch (e) {}
      
      try {
        const workspaceId = localStorage.getItem('current_workspace_id');
        if (workspaceId && userWorkspaces.some(ws => ws.id.toString() === workspaceId)) {
          const inboxRes = await workspaceFetch(`/api/v1/inbox?workspace_id=${workspaceId}&limit=5`, {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          if (inboxRes.ok) {
            const inboxData = await inboxRes.json();
            setInboxItems(inboxData.items || []);
          }
        }
      } catch (e) {}
      
      setError(null);
    } catch (err) {
      setError('Erreur de chargement');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <p className="text-gray-500">{error}</p>
        <Button onClick={fetchDashboard} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Réessayer
        </Button>
      </div>
    );
  }

  const hasNoTodos = !data || data.todos_count === 0;
  const hasNoUrgencies = !data || data.urgencies_count === 0;
  const hasNoBusiness = !data || data.business_count === 0;
  const allEmpty = hasNoTodos && hasNoUrgencies && hasNoBusiness && inboxItems.length === 0;
  const pipelineTotal = data?.business.reduce((sum, item) => sum + (item.value || 0), 0) || 0;

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Cockpit</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm">Vue d'ensemble de votre activité</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/inbox">
            <Button variant="outline" size="sm" className="border-gray-200">
              <Inbox className="h-4 w-4 mr-2" />
              Inbox
              {inboxItems.length > 0 && (
                <span className="ml-2 bg-purple-100 text-purple-700 text-xs px-1.5 py-0.5 rounded-full font-medium">
                  {inboxItems.length}
                </span>
              )}
            </Button>
          </Link>
          <Link href="/projects/new">
            <Button size="sm" className="bg-purple-600 hover:bg-purple-700">
              <Plus className="h-4 w-4 mr-2" />
              Nouveau projet
            </Button>
          </Link>
          <Button onClick={fetchDashboard} variant="ghost" size="sm">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">Projets actifs</span>
            <div className="h-8 w-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
              <FolderKanban className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900 dark:text-white">{data?.active_projects || 0}</div>
          <Link href="/projects" className="flex items-center gap-1 mt-1 text-sm text-purple-600 hover:underline">
            <span>Voir les projets</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">En attente validation</span>
            <div className="h-8 w-8 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
              <Clock className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
          <div className="text-3xl font-bold text-orange-500">{data?.pending_validations || 0}</div>
          {(data?.urgencies_count || 0) > 0 && (
            <span className="text-sm text-orange-600 font-medium">{data?.urgencies_count} urgents</span>
          )}
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">Leads chauds</span>
            <div className="h-8 w-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
              <Zap className="h-4 w-4 text-green-600 dark:text-green-400" />
            </div>
          </div>
          <div className="text-3xl font-bold text-green-500">{data?.hot_leads || 0}</div>
          {pipelineTotal > 0 && (
            <div className="flex items-center gap-1 mt-1 text-sm">
              <span className="text-green-600 font-medium">
                {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(pipelineTotal)}
              </span>
              <span className="text-gray-400">potentiel</span>
            </div>
          )}
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-gray-500 dark:text-gray-400 text-sm font-medium">CA du mois</span>
            <div className="h-8 w-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
              <Euro className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(data?.monthly_revenue || 0)}
          </div>
          <Link href="/pipeline" className="flex items-center gap-1 mt-1 text-sm text-blue-600 hover:underline">
            <span>Voir le pipeline</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </motion.div>
      </div>

      {/* Empty State */}
      {allEmpty && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-xl border border-dashed border-gray-200 dark:border-gray-700 p-12"
        >
          <div className="flex flex-col items-center justify-center text-center">
            <Sparkles className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Tout est clair ! 🎉
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
              Aucune action urgente pour le moment. C'est le bon moment pour capturer de nouvelles idées ou avancer sur vos projets.
            </p>
            <div className="flex gap-3">
              <Link href="/inbox">
                <Button className="bg-purple-600 hover:bg-purple-700">
                  <Plus className="h-4 w-4 mr-2" />
                  Capturer une idée
                </Button>
              </Link>
              <Link href="/projects">
                <Button variant="outline">
                  <FolderKanban className="h-4 w-4 mr-2" />
                  Voir les projets
                </Button>
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      {/* Main Grid */}
      {!allEmpty && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Kanban Columns */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* À faire */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden"
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                  <span className="font-semibold text-gray-700 dark:text-gray-200">À faire</span>
                </div>
                <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full font-medium">
                  {data?.todos_count || 0}
                </span>
              </div>
              <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto">
                {hasNoTodos ? (
                  <div className="text-center py-8 text-gray-400">
                    <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Rien pour aujourd'hui</p>
                  </div>
                ) : (
                  data?.todos.slice(0, 5).map((item) => (
                    <Link
                      key={`todo-${item.id}-${item.type}`}
                      href={item.link || '#'}
                      className={`block p-3 rounded-lg border-l-4 ${
                        item.priority === 'high' 
                          ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-500' 
                          : 'bg-gray-50 dark:bg-gray-700/50 border-gray-300 dark:border-gray-600'
                      }`}
                    >
                      <div className="font-medium text-gray-900 dark:text-white text-sm mb-1 truncate">
                        {item.title}
                      </div>
                      {item.client_name && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2 truncate">
                          {item.client_name}
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          item.type === 'followup' 
                            ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' 
                            : item.type === 'validation'
                            ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300'
                            : 'bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                        }`}>
                          {item.type === 'followup' ? 'Relance' : item.type === 'validation' ? 'Validation' : 'Tâche'}
                        </span>
                        {item.priority === 'high' && (
                          <span className="text-xs text-red-500 font-medium">Urgent</span>
                        )}
                      </div>
                    </Link>
                  ))
                )}
                {(data?.todos_count || 0) > 5 && (
                  <Link href="/production" className="block text-center text-sm text-purple-600 hover:underline py-2">
                    Voir les {data?.todos_count} actions →
                  </Link>
                )}
              </div>
            </motion.div>

            {/* Urgences */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden"
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 bg-orange-500 rounded-full"></div>
                  <span className="font-semibold text-gray-700 dark:text-gray-200">Urgences</span>
                </div>
                <span className="text-xs bg-orange-100 dark:bg-orange-900 text-orange-600 dark:text-orange-300 px-2 py-1 rounded-full font-medium">
                  {data?.urgencies_count || 0}
                </span>
              </div>
              <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto">
                {hasNoUrgencies ? (
                  <div className="text-center py-8 text-gray-400">
                    <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Pas d'urgence</p>
                  </div>
                ) : (
                  data?.urgencies.slice(0, 5).map((item) => (
                    <div
                      key={`urgency-${item.id}-${item.type}`}
                      className={`p-3 rounded-lg border-l-4 ${
                        item.severity === 'danger' 
                          ? 'bg-red-50 dark:bg-red-900/20 border-red-500' 
                          : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500'
                      }`}
                    >
                      <div className="font-medium text-gray-900 dark:text-white text-sm mb-1 truncate">
                        {item.title}
                      </div>
                      {item.client_name && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2 truncate">
                          {item.client_name}
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          item.severity === 'danger'
                            ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
                            : 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300'
                        }`}>
                          {item.type === 'blocked_project' ? 'Bloqué' : 'Deadline'}
                        </span>
                        {item.days_remaining !== undefined && (
                          <span className={`text-xs font-medium ${
                            item.days_remaining <= 1 ? 'text-red-500' : 'text-orange-500'
                          }`}>
                            {item.days_remaining <= 0 ? 'Dépassé' : `J-${item.days_remaining}`}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </motion.div>

            {/* Activité */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden"
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                  <span className="font-semibold text-gray-700 dark:text-gray-200">Activité</span>
                </div>
                <Link href="/inbox" className="text-xs text-purple-600 font-medium hover:underline">
                  Voir tout
                </Link>
              </div>
              <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto">
                {inboxItems.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Inbox className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Pas d'activité récente</p>
                  </div>
                ) : (
                  inboxItems.map((item) => (
                    <Link
                      key={item.id}
                      href={`/inbox?item=${item.id}`}
                      className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="h-8 w-8 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center flex-shrink-0">
                        {item.type === 'email' ? (
                          <Mail className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                        ) : item.type === 'file' ? (
                          <FileText className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                        ) : (
                          <Inbox className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-gray-900 dark:text-white truncate">{item.text}</div>
                        <div className="text-xs text-gray-400">
                          {formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: fr })}
                        </div>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </motion.div>
          </div>

          {/* Sidebar */}
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8 }}
            className="space-y-4"
          >
            {/* Pipeline */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900 dark:text-white">Pipeline</h3>
                <span className="text-sm text-green-600 font-medium">
                  {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(pipelineTotal)}
                </span>
              </div>
              <div className="space-y-3">
                {hasNoBusiness ? (
                  <div className="text-center py-6 text-gray-400">
                    <TrendingUp className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Pas de deals actifs</p>
                    <Link href="/pipeline">
                      <Button variant="link" size="sm" className="mt-2 text-purple-600">
                        Créer un deal →
                      </Button>
                    </Link>
                  </div>
                ) : (
                  data?.business.slice(0, 4).map((item) => {
                    const probability = item.status === 'negotiation' ? 80 : item.status === 'proposal' ? 50 : item.status === 'qualified' ? 30 : 20;
                    const bgColor = probability >= 70 ? 'bg-green-50 dark:bg-green-900/20' : probability >= 40 ? 'bg-yellow-50 dark:bg-yellow-900/20' : 'bg-blue-50 dark:bg-blue-900/20';
                    const textColor = probability >= 70 ? 'text-green-600' : probability >= 40 ? 'text-yellow-600' : 'text-blue-600';
                    
                    return (
                      <Link
                        key={`business-${item.id}-${item.type}`}
                        href={`/pipeline?deal=${item.id}`}
                        className={`flex items-center justify-between p-3 ${bgColor} rounded-lg hover:opacity-80 transition-opacity`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm text-gray-900 dark:text-white truncate">{item.title}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {item.client_name} • {probability}%
                          </div>
                        </div>
                        <span className={`font-semibold ${textColor}`}>
                          {item.value ? new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(item.value) : '-'}
                        </span>
                      </Link>
                    );
                  })
                )}
                {(data?.business_count || 0) > 4 && (
                  <Link href="/pipeline" className="block text-center text-sm text-purple-600 hover:underline py-2">
                    Voir tout le pipeline →
                  </Link>
                )}
              </div>
            </div>

            {/* Workspace Info */}
            {workspaces.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Building2 className="h-4 w-4 text-gray-400" />
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm">Workspace</h3>
                </div>
                <div className="space-y-2">
                  {workspaces.map((ws) => (
                    <div key={ws.id} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <span className="text-sm text-gray-900 dark:text-white font-medium">{ws.name}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {ws.members_count} membre{ws.members_count > 1 ? 's' : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-gradient-to-br from-purple-600 to-pink-500 rounded-xl p-4 text-white">
              <h3 className="font-semibold mb-3">Actions rapides</h3>
              <div className="space-y-2">
                <Link href="/inbox" className="flex items-center gap-2 p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                  <Plus className="h-4 w-4" />
                  <span className="text-sm">Capturer une idée</span>
                </Link>
                <Link href="/clients/new" className="flex items-center gap-2 p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                  <Users className="h-4 w-4" />
                  <span className="text-sm">Ajouter un client</span>
                </Link>
                <Link href="/pipeline/new" className="flex items-center gap-2 p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                  <TrendingUp className="h-4 w-4" />
                  <span className="text-sm">Créer un deal</span>
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
