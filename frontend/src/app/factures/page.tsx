'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  FileCheck, Plus, Search, MoreHorizontal, Eye, Edit2, Trash2,
  FileText, Send, Check, AlertTriangle, Clock, CreditCard, Building2, User, DollarSign
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

interface InvoiceItem {
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

interface Invoice {
  id: number;
  reference: string;
  title: string;
  description?: string;
  status: 'DRAFT' | 'SENT' | 'PAID' | 'PARTIAL' | 'OVERDUE' | 'CANCELLED';
  issue_date: string;
  due_date?: string;
  paid_date?: string;
  client_id?: number;
  client?: Client;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  discount_percent: number;
  discount_amount: number;
  total: number;
  amount_paid: number;
  payment_method?: string;
  items: InvoiceItem[];
  created_at: string;
}

const STATUS_CONFIG = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200', icon: FileText },
  SENT: { label: 'Envoyée', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200', icon: Send },
  PAID: { label: 'Payée', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200', icon: Check },
  PARTIAL: { label: 'Partielle', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200', icon: Clock },
  OVERDUE: { label: 'En retard', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200', icon: AlertTriangle },
  CANCELLED: { label: 'Annulée', color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400', icon: Trash2 },
};

export default function InvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [creating, setCreating] = useState(false);
  
  // New invoice form
  const [newInvoice, setNewInvoice] = useState({
    title: '',
    description: '',
    client_id: '',
    due_days: 30,
  });

  // Payment form
  const [payment, setPayment] = useState({
    amount: '',
    method: 'BANK_TRANSFER',
  });

  const fetchInvoices = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      
      const res = await workspaceFetch(`/api/v1/billing/invoices?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setInvoices(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch invoices', err);
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
    fetchInvoices();
    fetchClients();
  }, [search, statusFilter]);

  const createInvoice = async () => {
    if (!newInvoice.title) {
      toast.error('Le titre est requis');
      return;
    }
    
    setCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + newInvoice.due_days);
      
      const res = await workspaceFetch('/api/v1/billing/invoices', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: newInvoice.title,
          description: newInvoice.description,
          client_id: newInvoice.client_id ? parseInt(newInvoice.client_id) : null,
          due_date: dueDate.toISOString().split('T')[0],
        }),
      });
      
      if (res.ok) {
        const invoice = await res.json();
        toast.success('Facture créée avec succès');
        setShowCreateDialog(false);
        setNewInvoice({ title: '', description: '', client_id: '', due_days: 30 });
        router.push(`/factures/${invoice.id}`);
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

  const updateStatus = async (invoiceId: number, status: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });
      
      if (res.ok) {
        toast.success('Statut mis à jour');
        fetchInvoices();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    }
  };

  const recordPayment = async () => {
    if (!selectedInvoice || !payment.amount) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${selectedInvoice.id}/payment`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount_paid: parseFloat(payment.amount),
          payment_method: payment.method,
        }),
      });
      
      if (res.ok) {
        toast.success('Paiement enregistré');
        setShowPaymentDialog(false);
        setPayment({ amount: '', method: 'BANK_TRANSFER' });
        setSelectedInvoice(null);
        fetchInvoices();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    }
  };

