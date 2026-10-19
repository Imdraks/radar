'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  User,
  MoreHorizontal,
  Loader2,
  X,
  ExternalLink,
  Eye,
  Trash2,
  Edit,
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

interface ProductionItem {
  id: number;
  name: string;
  type?: string;
  status: string;
  due_date?: string;
  days_until_due?: number;
  is_urgent: boolean;
  project_id: number;
  project_name: string;
  client_name: string;
  has_pending_approval: boolean;
  link?: string;
}

interface ProductionColumn {
  status: string;
  label: string;
  items: ProductionItem[];
  count: number;
}

interface ProductionData {
  columns: ProductionColumn[];
  total_items: number;
}

interface Project {
  id: number;
  name: string;
  client_name?: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-400',
  to_review: 'bg-purple-500',
  changes_requested: 'bg-amber-500',
  approved: 'bg-green-500',
  delivered: 'bg-blue-500',
};

export default function ProductionPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <ProductionContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function ProductionContent() {
  const [data, setData] = useState<ProductionData | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [draggedItem, setDraggedItem] = useState<ProductionItem | null>(null);
  
  // View/Edit/Delete states
  const [selectedItem, setSelectedItem] = useState<ProductionItem | null>(null);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editItem, setEditItem] = useState<{
    name: string;
    type: string;
    due_date: string;
    link: string;
  }>({ name: '', type: '', due_date: '', link: '' });

  // Form state
  const [newDeliverable, setNewDeliverable] = useState({
    name: '',
    project_id: '',
    type: '',
    due_date: '',
    link: '',
    notes: '',
  });

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const [productionRes, projectsRes] = await Promise.all([
        workspaceFetch('/api/v1/agency/production', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        workspaceFetch('/api/v1/agency/projects', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
      ]);
      
      if (productionRes.ok) {
        setData(await productionRes.json());
      }
      if (projectsRes.ok) {
        setProjects(await projectsRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch production:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDragStart = (item: ProductionItem) => {
    setDraggedItem(item);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (newStatus: string) => {
    if (!draggedItem || draggedItem.status === newStatus) {
      setDraggedItem(null);
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/agency/deliverables/${draggedItem.id}/status?status=${newStatus}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      await fetchData();
    } catch (err) {
      console.error('Failed to update status:', err);
    } finally {
      setDraggedItem(null);
    }
  };

  const handleCreateDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch('/api/v1/agency/deliverables', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newDeliverable,
          project_id: parseInt(newDeliverable.project_id),
          due_date: newDeliverable.due_date || null,
        }),
      });
      
      if (response.ok) {
        setShowAddModal(false);
        setNewDeliverable({ name: '', project_id: '', type: '', due_date: '', link: '', notes: '' });
        await fetchData();
      }
    } catch (err) {
      console.error('Failed to create deliverable:', err);
    }
  };

  const requestApproval = async (deliverableId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch('/api/v1/agency/approvals', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ deliverable_id: deliverableId }),
      });
      
      await fetchData();
    } catch (err) {
      console.error('Failed to request approval:', err);
    }
  };

  const handleViewItem = (item: ProductionItem) => {
    setSelectedItem(item);
    setShowViewModal(true);
  };

  const handleEditItem = (item: ProductionItem) => {
    setSelectedItem(item);
    setEditItem({
      name: item.name,
      type: item.type || '',
      due_date: item.due_date || '',
      link: item.link || '',
    });
    setShowEditModal(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedItem) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch(`/api/v1/agency/deliverables/${selectedItem.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...editItem,
          due_date: editItem.due_date || null,
        }),
      });
      if (response.ok) {
        setShowEditModal(false);
        setSelectedItem(null);
        await fetchData();
      }
    } catch (err) {
      console.error('Failed to update deliverable:', err);
    }
  };

  const handleDeleteItem = async (item: ProductionItem) => {
    if (!confirm(`Supprimer le livrable "${item.name}" ?`)) return;
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/agency/deliverables/${item.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      await fetchData();
    } catch (err) {
      console.error('Failed to delete deliverable:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Production</h1>
            <p className="text-gray-600">
              {data?.total_items || 0} livrables en cours
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            <Plus className="h-4 w-4" />
            Nouveau livrable
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto p-6">
        <div className="flex gap-4 h-full min-w-max">
          {data?.columns.map((column) => (
            <div
              key={column.status}
              className="w-80 flex flex-col bg-gray-50 rounded-xl"
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(column.status)}
            >
              {/* Column Header */}
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${STATUS_COLORS[column.status]}`} />
                  <h3 className="font-semibold text-gray-900">{column.label}</h3>
                  <span className="text-sm text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                    {column.count}
                  </span>
                </div>
              </div>

              {/* Cards */}
              <div className="flex-1 p-3 space-y-3 overflow-y-auto max-h-[calc(100vh-280px)]">
                {column.items.map((item) => (
                  <div
                    key={item.id}
                    draggable
                    onDragStart={() => handleDragStart(item)}
                    className={`bg-white rounded-lg shadow-sm border p-4 cursor-move hover:shadow-md transition-shadow ${
                      item.is_urgent ? 'border-amber-300' : 'border-gray-100'
                    } ${draggedItem?.id === item.id ? 'opacity-50' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-gray-900 line-clamp-2">{item.name}</h4>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="p-1 hover:bg-gray-100 rounded">
                            <MoreHorizontal className="h-4 w-4 text-gray-400" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleViewItem(item)}>
                            <Eye className="h-4 w-4 mr-2" />
                            Voir détails
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleEditItem(item)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Modifier
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-red-600" onClick={() => handleDeleteItem(item)}>
                            <Trash2 className="h-4 w-4 mr-2" />
                            Supprimer
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-2">
                      {item.project_name}
                    </p>
                    
                    <p className="text-xs text-gray-400 mb-3">
                      {item.client_name}
                    </p>
                    
                    {item.type && (
                      <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded mb-2 inline-block">
                        {item.type}
                      </span>
                    )}
                    
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                      {item.days_until_due !== undefined && item.days_until_due !== null ? (
                        <span className={`text-xs flex items-center gap-1 ${
                          item.days_until_due < 0 ? 'text-red-500' :
                          item.days_until_due <= 3 ? 'text-amber-500' : 
                          'text-gray-500'
                        }`}>
                          <Clock className="h-3 w-3" />
                          {item.days_until_due < 0 
                            ? `${Math.abs(item.days_until_due)}j en retard`
                            : `${item.days_until_due}j restants`
                          }
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                      
                      <div className="flex items-center gap-1">
                        {item.link && (
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        )}
                        
                        {item.has_pending_approval && (
                          <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-600 rounded flex items-center gap-1">
                            <Eye className="h-3 w-3" />
                            En attente
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Quick actions */}
                    {column.status === 'draft' && !item.has_pending_approval && (
                      <button
                        onClick={() => requestApproval(item.id)}
                        className="mt-3 w-full text-sm py-1.5 bg-purple-50 text-purple-600 rounded hover:bg-purple-100 transition-colors"
                      >
                        Demander validation
                      </button>
                    )}
                  </div>
                ))}
                
                {column.items.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Aucun livrable</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Deliverable Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Nouveau livrable</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateDeliverable} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom *
                </label>
                <input
                  type="text"
                  required
                  value={newDeliverable.name}
                  onChange={(e) => setNewDeliverable({ ...newDeliverable, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Ex: Vidéo teaser 30s"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Projet *
                </label>
                <select
                  required
                  value={newDeliverable.project_id}
                  onChange={(e) => setNewDeliverable({ ...newDeliverable, project_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="">Sélectionner un projet</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name} {project.client_name && `- ${project.client_name}`}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type
                  </label>
                  <select
                    value={newDeliverable.type}
                    onChange={(e) => setNewDeliverable({ ...newDeliverable, type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="">Sélectionner</option>
                    <option value="video">Vidéo</option>
                    <option value="photo">Photo</option>
                    <option value="design">Design</option>
                    <option value="document">Document</option>
                    <option value="audio">Audio</option>
                    <option value="other">Autre</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date limite
                  </label>
                  <input
                    type="date"
                    value={newDeliverable.due_date}
                    onChange={(e) => setNewDeliverable({ ...newDeliverable, due_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Lien (Google Drive, Figma, etc.)
                </label>
                <input
                  type="url"
                  value={newDeliverable.link}
                  onChange={(e) => setNewDeliverable({ ...newDeliverable, link: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="https://..."
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
                  Créer le livrable
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Deliverable Modal */}
      {showViewModal && selectedItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Détails du livrable</h2>
              <button
                onClick={() => { setShowViewModal(false); setSelectedItem(null); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500">Nom</label>
                <p className="text-gray-900 font-medium">{selectedItem.name}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Projet</label>
                  <p className="text-gray-900">{selectedItem.project_name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Client</label>
                  <p className="text-gray-900">{selectedItem.client_name}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Type</label>
                  <p className="text-gray-900">{selectedItem.type || '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Statut</label>
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${STATUS_COLORS[selectedItem.status]}`} />
                    <span className="text-gray-900">{selectedItem.status}</span>
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-500">Date limite</label>
                <p className="text-gray-900">
                  {selectedItem.due_date 
                    ? new Date(selectedItem.due_date).toLocaleDateString('fr-FR')
                    : 'Non définie'}
                </p>
              </div>
              {selectedItem.link && (
                <div>
                  <label className="block text-sm font-medium text-gray-500">Lien</label>
                  <a 
                    href={selectedItem.link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-purple-600 hover:underline flex items-center gap-1"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Ouvrir le lien
                  </a>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => { setShowViewModal(false); handleEditItem(selectedItem); }}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Modifier
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Deliverable Modal */}
      {showEditModal && selectedItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Modifier le livrable</h2>
              <button
                onClick={() => { setShowEditModal(false); setSelectedItem(null); }}
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
                  value={editItem.name}
                  onChange={(e) => setEditItem({ ...editItem, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={editItem.type}
                    onChange={(e) => setEditItem({ ...editItem, type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="">Sélectionner</option>
                    <option value="video">Vidéo</option>
                    <option value="photo">Photo</option>
                    <option value="design">Design</option>
                    <option value="document">Document</option>
                    <option value="audio">Audio</option>
                    <option value="other">Autre</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date limite</label>
                  <input
                    type="date"
                    value={editItem.due_date}
                    onChange={(e) => setEditItem({ ...editItem, due_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Lien</label>
                <input
                  type="url"
                  value={editItem.link}
                  onChange={(e) => setEditItem({ ...editItem, link: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="https://..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => { setShowEditModal(false); setSelectedItem(null); }}
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
