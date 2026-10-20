'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { 
  FileCheck, ArrowLeft, Edit2, Trash2, Plus, Save, Send, Check, X,
  Building2, User, Calendar, Clock, CreditCard, AlertTriangle, DollarSign, Pencil,
  Download, Loader2, Eye, Cloud, ExternalLink
} from 'lucide-react';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableFooter,
} from '@/components/ui/table';
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
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';

interface InvoiceItem {
  id: number;
  position: number;
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
  phone?: string;
  company_name?: string;
  address_line1?: string;
  city?: string;
  postal_code?: string;
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
  terms?: string;
  notes?: string;
  items: InvoiceItem[];
  source_quote_id?: number;
  created_at: string;
}

const STATUS_CONFIG = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200' },
  SENT: { label: 'Envoyée', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  PAID: { label: 'Payée', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  PARTIAL: { label: 'Partielle', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' },
  OVERDUE: { label: 'En retard', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
  CANCELLED: { label: 'Annulée', color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
};

const PAYMENT_METHODS = {
  BANK_TRANSFER: 'Virement bancaire',
  CHECK: 'Chèque',
  CARD: 'Carte bancaire',
  CASH: 'Espèces',
  OTHER: 'Autre',
};

export default function InvoiceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const invoiceId = params.id as string;
  
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showAddItemDialog, setShowAddItemDialog] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [showEditItemDialog, setShowEditItemDialog] = useState(false);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [savingToDrive, setSavingToDrive] = useState(false);
  const [driveLink, setDriveLink] = useState<string | null>(null);
  
  // Edit form
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    client_id: '',
    due_date: '',
    tax_rate: '20',
    discount_percent: '0',
    terms: '',
    notes: '',
  });

  // Original form values (cached when entering edit mode)
  const [originalForm, setOriginalForm] = useState({
    title: '',
    description: '',
    client_id: '',
    due_date: '',
    tax_rate: '20',
    discount_percent: '0',
    terms: '',
    notes: '',
  });

  // Local items management (for temporary edits before saving)
  const [localItems, setLocalItems] = useState<InvoiceItem[]>([]);
  const [originalItems, setOriginalItems] = useState<InvoiceItem[]>([]);
  const [nextTempId, setNextTempId] = useState(-1); // IDs négatifs pour les nouveaux items

  // Edit item form
  const [editItem, setEditItem] = useState({
    description: '',
    quantity: '1',
    unit: 'unité',
    unit_price: '',
  });

  // New item form
  const [newItem, setNewItem] = useState({
    description: '',
    quantity: '1',
    unit: 'unité',
    unit_price: '',
  });

  // Payment form
  const [payment, setPayment] = useState({
    amount: '',
    method: 'BANK_TRANSFER',
  });

  const fetchInvoice = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setInvoice(data);
        setEditForm({
          title: data.title || '',
          description: data.description || '',
          client_id: data.client_id ? String(data.client_id) : '',
          due_date: data.due_date || '',
          tax_rate: String(data.tax_rate || 20),
          discount_percent: String(data.discount_percent || 0),
          terms: data.terms || '',
          notes: data.notes || '',
        });
        // Initialiser les items locaux
        setLocalItems(data.items || []);
        setOriginalItems(data.items || []);
      } else {
        toast.error('Facture non trouvée');
        router.push('/factures');
      }
    } catch (err) {
      console.error('Failed to fetch invoice', err);
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
    fetchInvoice();
    fetchClients();
  }, [invoiceId]);

  const saveInvoice = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      
      // 1. Sauvegarder les infos de la facture
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: editForm.title,
          description: editForm.description || null,
          client_id: editForm.client_id ? parseInt(editForm.client_id) : null,
          due_date: editForm.due_date || null,
          tax_rate: parseFloat(editForm.tax_rate),
          discount_percent: parseFloat(editForm.discount_percent),
          terms: editForm.terms || null,
          notes: editForm.notes || null,
        }),
      });
      
      if (!res.ok) {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
        setSaving(false);
        return;
      }
      
      // 2. Synchroniser les items
      // Items à supprimer (dans originalItems mais pas dans localItems)
      const itemsToDelete = originalItems.filter(
        orig => !localItems.find(local => local.id === orig.id)
      );
      
      // Items à ajouter (ID négatif = nouveau)
      const itemsToAdd = localItems.filter(item => item.id < 0);
      
      // Items à modifier (ID positif et différent de l'original)
      const itemsToUpdate = localItems.filter(item => {
        if (item.id < 0) return false;
        const orig = originalItems.find(o => o.id === item.id);
        if (!orig) return false;
        return (
          orig.description !== item.description ||
          orig.quantity !== item.quantity ||
          orig.unit !== item.unit ||
          orig.unit_price !== item.unit_price
        );
      });
      
      // Supprimer les items
      for (const item of itemsToDelete) {
        await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}/items/${item.id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` },
        });
      }
      
      // Ajouter les nouveaux items
      for (const item of itemsToAdd) {
        await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}/items`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            description: item.description,
            quantity: item.quantity,
            unit: item.unit,
            unit_price: item.unit_price,
            position: item.position,
          }),
        });
      }
      
      // Modifier les items existants
      for (const item of itemsToUpdate) {
        await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}/items/${item.id}`, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            description: item.description,
            quantity: item.quantity,
            unit: item.unit,
            unit_price: item.unit_price,
          }),
        });
      }
      
      toast.success('Facture mise à jour');
      setEditing(false);
      fetchInvoice();
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setSaving(false);
    }
  };

  const addItem = () => {
    if (!newItem.description || !newItem.unit_price) {
      toast.error('Description et prix requis');
      return;
    }
    
    // Ajouter localement avec un ID temporaire négatif
    const tempItem: InvoiceItem = {
      id: nextTempId,
      position: localItems.length,
      description: newItem.description,
      quantity: parseFloat(newItem.quantity),
      unit: newItem.unit,
      unit_price: parseFloat(newItem.unit_price),
      line_total: parseFloat(newItem.quantity) * parseFloat(newItem.unit_price),
    };
    
    setLocalItems([...localItems, tempItem]);
    setNextTempId(nextTempId - 1);
    setShowAddItemDialog(false);
    setNewItem({ description: '', quantity: '1', unit: 'unité', unit_price: '' });
    toast.success('Ligne ajoutée (non enregistrée)');
  };

  const deleteItem = (itemId: number) => {
    // Supprimer localement
    setLocalItems(localItems.filter(item => item.id !== itemId));
    toast.success('Ligne supprimée (non enregistrée)');
  };

  const openEditItemDialog = (item: InvoiceItem) => {
    setEditingItemId(item.id);
    setEditItem({
      description: item.description,
      quantity: String(item.quantity),
      unit: item.unit,
      unit_price: String(item.unit_price),
    });
    setShowEditItemDialog(true);
  };

  const updateItem = () => {
    if (!editingItemId || !editItem.description || !editItem.unit_price) {
      toast.error('Description et prix requis');
      return;
    }
    
    // Modifier localement
    setLocalItems(localItems.map(item => {
      if (item.id === editingItemId) {
        return {
          ...item,
          description: editItem.description,
          quantity: parseFloat(editItem.quantity),
          unit: editItem.unit,
          unit_price: parseFloat(editItem.unit_price),
          line_total: parseFloat(editItem.quantity) * parseFloat(editItem.unit_price),
        };
      }
      return item;
    }));
    
    setShowEditItemDialog(false);
    setEditingItemId(null);
    toast.success('Ligne modifiée (non enregistrée)');
  };

  const updateStatus = async (status: string) => {
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
        fetchInvoice();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    }
  };

  const recordPayment = async () => {
    if (!payment.amount) {
      toast.error('Montant requis');
      return;
    }
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}/payment`, {
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
        fetchInvoice();
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

  if (loading) {
    return (
      <ProtectedRoute>
        <AppLayoutWithOnboarding>
          <div className="p-6 flex items-center justify-center">
            <div className="text-gray-500">Chargement...</div>
          </div>
        </AppLayoutWithOnboarding>
      </ProtectedRoute>
    );
  }

  if (!invoice) {
    return null;
  }

  const isEditable = invoice.status !== 'PAID' && invoice.status !== 'CANCELLED';
  const remaining = Number(invoice.total) - Number(invoice.amount_paid);
  const paymentProgress = Number(invoice.total) > 0 
    ? (Number(invoice.amount_paid) / Number(invoice.total)) * 100 
    : 0;

  const generatePdf = async () => {
    setGeneratingPdf(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}/pdf`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        if (pdfUrl) window.URL.revokeObjectURL(pdfUrl);
        const url = window.URL.createObjectURL(blob);
        setPdfUrl(url);
        toast.success('PDF généré avec succès');
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur de génération du PDF');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const viewPdf = () => {
    if (pdfUrl) window.open(pdfUrl, '_blank');
  };

  const saveToDrive = async () => {
    setSavingToDrive(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/billing/invoices/${invoiceId}/pdf/drive`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDriveLink(data.web_view_link);
        if (pdfUrl) {
          window.URL.revokeObjectURL(pdfUrl);
          setPdfUrl(null);
        }
        toast.success('PDF sauvegardé sur Google Drive');
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Erreur de sauvegarde sur Drive');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setSavingToDrive(false);
    }
  };

  const openDriveLink = () => {
    if (driveLink) window.open(driveLink, '_blank');
  };

  const downloadPdf = () => {
    if (pdfUrl) {
      const a = document.createElement('a');
      a.href = pdfUrl;
      a.download = `${invoice?.reference || 'facture'}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  return (
    <>
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push('/factures')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {invoice.reference}
              </h1>
              <Badge className={STATUS_CONFIG[invoice.status].color}>
                {STATUS_CONFIG[invoice.status].label}
              </Badge>
            </div>
            <p className="text-gray-500 dark:text-gray-400">{invoice.title}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={generatePdf} disabled={generatingPdf}>
            {generatingPdf ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
            {generatingPdf ? 'Génération...' : 'PDF'}
          </Button>
          {pdfUrl && (
            <>
              <Button variant="outline" onClick={viewPdf}>
                <Eye className="h-4 w-4 mr-2" />
                Voir PDF
              </Button>
              <Button variant="outline" onClick={downloadPdf}>
                <Download className="h-4 w-4 mr-2" />
                Télécharger
              </Button>
              <Button variant="outline" onClick={saveToDrive} disabled={savingToDrive}>
                <Cloud className="h-4 w-4 mr-2" />
                {savingToDrive ? 'Sauvegarde...' : 'Sauver sur Drive'}
              </Button>
            </>
          )}
          {driveLink && (
            <Button variant="outline" onClick={openDriveLink}>
              <ExternalLink className="h-4 w-4 mr-2" />
              Voir sur Drive
            </Button>
          )}
          {invoice.status === 'DRAFT' && (
            <Button variant="outline" onClick={() => updateStatus('SENT')}>
              <Send className="h-4 w-4 mr-2" />
              Marquer envoyée
            </Button>
          )}
          {['SENT', 'PARTIAL', 'OVERDUE'].includes(invoice.status) && (
            <Button 
              onClick={() => {
                setPayment({ amount: String(remaining), method: 'BANK_TRANSFER' });
                setShowPaymentDialog(true);
              }}
              className="bg-green-600 hover:bg-green-700"
            >
              <CreditCard className="h-4 w-4 mr-2" />
              Enregistrer paiement
            </Button>
          )}
          {isEditable && (
            <Button variant="outline" onClick={() => {
              if (!editing) {
                // Sauvegarder l'état original quand on entre en mode édition
                setOriginalForm({ ...editForm });
                setOriginalItems([...localItems]);
              }
              setEditing(!editing);
            }}>
              <Edit2 className="h-4 w-4 mr-2" />
              {editing ? 'Quitter' : 'Modifier'}
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Info */}
          {editing ? (
            <Card>
              <CardHeader>
                <CardTitle>Informations de la facture</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Titre</Label>
                    <Input
                      value={editForm.title}
                      onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Client</Label>
                    <Select 
                      value={editForm.client_id} 
                      onValueChange={(v) => setEditForm({ ...editForm, client_id: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner" />
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
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Date d'échéance</Label>
                    <Input
                      type="date"
                      value={editForm.due_date}
                      onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>TVA (%)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={editForm.tax_rate}
                      onChange={(e) => setEditForm({ ...editForm, tax_rate: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Remise (%)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={editForm.discount_percent}
                      onChange={(e) => setEditForm({ ...editForm, discount_percent: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Conditions</Label>
                  <Textarea
                    value={editForm.terms}
                    onChange={(e) => setEditForm({ ...editForm, terms: e.target.value })}
                    placeholder="Conditions de paiement..."
                  />
                </div>
                <div className="space-y-2">
                  <Label>Notes internes</Label>
                  <Textarea
                    value={editForm.notes}
                    onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                  />
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{invoice.title}</CardTitle>
                  <div className="text-sm text-gray-500 space-x-4">
                    <span>
                      <Calendar className="h-4 w-4 inline mr-1" />
                      {formatDate(invoice.issue_date)}
                    </span>
                    {invoice.due_date && (
                      <span className={invoice.status === 'OVERDUE' ? 'text-red-600' : ''}>
                        <Clock className="h-4 w-4 inline mr-1" />
                        Échéance: {formatDate(invoice.due_date)}
                      </span>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {invoice.description && (
                  <p className="text-gray-600 dark:text-gray-300 mb-4">{invoice.description}</p>
                )}
                {invoice.terms && (
                  <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Conditions:</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{invoice.terms}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Items Table */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Lignes de la facture</CardTitle>
                {editing && (
                  <Button size="sm" onClick={() => setShowAddItemDialog(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Ajouter une ligne
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50%]">Description</TableHead>
                    <TableHead className="text-right">Qté</TableHead>
                    <TableHead>Unité</TableHead>
                    <TableHead className="text-right">Prix unit.</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    {editing && <TableHead className="w-[100px]"></TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {localItems.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={editing ? 6 : 5} className="text-center py-8 text-gray-500">
                        Aucune ligne. Ajoutez des prestations à la facture.
                      </TableCell>
                    </TableRow>
                  ) : (
                    localItems.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.description}</TableCell>
                        <TableCell className="text-right">{item.quantity}</TableCell>
                        <TableCell>{item.unit}</TableCell>
                        <TableCell className="text-right">{formatCurrency(Number(item.unit_price))}</TableCell>
                        <TableCell className="text-right font-medium">{formatCurrency(Number(item.line_total))}</TableCell>
                        {editing && (
                          <TableCell>
                            <div className="flex gap-1">
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => openEditItemDialog(item)}
                                className="text-blue-600 hover:text-blue-700"
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => deleteItem(item.id)}
                                className="text-red-600 hover:text-red-700"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  )}
                </TableBody>
                {localItems.length > 0 && (
                  <TableFooter>
                    {(() => {
                      // Calculer les totaux locaux
                      const localSubtotal = localItems.reduce((sum, item) => sum + (Number(item.line_total) || 0), 0);
                      const taxRate = editing ? (parseFloat(editForm.tax_rate) || 0) : (invoice.tax_rate || 0);
                      const discountPercent = editing ? (parseFloat(editForm.discount_percent) || 0) : (invoice.discount_percent || 0);
                      const discountAmount = localSubtotal * (discountPercent / 100);
                      const taxableAmount = localSubtotal - discountAmount;
                      const taxAmount = taxableAmount * (taxRate / 100);
                      const total = taxableAmount + taxAmount;
                      
                      return (
                        <>
                          <TableRow>
                            <TableCell colSpan={editing ? 4 : 3} className="text-right font-medium">
                              Sous-total HT
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              {formatCurrency(localSubtotal)}
                            </TableCell>
                            {editing && <TableCell />}
                          </TableRow>
                          {discountAmount > 0 && (
                            <TableRow>
                              <TableCell colSpan={editing ? 4 : 3} className="text-right text-red-600">
                                Remise ({discountPercent}%)
                              </TableCell>
                              <TableCell className="text-right text-red-600">
                                -{formatCurrency(discountAmount)}
                              </TableCell>
                              {editing && <TableCell />}
                            </TableRow>
                          )}
                          <TableRow>
                            <TableCell colSpan={editing ? 4 : 3} className="text-right">
                              TVA ({taxRate}%)
                            </TableCell>
                            <TableCell className="text-right">
                              {formatCurrency(taxAmount)}
                            </TableCell>
                            {editing && <TableCell />}
                          </TableRow>
                          <TableRow className="bg-gray-50 dark:bg-gray-800">
                            <TableCell colSpan={editing ? 4 : 3} className="text-right font-bold text-lg">
                              Total TTC
                            </TableCell>
                            <TableCell className="text-right font-bold text-lg">
                              {formatCurrency(total)}
                            </TableCell>
                            {editing && <TableCell />}
                          </TableRow>
                        </>
                      );
                    })()}
                  </TableFooter>
                )}
              </Table>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Payment Status Card */}
          <Card className={invoice.status === 'PAID' ? 'border-green-200 bg-green-50 dark:bg-green-950' : ''}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Paiement
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Progression</span>
                  <span>{paymentProgress.toFixed(0)}%</span>
                </div>
                <Progress value={paymentProgress} className="h-2" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Montant total</span>
                  <span className="font-medium">{formatCurrency(Number(invoice.total))}</span>
                </div>
                <div className="flex justify-between text-green-600">
                  <span>Payé</span>
                  <span className="font-medium">{formatCurrency(Number(invoice.amount_paid))}</span>
                </div>
                {remaining > 0 && (
                  <div className="flex justify-between text-orange-600">
                    <span>Reste à payer</span>
                    <span className="font-medium">{formatCurrency(remaining)}</span>
                  </div>
                )}
              </div>
              {invoice.payment_method && (
                <div className="pt-2 border-t">
                  <span className="text-sm text-gray-500">Mode de paiement: </span>
                  <span className="text-sm">{PAYMENT_METHODS[invoice.payment_method as keyof typeof PAYMENT_METHODS]}</span>
                </div>
              )}
              {invoice.paid_date && (
                <div>
                  <span className="text-sm text-gray-500">Date de paiement: </span>
                  <span className="text-sm">{formatDate(invoice.paid_date)}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Client Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {invoice.client?.company_name ? (
                  <Building2 className="h-5 w-5" />
                ) : (
                  <User className="h-5 w-5" />
                )}
                Client
              </CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.client ? (
                <div className="space-y-2">
                  <p className="font-medium">{invoice.client.company_name || invoice.client.name}</p>
                  {invoice.client.company_name && (
                    <p className="text-sm text-gray-500">{invoice.client.name}</p>
                  )}
                  {invoice.client.email && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">{invoice.client.email}</p>
                  )}
                  {invoice.client.phone && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">{invoice.client.phone}</p>
                  )}
                  {invoice.client.address_line1 && (
                    <div className="text-sm text-gray-600 dark:text-gray-400 pt-2 border-t">
                      <p>{invoice.client.address_line1}</p>
                      <p>{invoice.client.postal_code} {invoice.client.city}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500">Aucun client sélectionné</p>
              )}
            </CardContent>
          </Card>

          {/* Overdue Warning */}
          {invoice.status === 'OVERDUE' && (
            <Card className="border-red-200 bg-red-50 dark:bg-red-950">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Facture en retard</span>
                </div>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  L'échéance était le {invoice.due_date && formatDate(invoice.due_date)}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Source Quote */}
          {invoice.source_quote_id && (
            <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                  <FileCheck className="h-5 w-5" />
                  <span>Créée depuis un devis</span>
                </div>
                <Button 
                  variant="link" 
                  className="text-blue-700 p-0 mt-2"
                  onClick={() => router.push(`/devis/${invoice.source_quote_id}`)}
                >
                  Voir le devis →
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Add Item Dialog */}
      <Dialog open={showAddItemDialog} onOpenChange={setShowAddItemDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ajouter une ligne</DialogTitle>
            <DialogDescription>
              Ajoutez une prestation ou un produit à la facture
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Description *</Label>
              <Textarea
                placeholder="Description de la prestation..."
                value={newItem.description}
                onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Quantité</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newItem.quantity}
                  onChange={(e) => setNewItem({ ...newItem, quantity: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Unité</Label>
                <Select 
                  value={newItem.unit} 
                  onValueChange={(v) => setNewItem({ ...newItem, unit: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unité">Unité</SelectItem>
                    <SelectItem value="heure">Heure</SelectItem>
                    <SelectItem value="jour">Jour</SelectItem>
                    <SelectItem value="forfait">Forfait</SelectItem>
                    <SelectItem value="mois">Mois</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Prix unitaire HT *</Label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={newItem.unit_price}
                  onChange={(e) => setNewItem({ ...newItem, unit_price: e.target.value })}
                />
              </div>
            </div>
            {newItem.quantity && newItem.unit_price && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex justify-between text-sm">
                  <span>Total ligne HT</span>
                  <span className="font-medium">
                    {formatCurrency(parseFloat(newItem.quantity) * parseFloat(newItem.unit_price))}
                  </span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddItemDialog(false)}>
              Annuler
            </Button>
            <Button onClick={addItem}>
              <Plus className="h-4 w-4 mr-2" />
              Ajouter
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
              Reste à payer: {formatCurrency(remaining)}
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
              <Check className="h-4 w-4 mr-2" />
              Enregistrer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Item Dialog */}
      <Dialog open={showEditItemDialog} onOpenChange={setShowEditItemDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modifier la ligne</DialogTitle>
            <DialogDescription>
              Modifiez les détails de cette ligne
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Description *</Label>
              <Textarea
                placeholder="Description de la prestation..."
                value={editItem.description}
                onChange={(e) => setEditItem({ ...editItem, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Quantité</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={editItem.quantity}
                  onChange={(e) => setEditItem({ ...editItem, quantity: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Unité</Label>
                <Select 
                  value={editItem.unit} 
                  onValueChange={(v) => setEditItem({ ...editItem, unit: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unité">Unité</SelectItem>
                    <SelectItem value="heure">Heure</SelectItem>
                    <SelectItem value="jour">Jour</SelectItem>
                    <SelectItem value="forfait">Forfait</SelectItem>
                    <SelectItem value="mois">Mois</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Prix unitaire HT *</Label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={editItem.unit_price}
                  onChange={(e) => setEditItem({ ...editItem, unit_price: e.target.value })}
                />
              </div>
            </div>
            {editItem.quantity && editItem.unit_price && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex justify-between text-sm">
                  <span>Total ligne HT</span>
                  <span className="font-medium">
                    {formatCurrency(parseFloat(editItem.quantity) * parseFloat(editItem.unit_price))}
                  </span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditItemDialog(false)}>
              Annuler
            </Button>
            <Button onClick={updateItem}>
              <Save className="h-4 w-4 mr-2" />
              Enregistrer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
        </div>
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
    
    {/* Popup de sauvegarde flottant - complètement en dehors de tout layout */}
    {(() => {
      // Détecter si les items ont changé
      const itemsChanged = () => {
        if (localItems.length !== originalItems.length) return true;
        for (const local of localItems) {
          const orig = originalItems.find(o => o.id === local.id);
          if (!orig) return true;
          if (
            orig.description !== local.description ||
            orig.quantity !== local.quantity ||
            orig.unit !== local.unit ||
            orig.unit_price !== local.unit_price
          ) return true;
        }
        return false;
      };
      
      // Détecter si des modifications ont été faites
      const hasChanges = editing && (
        editForm.title !== originalForm.title ||
        editForm.description !== originalForm.description ||
        editForm.client_id !== originalForm.client_id ||
        editForm.due_date !== originalForm.due_date ||
        editForm.tax_rate !== originalForm.tax_rate ||
        editForm.discount_percent !== originalForm.discount_percent ||
        editForm.terms !== originalForm.terms ||
        editForm.notes !== originalForm.notes ||
        itemsChanged()
      );
      
      if (!hasChanges) return null;
      
      return (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999]" style={{ position: 'fixed' }}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl px-5 py-3 flex items-center gap-3" style={{ border: '2px solid #E5E7EB' }}>
            <button
              onClick={() => {
                setEditForm({ ...originalForm });
                setLocalItems([...originalItems]);
              }}
              className="flex items-center gap-2 px-5 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium"
            >
              <X className="h-4 w-4" />
              Annuler
            </button>
            <button
              onClick={saveInvoice}
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </div>
        </div>
      );
    })()}
    </>
  );
}
