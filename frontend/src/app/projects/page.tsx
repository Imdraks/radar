'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  FolderOpen,
  Plus,
  Calendar,
  Users,
  MoreHorizontal,
  Loader2,
  X,
  Search,
  ArrowUpRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  DollarSign,
  Trash2,
  Edit,
  Eye,
} from 'lucide-react';
import Link from 'next/link';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Project {
  id: number;
  name: string;
  status: string;
  client_id: number;
  client_name?: string;
  deadline?: string;
  days_until_deadline?: number;
  is_urgent: boolean;
  progress_percent: number;
  deliverables_count: number;
  deliverables_approved: number;
}

interface Client {
  id: number;
  name: string;
}

interface Deal {
  id: number;
  title: string;
  client_name?: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  active: { label: 'Actif', color: 'text-green-600', bgColor: 'bg-green-50' },
  blocked: { label: 'Bloqué', color: 'text-red-600', bgColor: 'bg-red-50' },
  delivered: { label: 'Livré', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  archived: { label: 'Archivé', color: 'text-gray-600', bgColor: 'bg-gray-50' },
};

export default function ProjectsPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <ProjectsContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function ProjectsContent() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [search, setSearch] = useState('');
  
  // View/Edit/Delete states
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editProject, setEditProject] = useState<{
    name: string;
    status: string;
    client_id: string;
    deadline: string;
    description: string;
  }>({ name: '', status: '', client_id: '', deadline: '', description: '' });

  // Form state
  const [newProject, setNewProject] = useState({
    name: '',
    client_id: '',
    deal_id: '',
    deadline: '',
    budget: '',
    description: '',
  });

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (filterStatus) params.append('status', filterStatus);
      
      const [projectsRes, clientsRes, dealsRes] = await Promise.all([
        workspaceFetch(`/api/v1/agency/projects?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        workspaceFetch('/api/v1/agency/clients', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        workspaceFetch('/api/v1/agency/deals?status=won', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
      ]);
      
      if (projectsRes.ok) {
        setProjects(await projectsRes.json());
      }
      if (clientsRes.ok) {
        setClients(await clientsRes.json());
      }
      if (dealsRes.ok) {
        setDeals(await dealsRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterStatus]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch('/api/v1/agency/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newProject,
          client_id: parseInt(newProject.client_id),
          deal_id: newProject.deal_id ? parseInt(newProject.deal_id) : null,
          budget: newProject.budget ? parseFloat(newProject.budget) : null,
          deadline: newProject.deadline || null,
        }),
      });
      
      if (response.ok) {
        setShowAddModal(false);
        setNewProject({ name: '', client_id: '', deal_id: '', deadline: '', budget: '', description: '' });
        await fetchData();
      }
    } catch (err) {
      console.error('Failed to create project:', err);
    }
  };

  const handleViewProject = (project: Project) => {
    setSelectedProject(project);
    setShowViewModal(true);
  };

  const handleEditProject = (project: Project) => {
    setSelectedProject(project);
    setEditProject({
      name: project.name,
      status: project.status,
      client_id: project.client_id?.toString() || '',
      deadline: project.deadline || '',
      description: '',
    });
    setShowEditModal(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedProject) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch(`/api/v1/agency/projects/${selectedProject.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...editProject,
          client_id: editProject.client_id ? parseInt(editProject.client_id) : null,
          deadline: editProject.deadline || null,
        }),
      });
      if (response.ok) {
        setShowEditModal(false);
        setSelectedProject(null);
        await fetchData();
      }
    } catch (err) {
      console.error('Failed to update project:', err);
    }
  };

  const handleDeleteProject = async (project: Project) => {
    if (!confirm(`Supprimer le projet "${project.name}" ?`)) return;
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/agency/projects/${project.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      await fetchData();
    } catch (err) {
      console.error('Failed to delete project:', err);
    }
  };

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.client_name && p.client_name.toLowerCase().includes(search.toLowerCase()))
  );

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projets</h1>
          <p className="text-gray-600">{projects.length} projets</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          <Plus className="h-4 w-4" />
          Nouveau projet
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un projet..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          />
        </div>
        
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
        >
          <option value="">Tous les statuts</option>
          <option value="active">Actifs</option>
          <option value="blocked">Bloqués</option>
          <option value="delivered">Livrés</option>
          <option value="archived">Archivés</option>
        </select>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProjects.map((project) => {
          const statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.active;
          
          return (
            <div
              key={project.id}
              onClick={() => router.push(`/projects/${project.id}`)}
              className={`bg-white rounded-xl border p-5 hover:shadow-md transition-shadow cursor-pointer ${
                project.is_urgent ? 'border-amber-300' : 'border-gray-100'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-1 rounded-full ${statusConfig.bgColor} ${statusConfig.color}`}>
                    {statusConfig.label}
                  </span>
                  {project.is_urgent && (
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                  )}
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button 
                      className="p-1 hover:bg-gray-100 rounded"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreHorizontal className="h-4 w-4 text-gray-400" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                    <DropdownMenuItem onClick={() => handleViewProject(project)}>
                      <Eye className="h-4 w-4 mr-2" />
                      Voir détails
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleEditProject(project)}>
                      <Edit className="h-4 w-4 mr-2" />
                      Modifier
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-red-600" onClick={() => handleDeleteProject(project)}>
                      <Trash2 className="h-4 w-4 mr-2" />
                      Supprimer
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              
              <h3 className="font-semibold text-gray-900 mb-1">{project.name}</h3>
              
              {project.client_name && (
                <p className="text-sm text-gray-500 mb-3 flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {project.client_name}
                </p>
              )}
              
              {/* Progress Bar */}
              <div className="mb-4">
                {project.deliverables_count === 0 ? (
                  <>
                    <div className="text-sm text-gray-500 mb-1">Aucun livrable défini</div>
                    <div className="h-2 bg-gray-200 rounded-full opacity-50" />
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-600">Progression</span>
                      <span className={`font-medium ${
                        project.progress_percent === 100 ? 'text-green-600' :
                        project.progress_percent >= 70 ? 'text-orange-500' :
                        project.progress_percent >= 30 ? 'text-blue-600' :
                        'text-gray-600'
                      }`}>
                        {project.progress_percent}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          project.progress_percent === 100 ? 'bg-green-500' :
                          project.progress_percent >= 70 ? 'bg-orange-500' :
                          project.progress_percent >= 30 ? 'bg-blue-500' :
                          'bg-gray-400'
                        }`}
                        style={{ width: `${project.progress_percent}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {project.deliverables_approved} / {project.deliverables_count} livrables validés
                    </p>
                  </>
                )}
              </div>
              
              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                {project.days_until_deadline !== undefined && project.days_until_deadline !== null ? (
                  <span className={`text-xs flex items-center gap-1 ${
                    project.days_until_deadline < 0 ? 'text-red-500' :
                    project.days_until_deadline <= 3 ? 'text-amber-500' : 
                    'text-gray-500'
                  }`}>
                    <Calendar className="h-3 w-3" />
                    {project.days_until_deadline < 0 
                      ? `${Math.abs(project.days_until_deadline)}j en retard`
                      : `${project.days_until_deadline}j restants`
                    }
                  </span>
                ) : (
                  <span className="text-xs text-gray-400">Pas de deadline</span>
                )}
                
                <Link
                  href={`/production?project_id=${project.id}`}
                  className="text-sm text-purple-600 hover:text-purple-700 flex items-center gap-1"
                >
                  Voir <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          );
        })}
        
        {filteredProjects.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            <FolderOpen className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Aucun projet trouvé</p>
          </div>
        )}
      </div>

      {/* Add Project Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Nouveau projet</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateProject} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom du projet *
                </label>
                <input
                  type="text"
                  required
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Ex: Campagne Summer 2025"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client (facultatif)
                </label>
                <select
                  value={newProject.client_id}
                  onChange={(e) => setNewProject({ ...newProject, client_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="">Production interne</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Deal associé (optionnel)
                </label>
                <select
                  value={newProject.deal_id}
                  onChange={(e) => setNewProject({ ...newProject, deal_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="">Aucun deal</option>
                  {deals.map((deal) => (
                    <option key={deal.id} value={deal.id}>
                      {deal.title} {deal.client_name && `- ${deal.client_name}`}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Deadline
                  </label>
                  <input
                    type="date"
                    value={newProject.deadline}
                    onChange={(e) => setNewProject({ ...newProject, deadline: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Budget (€)
                  </label>
                  <input
                    type="number"
                    value={newProject.budget}
                    onChange={(e) => setNewProject({ ...newProject, budget: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="5000"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  rows={3}
                  placeholder="Description du projet..."
                />
              </div>
              
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  Créer le projet
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Project Modal */}
      {showViewModal && selectedProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Détails du projet</h2>
              <button
                onClick={() => { setShowViewModal(false); setSelectedProject(null); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500">Nom</label>
                <p className="text-gray-900 font-medium">{selectedProject.name}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Client</label>
                  <p className="text-gray-900">{selectedProject.client_name || '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Statut</label>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    STATUS_CONFIG[selectedProject.status]?.bgColor || 'bg-gray-100'
                  } ${STATUS_CONFIG[selectedProject.status]?.color || 'text-gray-600'}`}>
                    {STATUS_CONFIG[selectedProject.status]?.label || selectedProject.status}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Deadline</label>
                  <p className="text-gray-900">
                    {selectedProject.deadline 
                      ? new Date(selectedProject.deadline).toLocaleDateString('fr-FR')
                      : 'Non définie'}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Progression</label>
                  {selectedProject.deliverables_count === 0 ? (
                    <p className="text-gray-500 italic">Aucun livrable</p>
                  ) : (
                    <p className={`font-medium ${
                      selectedProject.progress_percent === 100 ? 'text-green-600' :
                      selectedProject.progress_percent >= 70 ? 'text-orange-500' :
                      selectedProject.progress_percent >= 30 ? 'text-blue-600' :
                      'text-gray-600'
                    }`}>
                      {selectedProject.progress_percent}%
                    </p>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-500">Livrables</label>
                {selectedProject.deliverables_count === 0 ? (
                  <p className="text-gray-500 italic">Aucun livrable défini</p>
                ) : (
                  <p className="text-gray-900">
                    {selectedProject.deliverables_approved} / {selectedProject.deliverables_count} validés
                  </p>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => { setShowViewModal(false); handleEditProject(selectedProject); }}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Modifier
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Project Modal */}
      {showEditModal && selectedProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Modifier le projet</h2>
              <button
                onClick={() => { setShowEditModal(false); setSelectedProject(null); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nom *</label>
                <input
                  type="text"
                  value={editProject.name}
                  onChange={(e) => setEditProject({ ...editProject, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
                  <select
                    value={editProject.status}
                    onChange={(e) => setEditProject({ ...editProject, status: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="active">Actif</option>
                    <option value="blocked">Bloqué</option>
                    <option value="delivered">Livré</option>
                    <option value="archived">Archivé</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Deadline</label>
                  <input
                    type="date"
                    value={editProject.deadline}
                    onChange={(e) => setEditProject({ ...editProject, deadline: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
                <select
                  value={editProject.client_id}
                  onChange={(e) => setEditProject({ ...editProject, client_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="">Aucun client</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>{client.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => { setShowEditModal(false); setSelectedProject(null); }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Annuler
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
