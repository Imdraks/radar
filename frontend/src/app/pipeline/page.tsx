'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import {
  DollarSign,
  Plus,
  ChevronDown,
  Calendar,
  User,
  Tag,
  MoreHorizontal,
  Loader2,
  Search,
  X,
  Clock,
  Trash2,
  Edit,
  Eye,
} from 'lucide-react';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

interface Deal {
  id: number;
  title: string;
  status: string;
  value?: number;
  client_id: number;
  client_name?: string;
  next_action_date?: string;
  last_contact_at?: string;
  days_since_contact?: number;
  owner_name?: string;
  tags: string[];
}

interface PipelineColumn {
  status: string;
  label: string;
  deals: Deal[];
  count: number;
  total_value: number;
}

interface PipelineData {
  columns: PipelineColumn[];
  total_deals: number;
  total_value: number;
}

interface Client {
  id: number;
  name: string;
}

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-500',
  contacted: 'bg-purple-500',
  quote_sent: 'bg-amber-500',
  negotiation: 'bg-orange-500',
  won: 'bg-green-500',
  lost: 'bg-red-500',
};

export default function PipelinePage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <PipelineContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function PipelineContent() {
  const [data, setData] = useState<PipelineData | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null);
  const [draggedDeal, setDraggedDeal] = useState<Deal | null>(null);
  
  // View/Edit/Delete states
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Form state
  const [newDeal, setNewDeal] = useState({
    title: '',
    client_id: '',
    value: '',
    status: 'new',
    source: '',
    notes: '',
  });
  
  // Edit form state
  const [editDeal, setEditDeal] = useState({
    title: '',
    client_id: '',
    value: '',
    source: '',
    notes: '',
  });

  const fetchPipeline = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const [pipelineRes, clientsRes] = await Promise.all([
        workspaceFetch('/api/v1/agency/pipeline', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        workspaceFetch('/api/v1/agency/clients', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
      ]);
      
      if (pipelineRes.ok) {
        setData(await pipelineRes.json());
      }
      if (clientsRes.ok) {
        setClients(await clientsRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch pipeline:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipeline();
  }, []);

  const handleDragStart = (deal: Deal) => {
    setDraggedDeal(deal);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (newStatus: string) => {
    if (!draggedDeal || draggedDeal.status === newStatus) {
      setDraggedDeal(null);
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/agency/deals/${draggedDeal.id}/status?status=${newStatus}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      // Refresh pipeline
      await fetchPipeline();
    } catch (err) {
      console.error('Failed to update deal status:', err);
    } finally {
      setDraggedDeal(null);
    }
  };

  const handleCreateDeal = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch('/api/v1/agency/deals', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newDeal,
          client_id: parseInt(newDeal.client_id),
          value: newDeal.value ? parseFloat(newDeal.value) : null,
        }),
      });
      
      if (response.ok) {
        setShowAddModal(false);
        setNewDeal({ title: '', client_id: '', value: '', status: 'new', source: '', notes: '' });
        await fetchPipeline();
      }
    } catch (err) {
      console.error('Failed to create deal:', err);
    }
  };

  // View deal details
  const handleViewDeal = (deal: Deal) => {
    setSelectedDeal(deal);
    setShowViewModal(true);
  };

  // Open edit modal
  const handleEditDeal = (deal: Deal) => {
    setSelectedDeal(deal);
    setEditDeal({
      title: deal.title,
      client_id: deal.client_id.toString(),
      value: deal.value?.toString() || '',
      source: '',
      notes: '',
    });
    setShowEditModal(true);
  };

  // Save edited deal
  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeal) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch(`/api/v1/agency/deals/${selectedDeal.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: editDeal.title,
          client_id: parseInt(editDeal.client_id),
          value: editDeal.value ? parseFloat(editDeal.value) : null,
        }),
      });
      
      if (response.ok) {
        setShowEditModal(false);
        setSelectedDeal(null);
        await fetchPipeline();
      }
    } catch (err) {
      console.error('Failed to update deal:', err);
    }
  };

  // Delete deal
  const handleDeleteDeal = async (deal: Deal) => {
    if (!confirm(`Supprimer le deal "${deal.title}" ?`)) return;
    
    setIsDeleting(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch(`/api/v1/agency/deals/${deal.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (response.ok) {
        await fetchPipeline();
      }
    } catch (err) {
      console.error('Failed to delete deal:', err);
    } finally {
      setIsDeleting(false);
    }
  };

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
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Pipeline Commercial</h1>
            <p className="text-gray-600">
              {data?.total_deals || 0} deals • {formatCurrency(data?.total_value || 0)} total
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            <Plus className="h-4 w-4" />
            Nouveau deal
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
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${STATUS_COLORS[column.status]}`} />
                    <h3 className="font-semibold text-gray-900">{column.label}</h3>
                    <span className="text-sm text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                      {column.count}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-green-600">
                    {formatCurrency(column.total_value)}
                  </span>
                </div>
              </div>

              {/* Cards */}
              <div className="flex-1 p-3 space-y-3 overflow-y-auto max-h-[calc(100vh-280px)]">
                {column.deals.map((deal) => (
                  <div
                    key={deal.id}
                    draggable
                    onDragStart={() => handleDragStart(deal)}
                    className={`bg-white rounded-lg shadow-sm border border-gray-100 p-4 cursor-move hover:shadow-md transition-shadow ${
                      draggedDeal?.id === deal.id ? 'opacity-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-gray-900 line-clamp-2">{deal.title}</h4>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="p-1 hover:bg-gray-100 rounded">
                            <MoreHorizontal className="h-4 w-4 text-gray-400" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleViewDeal(deal)}>
                            <Eye className="h-4 w-4 mr-2" />
                            Voir détails
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleEditDeal(deal)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Modifier
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleDeleteDeal(deal)} className="text-red-600">
                            <Trash2 className="h-4 w-4 mr-2" />
                            Supprimer
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    
                    {deal.client_name && (
                      <p className="text-sm text-gray-600 mb-2 flex items-center gap-1">
                        <User className="h-3 w-3" />
                        {deal.client_name}
                      </p>
                    )}
                    
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                      {deal.value ? (
                        <span className="text-sm font-semibold text-green-600 flex items-center gap-1">
                          <DollarSign className="h-3 w-3" />
                          {formatCurrency(deal.value)}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                      
                      {deal.days_since_contact !== undefined && deal.days_since_contact !== null && (
                        <span className={`text-xs flex items-center gap-1 ${
                          deal.days_since_contact > 7 ? 'text-red-500' : 
                          deal.days_since_contact > 3 ? 'text-amber-500' : 
                          'text-gray-500'
                        }`}>
                          <Clock className="h-3 w-3" />
                          {deal.days_since_contact}j
                        </span>
                      )}
                    </div>
                    
                    {deal.tags && deal.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {deal.tags.slice(0, 3).map((tag, i) => (
                          <span
                            key={i}
                            className="text-xs px-2 py-0.5 bg-purple-50 text-purple-600 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                
                {column.deals.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <p className="text-sm">Aucun deal</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Deal Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Nouveau deal</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateDeal} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Titre *
                </label>
                <input
                  type="text"
                  required
                  value={newDeal.title}
                  onChange={(e) => setNewDeal({ ...newDeal, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Ex: Campagne Summer 2025"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client *
                </label>
                <select
                  required
                  value={newDeal.client_id}
                  onChange={(e) => setNewDeal({ ...newDeal, client_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="">Sélectionner un client</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Valeur (€)
                  </label>
                  <input
                    type="number"
                    value={newDeal.value}
                    onChange={(e) => setNewDeal({ ...newDeal, value: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="5000"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source
                  </label>
                  <input
                    type="text"
                    value={newDeal.source}
                    onChange={(e) => setNewDeal({ ...newDeal, source: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    placeholder="Ex: Bouche à oreille"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={newDeal.notes}
                  onChange={(e) => setNewDeal({ ...newDeal, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  rows={3}
                  placeholder="Notes additionnelles..."
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
                  Créer le deal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Deal Modal */}
      {showViewModal && selectedDeal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Détails du deal</h2>
              <button
                onClick={() => { setShowViewModal(false); setSelectedDeal(null); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Titre</label>
                <p className="text-gray-900 font-medium">{selectedDeal.title}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Client</label>
                  <p className="text-gray-900">{selectedDeal.client_name || '—'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Valeur</label>
                  <p className="text-gray-900 font-semibold text-green-600">
                    {selectedDeal.value ? formatCurrency(selectedDeal.value) : '—'}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Statut</label>
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium text-white ${STATUS_COLORS[selectedDeal.status]}`}>
                    {selectedDeal.status}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Dernier contact</label>
                  <p className="text-gray-900">
                    {selectedDeal.days_since_contact !== undefined ? `Il y a ${selectedDeal.days_since_contact}j` : '—'}
                  </p>
                </div>
              </div>
              
              {selectedDeal.tags && selectedDeal.tags.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Tags</label>
                  <div className="flex flex-wrap gap-1">
                    {selectedDeal.tags.map((tag, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 bg-purple-50 text-purple-600 rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => { setShowViewModal(false); setSelectedDeal(null); }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Fermer
              </button>
              <button
                onClick={() => { setShowViewModal(false); handleEditDeal(selectedDeal); }}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Modifier
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Deal Modal */}
      {showEditModal && selectedDeal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Modifier le deal</h2>
              <button
                onClick={() => { setShowEditModal(false); setSelectedDeal(null); }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleSaveEdit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Titre *</label>
                <input
                  type="text"
                  required
                  value={editDeal.title}
                  onChange={(e) => setEditDeal({ ...editDeal, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client *</label>
                <select
                  required
                  value={editDeal.client_id}
                  onChange={(e) => setEditDeal({ ...editDeal, client_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="">Sélectionner un client</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>{client.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valeur (€)</label>
                <input
                  type="number"
                  value={editDeal.value}
                  onChange={(e) => setEditDeal({ ...editDeal, value: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="5000"
                />
              </div>
              
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => { setShowEditModal(false); setSelectedDeal(null); }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  Sauvegarder
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
