'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Receipt, Plus, Search, Filter, MoreHorizontal, Eye, Edit2, Trash2,
  FileText, Send, Check, X, Clock, ArrowRight, Building2, User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";

interface QuoteItem {
  id: number;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  line_total: number;
}

interface Client {
  id: number;
  name: string;
  email?: string;
  company_name?: string;
}

interface Quote {
  id: number;
  reference: string;
  title: string;
  description?: string;
  status: 'DRAFT' | 'SENT' | 'ACCEPTED' | 'REJECTED' | 'EXPIRED' | 'INVOICED';
  issue_date: string;
  validity_date?: string;
  client_id?: number;
  client?: Client;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  discount_percent: number;
  discount_amount: number;
  total: number;
  items: QuoteItem[];
  created_at: string;
}

const STATUS_CONFIG = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200', icon: FileText },
  SENT: { label: 'Envoyé', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200', icon: Send },
  ACCEPTED: { label: 'Accepté', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200', icon: Check },
  REJECTED: { label: 'Refusé', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200', icon: X },
  EXPIRED: { label: 'Expiré', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200', icon: Clock },
  INVOICED: { label: 'Facturé', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200', icon: ArrowRight },
};

export default function QuotesPage() {
  const router = useRouter();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  
  // New quote form
  const [newQuote, setNewQuote] = useState({
    title: '',
    description: '',
    client_id: '',
    validity_days: 30,
  });

  const fetchQuotes = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      
      const res = await workspaceFetch(`/api/v1/billing/quotes?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setQuotes(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch quotes', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchClients = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch('/api/v1/billing/clients', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setClients(data);
      }
    } catch (err) {
      console.error('Failed to fetch clients', err);
    }
  };

  useEffect(() => {
    fetchQuotes();
    fetchClients();
  }, [search, statusFilter]);

  const createQuote = async () => {
    if (!newQuote.title) {
      toast.error('Le titre est requis');
      return;
    }
    
    setCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      const validityDate = new Date();
      validityDate.setDate(validityDate.getDate() + newQuote.validity_days);
      
      const res = await workspaceFetch('/api/v1/billing/quotes', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: newQuote.title,
          description: newQuote.description,
          client_id: newQuote.client_id ? parseInt(newQuote.client_id) : null,
          validity_date: validityDate.toISOString().split('T')[0],
        }),
      });
      
      if (res.ok) {
        const quote = await res.json();
        toast.success('Devis créé avec succès');
        setShowCreateDialog(false);
        setNewQuote({ title: '', description: '', client_id: '', validity_days: 30 });
        router.push(`/devis/${quote.id}`);
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur lors de la création');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setCreating(false);
    }
  };

  const updateStatus = async (quoteId: number, status: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/quotes/${quoteId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });
      
      if (res.ok) {
        toast.success('Statut mis à jour');
        fetchQuotes();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    }
  };

  const deleteQuote = async (quoteId: number) => {
    if (!confirm('Supprimer ce devis ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/quotes/${quoteId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        toast.success('Devis supprimé');
        fetchQuotes();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    }
  };

  const convertToInvoice = async (quoteId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + 30);
      
      const res = await workspaceFetch(`/api/v1/billing/quotes/${quoteId}/convert`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          due_date: dueDate.toISOString().split('T')[0],
        }),
      });
      
      if (res.ok) {
        const invoice = await res.json();
        toast.success('Devis converti en facture');
        router.push(`/factures/${invoice.id}`);
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur lors de la conversion');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('fr-FR');
  };

  // Calculate stats
  const stats = {
    draft: quotes.filter(q => q.status === 'DRAFT').length,
    sent: quotes.filter(q => q.status === 'SENT').length,
    accepted: quotes.filter(q => q.status === 'ACCEPTED').length,
    total: quotes.reduce((sum, q) => sum + (q.status === 'ACCEPTED' ? Number(q.total) : 0), 0),
  };

  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Receipt className="h-6 w-6 text-blue-600" />
                Devis
              </h1>
              <p className="text-gray-500 dark:text-gray-400">
                Créez et gérez vos devis clients
              </p>
            </div>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau Devis
            </Button>
          </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Brouillons</p>
                <p className="text-2xl font-bold">{stats.draft}</p>
              </div>
              <FileText className="h-8 w-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Envoyés</p>
                <p className="text-2xl font-bold">{stats.sent}</p>
              </div>
              <Send className="h-8 w-8 text-blue-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Acceptés</p>
                <p className="text-2xl font-bold">{stats.accepted}</p>
              </div>
              <Check className="h-8 w-8 text-green-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total accepté</p>
                <p className="text-2xl font-bold">{formatCurrency(stats.total)}</p>
              </div>
              <Receipt className="h-8 w-8 text-purple-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Rechercher par référence ou titre..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Tous les statuts" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les statuts</SelectItem>
                <SelectItem value="DRAFT">Brouillon</SelectItem>
                <SelectItem value="SENT">Envoyé</SelectItem>
                <SelectItem value="ACCEPTED">Accepté</SelectItem>
                <SelectItem value="REJECTED">Refusé</SelectItem>
                <SelectItem value="EXPIRED">Expiré</SelectItem>
                <SelectItem value="INVOICED">Facturé</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Quotes Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Référence</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Titre</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Montant TTC</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    Chargement...
                  </TableCell>
                </TableRow>
              ) : quotes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                    Aucun devis trouvé
                  </TableCell>
                </TableRow>
              ) : (
                quotes.map((quote) => {
                  const StatusIcon = STATUS_CONFIG[quote.status].icon;
                  return (
                    <TableRow 
                      key={quote.id} 
                      className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => router.push(`/devis/${quote.id}`)}
                    >
                      <TableCell className="font-mono font-medium">
                        {quote.reference}
                      </TableCell>
                      <TableCell>
                        {quote.client ? (
                          <div className="flex items-center gap-2">
                            {quote.client.company_name ? (
                              <Building2 className="h-4 w-4 text-gray-400" />
                            ) : (
                              <User className="h-4 w-4 text-gray-400" />
                            )}
                            <span>{quote.client.company_name || quote.client.name}</span>
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>{quote.title}</TableCell>
                      <TableCell>{formatDate(quote.issue_date)}</TableCell>
                      <TableCell>
                        <Badge className={STATUS_CONFIG[quote.status].color}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {STATUS_CONFIG[quote.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(Number(quote.total))}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); router.push(`/devis/${quote.id}`); }}>
                              <Eye className="h-4 w-4 mr-2" />
                              Voir
                            </DropdownMenuItem>
                            {quote.status === 'DRAFT' && (
                              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); updateStatus(quote.id, 'SENT'); }}>
                                <Send className="h-4 w-4 mr-2" />
                                Marquer envoyé
                              </DropdownMenuItem>
                            )}
                            {quote.status === 'SENT' && (
                              <>
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); updateStatus(quote.id, 'ACCEPTED'); }}>
                                  <Check className="h-4 w-4 mr-2" />
                                  Marquer accepté
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); updateStatus(quote.id, 'REJECTED'); }}>
                                  <X className="h-4 w-4 mr-2" />
                                  Marquer refusé
                                </DropdownMenuItem>
                              </>
                            )}
                            {quote.status === 'ACCEPTED' && (
                              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); convertToInvoice(quote.id); }}>
                                <ArrowRight className="h-4 w-4 mr-2" />
                                Convertir en facture
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {quote.status !== 'INVOICED' && (
                              <DropdownMenuItem 
                                onClick={(e) => { e.stopPropagation(); deleteQuote(quote.id); }}
                                className="text-red-600"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Supprimer
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create Quote Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouveau Devis</DialogTitle>
            <DialogDescription>
              Créez un nouveau devis pour votre client
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Titre *</Label>
              <Input
                placeholder="Ex: Prestation événementielle"
                value={newQuote.title}
                onChange={(e) => setNewQuote({ ...newQuote, title: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Description du devis..."
                value={newQuote.description}
                onChange={(e) => setNewQuote({ ...newQuote, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Client</Label>
              <Select 
                value={newQuote.client_id} 
                onValueChange={(v) => setNewQuote({ ...newQuote, client_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un client" />
                </SelectTrigger>
                <SelectContent>
                  {clients.map((client) => (
                    <SelectItem key={client.id} value={client.id.toString()}>
                      {client.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Validité (jours)</Label>
              <Input
                type="number"
                min={1}
                value={newQuote.validity_days}
                onChange={(e) => setNewQuote({ ...newQuote, validity_days: parseInt(e.target.value) || 30 })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Annuler
            </Button>
            <Button onClick={createQuote} disabled={creating}>
              {creating ? 'Création...' : 'Créer le devis'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
        </div>
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
