"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";
import { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp,
  Clock,
  Users,
  FileCheck,
  DollarSign,
  ArrowRight,
  Loader2,
  RefreshCw,
  Inbox,
  Calendar,
  FolderOpen,
  Sparkles,
  Plus,
  Building2
} from 'lucide-react';
import Link from 'next/link';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  hot_leads: number | null;
  monthly_revenue: number | null;
}

export default function TodayPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <TodayContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function TodayContent() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [inboxItems, setInboxItems] = useState<InboxItemPreview[]>([]);
  const [workspaces, setWorkspaces] = useState<UserWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      
      // Fetch dashboard data
      const dashboardRes = await workspaceFetch('/api/v1/agency/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!dashboardRes.ok) throw new Error('Failed to fetch dashboard');
      const dashboardData = await dashboardRes.json();
      setData(dashboardData);
      
      // Fetch user's workspaces first
      let userWorkspaces: UserWorkspace[] = [];
      try {
        const wsRes = await workspaceFetch('/api/v1/workspaces', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (wsRes.ok) {
          const wsData = await wsRes.json();
          userWorkspaces = wsData.items || [];
          setWorkspaces(userWorkspaces);
          
          // Update localStorage with valid workspace if needed
          if (userWorkspaces.length > 0) {
            const currentWsId = localStorage.getItem('current_workspace_id');
            const hasAccess = userWorkspaces.some(ws => ws.id.toString() === currentWsId);
            if (!hasAccess) {
              localStorage.setItem('current_workspace_id', userWorkspaces[0].id.toString());
            }
          }
        }
      } catch (e) {
        // Workspaces are optional
      }
      
      // Fetch recent inbox items (preview) - use valid workspace
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
      } catch (e) {
        // Inbox is optional
      }
      
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

  const now = new Date();
  const greeting = now.getHours() < 12 ? 'Bonjour' : now.getHours() < 18 ? 'Bon après-midi' : 'Bonsoir';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
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

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {greeting}
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            {format(now, "EEEE d MMMM yyyy", { locale: fr })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/inbox">
            <Button variant="outline" size="sm">
              <Inbox className="h-4 w-4 mr-2" />
              Inbox
              {inboxItems.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {inboxItems.length}
                </Badge>
              )}
            </Button>
          </Link>
          <Button onClick={fetchDashboard} variant="ghost" size="sm">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Workspace Info */}
      {workspaces.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <Building2 className="h-4 w-4 text-gray-400" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Workspace{workspaces.length > 1 ? 's' : ''} :</span>
          {workspaces.map((ws) => (
            <Badge key={ws.id} variant="secondary" className="text-xs">
              {ws.name}
              <span className="ml-1 text-gray-400">({ws.members_count} membre{ws.members_count > 1 ? 's' : ''})</span>
            </Badge>
          ))}
        </div>
      )}

      {/* Empty State */}
      {allEmpty && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Sparkles className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Tout est clair !
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-center max-w-md mb-6">
              Aucune action urgente pour le moment. C'est le bon moment pour capturer de nouvelles idées ou avancer sur vos projets.
            </p>
            <div className="flex gap-3">
              <Link href="/inbox">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Capturer une idée
                </Button>
              </Link>
              <Link href="/projects">
                <Button variant="outline">
                  <FolderOpen className="h-4 w-4 mr-2" />
                  Voir les projets
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main 3-column grid */}
      {!allEmpty && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Block A: À faire aujourd'hui */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-blue-600" />
                <CardTitle className="text-lg">À faire aujourd'hui</CardTitle>
              </div>
              <CardDescription>
                {data?.todos_count || 0} action{(data?.todos_count || 0) > 1 ? 's' : ''}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
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
                    className="block p-3 rounded-lg border border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                        item.priority === 'high' ? 'bg-red-500' : 
                        item.priority === 'medium' ? 'bg-yellow-500' : 'bg-gray-300'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 dark:text-white truncate">
                          {item.title}
                        </p>
                        {item.client_name && (
                          <p className="text-xs text-gray-500 truncate">
                            {item.client_name}
                          </p>
                        )}
                      </div>
                      <Badge variant={
                        item.type === 'followup' ? 'default' :
                        item.type === 'validation' ? 'secondary' : 'outline'
                      } className="text-[10px]">
                        {item.type === 'followup' ? 'Relance' :
                         item.type === 'validation' ? 'Validation' : 'Tâche'}
                      </Badge>
                    </div>
                  </Link>
                ))
              )}
              {(data?.todos_count || 0) > 5 && (
                <Link href="/production" className="block text-center text-sm text-blue-600 hover:underline py-2">
                  Voir les {data?.todos_count} actions
                </Link>
              )}
            </CardContent>
          </Card>

          {/* Block B: Urgences */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                <CardTitle className="text-lg">Urgences</CardTitle>
              </div>
              <CardDescription>
                Deadlines &lt; 72h et projets bloqués
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {hasNoUrgencies ? (
                <div className="text-center py-8 text-gray-400">
                  <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Pas d'urgence</p>
                </div>
              ) : (
                data?.urgencies.slice(0, 5).map((item) => (
                  <div
                    key={`urgency-${item.id}-${item.type}`}
                    className={`p-3 rounded-lg border transition-colors ${
                      item.severity === 'danger' 
                        ? 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950' 
                        : 'border-orange-200 bg-orange-50 dark:border-orange-900 dark:bg-orange-950'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 p-1 rounded ${
                        item.severity === 'danger' ? 'bg-red-100 dark:bg-red-900' : 'bg-orange-100 dark:bg-orange-900'
                      }`}>
                        {item.type === 'blocked_project' ? (
                          <AlertTriangle className={`h-3 w-3 ${item.severity === 'danger' ? 'text-red-600' : 'text-orange-600'}`} />
                        ) : (
                          <Clock className={`h-3 w-3 ${item.severity === 'danger' ? 'text-red-600' : 'text-orange-600'}`} />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 dark:text-white truncate">
                          {item.title}
                        </p>
                        <p className="text-xs text-gray-500">
                          {item.days_remaining !== undefined && item.days_remaining >= 0 
                            ? `Dans ${item.days_remaining}j` 
                            : item.subtitle}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Block C: Business */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-600" />
                <CardTitle className="text-lg">Business</CardTitle>
              </div>
              <CardDescription>
                Leads chauds & devis en attente
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {hasNoBusiness ? (
                <div className="text-center py-8 text-gray-400">
                  <DollarSign className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Pas de deals actifs</p>
                  <Link href="/pipeline">
                    <Button variant="link" size="sm" className="mt-2">
                      Créer un deal
                    </Button>
                  </Link>
                </div>
              ) : (
                data?.business.slice(0, 5).map((item) => (
                  <Link
                    key={`business-${item.id}-${item.type}`}
                    href={`/pipeline?deal=${item.id}`}
                    className="block p-3 rounded-lg border border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 dark:text-white truncate">
                          {item.title}
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          {item.client_name}
                          {item.days_waiting && item.days_waiting > 0 && (
                            <span className="text-orange-500 ml-1">• {item.days_waiting}j sans réponse</span>
                          )}
                        </p>
                      </div>
                      {item.value && (
                        <span className="text-sm font-semibold text-green-600">
                          {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(item.value)}
                        </span>
                      )}
                    </div>
                  </Link>
                ))
              )}
              {(data?.business_count || 0) > 5 && (
                <Link href="/pipeline" className="block text-center text-sm text-blue-600 hover:underline py-2">
                  Voir le pipeline
                </Link>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Quick Stats */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <FolderOpen className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.active_projects}</p>
                <p className="text-xs text-gray-500">Projets actifs</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                <FileCheck className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.pending_validations}</p>
                <p className="text-xs text-gray-500">Validations</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
                <Users className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.hot_leads ?? "Radar Business"}</p>
                <p className="text-xs text-gray-500">Leads chauds</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                <DollarSign className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {data.monthly_revenue == null ? 'Radar Business' : new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(data.monthly_revenue)}
                </p>
                <p className="text-xs text-gray-500">Ce mois</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Inbox Preview */}
      {inboxItems.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Inbox className="h-5 w-5 text-purple-600" />
                <CardTitle className="text-lg">Inbox</CardTitle>
              </div>
              <Link href="/inbox">
                <Button variant="ghost" size="sm">
                  Voir tout <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {inboxItems.map((item) => (
                <Link
                  key={item.id}
                  href={`/inbox?item=${item.id}`}
                  className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-full text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  <span className="truncate max-w-[200px]">{item.text}</span>
                  <span className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: fr })}
                  </span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