  const deleteInvoice = async (invoiceId: number) => {
    if (!confirm('Supprimer cette facture ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (res.ok) {
        toast.success('Facture supprimée');
        fetchInvoices();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
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
    draft: invoices.filter(i => i.status === 'DRAFT').length,
    sent: invoices.filter(i => i.status === 'SENT').length,
    paid: invoices.filter(i => i.status === 'PAID').length,
    overdue: invoices.filter(i => i.status === 'OVERDUE').length,
    totalPaid: invoices.reduce((sum, i) => sum + Number(i.amount_paid), 0),
    totalPending: invoices
      .filter(i => ['SENT', 'PARTIAL', 'OVERDUE'].includes(i.status))
      .reduce((sum, i) => sum + (Number(i.total) - Number(i.amount_paid)), 0),
  };

  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <FileCheck className="h-6 w-6 text-green-600" />
            Factures
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Gérez vos factures et suivez les paiements
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouvelle Facture
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Payées</p>
                <p className="text-2xl font-bold text-green-600">{stats.paid}</p>
              </div>
              <Check className="h-8 w-8 text-green-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">En attente</p>
                <p className="text-2xl font-bold text-blue-600">{stats.sent}</p>
              </div>
              <Send className="h-8 w-8 text-blue-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">En retard</p>
                <p className="text-2xl font-bold text-red-600">{stats.overdue}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-red-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total encaissé</p>
                <p className="text-2xl font-bold text-green-600">{formatCurrency(stats.totalPaid)}</p>
              </div>
              <DollarSign className="h-8 w-8 text-green-400" />
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
                <SelectItem value="SENT">Envoyée</SelectItem>
                <SelectItem value="PAID">Payée</SelectItem>
                <SelectItem value="PARTIAL">Partielle</SelectItem>
                <SelectItem value="OVERDUE">En retard</SelectItem>
                <SelectItem value="CANCELLED">Annulée</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Invoices Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Référence</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Titre</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Échéance</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Montant</TableHead>
                <TableHead className="text-right">Payé</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    Chargement...
                  </TableCell>
                </TableRow>
              ) : invoices.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                    Aucune facture trouvée
                  </TableCell>
                </TableRow>
              ) : (
                invoices.map((invoice) => {
                  const StatusIcon = STATUS_CONFIG[invoice.status].icon;
                  return (
                    <TableRow 
                      key={invoice.id} 
                      className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                      onClick={() => router.push(`/factures/${invoice.id}`)}
                    >
                      <TableCell className="font-mono font-medium">
                        {invoice.reference}
                      </TableCell>
                      <TableCell>
                        {invoice.client ? (
                          <div className="flex items-center gap-2">
                            {invoice.client.company_name ? (
                              <Building2 className="h-4 w-4 text-gray-400" />
                            ) : (
                              <User className="h-4 w-4 text-gray-400" />
                            )}
                            <span>{invoice.client.company_name || invoice.client.name}</span>
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>{invoice.title}</TableCell>
                      <TableCell>{formatDate(invoice.issue_date)}</TableCell>
                      <TableCell>
                        {invoice.due_date ? formatDate(invoice.due_date) : '-'}
                      </TableCell>
                      <TableCell>
                        <Badge className={STATUS_CONFIG[invoice.status].color}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {STATUS_CONFIG[invoice.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(Number(invoice.total))}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={Number(invoice.amount_paid) >= Number(invoice.total) ? 'text-green-600' : ''}>
                          {formatCurrency(Number(invoice.amount_paid))}
                        </span>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); router.push(`/factures/${invoice.id}`); }}>
                              <Eye className="h-4 w-4 mr-2" />
                              Voir
                            </DropdownMenuItem>
                            {invoice.status === 'DRAFT' && (
                              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); updateStatus(invoice.id, 'SENT'); }}>
                                <Send className="h-4 w-4 mr-2" />
                                Marquer envoyée
                              </DropdownMenuItem>
                            )}
                            {['SENT', 'PARTIAL', 'OVERDUE'].includes(invoice.status) && (
                              <DropdownMenuItem onClick={(e) => { 
                                e.stopPropagation(); 
                                setSelectedInvoice(invoice);
                                setPayment({ amount: String(Number(invoice.total) - Number(invoice.amount_paid)), method: 'BANK_TRANSFER' });
                                setShowPaymentDialog(true);
                              }}>
                                <CreditCard className="h-4 w-4 mr-2" />
                                Enregistrer paiement
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {invoice.status !== 'PAID' && (
                              <DropdownMenuItem 
                                onClick={(e) => { e.stopPropagation(); deleteInvoice(invoice.id); }}
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

      {/* Create Invoice Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvelle Facture</DialogTitle>
            <DialogDescription>
              Créez une nouvelle facture
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Titre *</Label>
              <Input
                placeholder="Ex: Prestation événementielle"
                value={newInvoice.title}
                onChange={(e) => setNewInvoice({ ...newInvoice, title: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Description de la facture..."
                value={newInvoice.description}
                onChange={(e) => setNewInvoice({ ...newInvoice, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Client</Label>
              <Select 
                value={newInvoice.client_id} 
                onValueChange={(v) => setNewInvoice({ ...newInvoice, client_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un client" />
                </SelectTrigger>
                <SelectContent>
                  {clients.map((client) => (
                    <SelectItem key={client.id} value={client.id.toString()}>
                      {client.company_name || client.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Échéance (jours)</Label>
              <Input
                type="number"
                min={1}
                value={newInvoice.due_days}
                onChange={(e) => setNewInvoice({ ...newInvoice, due_days: parseInt(e.target.value) || 30 })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Annuler
            </Button>
            <Button onClick={createInvoice} disabled={creating}>
              {creating ? 'Création...' : 'Créer la facture'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment Dialog */}
      <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Enregistrer un paiement</DialogTitle>
            <DialogDescription>
              {selectedInvoice && `Facture ${selectedInvoice.reference} - Reste à payer: ${formatCurrency(Number(selectedInvoice.total) - Number(selectedInvoice.amount_paid))}`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Montant payé *</Label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={payment.amount}
                onChange={(e) => setPayment({ ...payment, amount: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Mode de paiement</Label>
              <Select 
                value={payment.method} 
                onValueChange={(v) => setPayment({ ...payment, method: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BANK_TRANSFER">Virement bancaire</SelectItem>
                  <SelectItem value="CHECK">Chèque</SelectItem>
                  <SelectItem value="CARD">Carte bancaire</SelectItem>
                  <SelectItem value="CASH">Espèces</SelectItem>
                  <SelectItem value="OTHER">Autre</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPaymentDialog(false)}>
              Annuler
            </Button>
            <Button onClick={recordPayment} className="bg-green-600 hover:bg-green-700">
              Enregistrer le paiement
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
        </div>
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
