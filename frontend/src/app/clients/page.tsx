"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Plus,
  Search,
  Phone,
  Mail,
  MoreVertical,
  Pencil,
  Trash2,
  Users,
  FolderKanban,
  Euro,
  User,
  Briefcase,
  CreditCard,
  Landmark,
} from "lucide-react";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface ClientContact {
  name: string;
  email?: string;
  phone?: string;
  role?: string;
}

interface Client {
  id: number;
  name: string;
  contacts: ClientContact[];
  // Address fields
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  postal_code?: string | null;
  country?: string | null;
  // Legal info
  siret?: string | null;
  vat_number?: string | null;
  // Banking info
  iban?: string | null;
  iban_masked?: string | null;
  bic?: string | null;
  bank_name?: string | null;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
  active_deals_count?: number;
  active_projects_count?: number;
  total_value?: number;
}

// Helper to get auth headers
const getAuthHeaders = (): Record<string, string> => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function ClientsPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <ClientsContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function ClientsContent() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  
  // Form state
  const [formName, setFormName] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [formContacts, setFormContacts] = useState<ClientContact[]>([
    { name: "", email: "", phone: "", role: "" }
  ]);
  // Address fields
  const [formAddressLine1, setFormAddressLine1] = useState("");
  const [formAddressLine2, setFormAddressLine2] = useState("");
  const [formCity, setFormCity] = useState("");
  const [formPostalCode, setFormPostalCode] = useState("");
  const [formCountry, setFormCountry] = useState("France");
  // Legal info
  const [formSiret, setFormSiret] = useState("");
  const [formVatNumber, setFormVatNumber] = useState("");
  // Banking info
  const [formIban, setFormIban] = useState("");
  const [formBic, setFormBic] = useState("");
  const [formBankName, setFormBankName] = useState("");

  // Fetch clients
  const { data: clients = [], isLoading } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: async () => {
      const res = await workspaceFetch(`/api/v1/agency/clients`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to fetch clients");
      return res.json();
    },
  });

  // Create client mutation
  const createMutation = useMutation({
    mutationFn: async (data: { 
      name: string; 
      contacts: ClientContact[]; 
      address_line1?: string | null;
      address_line2?: string | null;
      city?: string | null;
      postal_code?: string | null;
      country?: string | null;
      siret?: string | null;
      vat_number?: string | null;
      notes: string | null;
    }) => {
      const res = await workspaceFetch(`/api/v1/agency/clients`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error("Failed to create client");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setIsCreateOpen(false);
      resetForm();
    },
  });

  // Update client mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { 
      id: number; 
      data: { 
        name: string; 
        contacts: ClientContact[]; 
        address_line1?: string | null;
        address_line2?: string | null;
        city?: string | null;
        postal_code?: string | null;
        country?: string | null;
        siret?: string | null;
        vat_number?: string | null;
        notes: string | null;
      } 
    }) => {
      const res = await workspaceFetch(`/api/v1/agency/clients/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error("Failed to update client");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setEditingClient(null);
      resetForm();
    },
  });

  // Delete client mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await workspaceFetch(`/api/v1/agency/clients/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to delete client");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });

  const resetForm = () => {
    setFormName("");
    setFormNotes("");
    setFormContacts([{ name: "", email: "", phone: "", role: "" }]);
    setFormAddressLine1("");
    setFormAddressLine2("");
    setFormCity("");
    setFormPostalCode("");
    setFormCountry("France");
    setFormSiret("");
    setFormVatNumber("");
    setFormIban("");
    setFormBic("");
    setFormBankName("");
  };

  const openEditDialog = (client: Client) => {
    setEditingClient(client);
    setFormName(client.name);
    setFormNotes(client.notes || "");
    setFormContacts(client.contacts?.length ? client.contacts : [{ name: "", email: "", phone: "", role: "" }]);
    setFormAddressLine1(client.address_line1 || "");
    setFormAddressLine2(client.address_line2 || "");
    setFormCity(client.city || "");
    setFormPostalCode(client.postal_code || "");
    setFormCountry(client.country || "France");
    setFormSiret(client.siret || "");
    setFormVatNumber(client.vat_number || "");
    setFormIban(""); // IBAN is not pre-filled for security
    setFormBic(client.bic || "");
    setFormBankName(client.bank_name || "");
  };

  const handleSubmit = () => {
    // Filter out empty contacts
    const filteredContacts = formContacts.filter(c => c.name.trim() || c.email?.trim() || c.phone?.trim());
    
    const data = {
      name: formName,
      contacts: filteredContacts,
      address_line1: formAddressLine1 || null,
      address_line2: formAddressLine2 || null,
      city: formCity || null,
      postal_code: formPostalCode || null,
      country: formCountry || "France",
      siret: formSiret || null,
      vat_number: formVatNumber || null,
      iban: formIban || null,
      bic: formBic || null,
      bank_name: formBankName || null,
      notes: formNotes || null,
    };

    if (editingClient) {
      updateMutation.mutate({ id: editingClient.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const addContact = () => {
    setFormContacts([...formContacts, { name: "", email: "", phone: "", role: "" }]);
  };

  const removeContact = (index: number) => {
    setFormContacts(formContacts.filter((_, i) => i !== index));
  };

  const updateContact = (index: number, field: keyof ClientContact, value: string) => {
    const updated = [...formContacts];
    updated[index] = { ...updated[index], [field]: value };
    setFormContacts(updated);
  };

  // Filter clients by search term
  const filteredClients = clients.filter((client) => {
    const searchLower = searchTerm.toLowerCase();
    const nameMatch = client.name.toLowerCase().includes(searchLower);
    const contactMatch = client.contacts?.some(
      c => c.name.toLowerCase().includes(searchLower) || 
           c.email?.toLowerCase().includes(searchLower)
    );
    return nameMatch || contactMatch;
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Get primary contact for display
  const getPrimaryContact = (client: Client): ClientContact | null => {
    return client.contacts?.[0] || null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Building2 className="h-8 w-8 text-primary" />
            Clients
          </h1>
          <p className="text-muted-foreground mt-1">
            Gérez votre portefeuille client
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau client
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Building2 className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{clients.length}</p>
                <p className="text-sm text-muted-foreground">Clients</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <FolderKanban className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {clients.reduce((acc, c) => acc + (c.active_projects_count || 0), 0)}
                </p>
                <p className="text-sm text-muted-foreground">Projets actifs</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Users className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {clients.reduce((acc, c) => acc + (c.active_deals_count || 0), 0)}
                </p>
                <p className="text-sm text-muted-foreground">Deals en cours</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Euro className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {formatCurrency(
                    clients.reduce((acc, c) => acc + (c.total_value || 0), 0)
                  )}
                </p>
                <p className="text-sm text-muted-foreground">Valeur totale</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Rechercher un client..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Clients Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="pt-6">
                <div className="h-6 bg-muted rounded w-3/4 mb-4" />
                <div className="h-4 bg-muted rounded w-1/2 mb-2" />
                <div className="h-4 bg-muted rounded w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredClients.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Building2 className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">Aucun client trouvé</p>
            <p className="text-sm text-muted-foreground mb-4">
              {searchTerm
                ? "Essayez une autre recherche"
                : "Commencez par ajouter votre premier client"}
            </p>
            {!searchTerm && (
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Ajouter un client
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClients.map((client) => {
            const primaryContact = getPrimaryContact(client);
            return (
              <Card
                key={client.id}
                className="hover:shadow-md transition-shadow"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="text-lg font-bold text-primary">
                          {client.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <CardTitle className="text-lg">{client.name}</CardTitle>
                        {primaryContact?.role && (
                          <p className="text-sm text-muted-foreground">
                            {primaryContact.role}
                          </p>
                        )}
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEditDialog(client)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Modifier
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => {
                            if (confirm(`Supprimer le client "${client.name}" ?`)) {
                              deleteMutation.mutate(client.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Supprimer
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {/* Contact info */}
                  {primaryContact && (
                    <div className="space-y-2 text-sm">
                      {primaryContact.name && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <User className="h-4 w-4" />
                          <span>{primaryContact.name}</span>
                        </div>
                      )}
                      {primaryContact.email && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Mail className="h-4 w-4" />
                          <a
                            href={`mailto:${primaryContact.email}`}
                            className="hover:text-primary"
                          >
                            {primaryContact.email}
                          </a>
                        </div>
                      )}
                      {primaryContact.phone && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Phone className="h-4 w-4" />
                          <a
                            href={`tel:${primaryContact.phone}`}
                            className="hover:text-primary"
                          >
                            {primaryContact.phone}
                          </a>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Additional contacts indicator */}
                  {client.contacts && client.contacts.length > 1 && (
                    <p className="text-xs text-muted-foreground">
                      +{client.contacts.length - 1} autres contacts
                    </p>
                  )}

                  {/* Stats badges */}
                  <div className="flex items-center gap-2 pt-2 border-t">
                    <Badge variant="secondary">
                      <FolderKanban className="h-3 w-3 mr-1" />
                      {client.active_projects_count || 0} projets
                    </Badge>
                    <Badge variant="secondary">
                      <Briefcase className="h-3 w-3 mr-1" />
                      {client.active_deals_count || 0} deals
                    </Badge>
                  </div>

                  {/* Total value if available */}
                  {(client.total_value || 0) > 0 && (
                    <div className="text-right">
                      <span className="text-lg font-bold text-green-600">
                        {formatCurrency(client.total_value || 0)}
                      </span>
                      <p className="text-xs text-muted-foreground">
                        Valeur totale deals
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={isCreateOpen || !!editingClient}
        onOpenChange={(open) => {
          if (!open) {
            setIsCreateOpen(false);
            setEditingClient(null);
            resetForm();
          }
        }}
      >
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingClient ? "Modifier le client" : "Nouveau client"}
            </DialogTitle>
            <DialogDescription>
              {editingClient ? "Modifiez les informations du client" : "Ajoutez un nouveau client à votre liste"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Client Name */}
            <div>
              <Label htmlFor="name">Nom du client / Entreprise *</Label>
              <Input
                id="name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Acme Inc."
              />
            </div>

            {/* Contacts */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Contacts</Label>
                <Button type="button" variant="outline" size="sm" onClick={addContact}>
                  <Plus className="h-4 w-4 mr-1" />
                  Ajouter
                </Button>
              </div>

              {formContacts.map((contact, index) => (
                <Card key={index} className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Contact {index + 1}</span>
                      {formContacts.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeContact(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label htmlFor={`contact-name-${index}`}>Nom</Label>
                        <Input
                          id={`contact-name-${index}`}
                          value={contact.name}
                          onChange={(e) => updateContact(index, "name", e.target.value)}
                          placeholder="Dupont"
                        />
                      </div>
                      <div>
                        <Label htmlFor={`contact-role-${index}`}>Prénom</Label>
                        <Input
                          id={`contact-role-${index}`}
                          value={contact.role || ""}
                          onChange={(e) => updateContact(index, "role", e.target.value)}
                          placeholder="Jean"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label htmlFor={`contact-email-${index}`}>Email</Label>
                        <Input
                          id={`contact-email-${index}`}
                          type="email"
                          value={contact.email || ""}
                          onChange={(e) => updateContact(index, "email", e.target.value)}
                          placeholder="jean@acme.com"
                        />
                      </div>
                      <div>
                        <Label htmlFor={`contact-phone-${index}`}>Téléphone</Label>
                        <Input
                          id={`contact-phone-${index}`}
                          type="tel"
                          value={contact.phone || ""}
                          onChange={(e) => updateContact(index, "phone", e.target.value)}
                          placeholder="+33 6 12 34 56 78"
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Notes */}
            <div>
              <Label htmlFor="notes">Notes internes</Label>
              <Textarea
                id="notes"
                value={formNotes}
                onChange={(e) => setFormNotes(e.target.value)}
                placeholder="Notes sur ce client..."
                rows={3}
              />
            </div>

            {/* Address Section */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">Adresse</Label>
              <div>
                <Label htmlFor="address_line1">Adresse ligne 1</Label>
                <Input
                  id="address_line1"
                  value={formAddressLine1}
                  onChange={(e) => setFormAddressLine1(e.target.value)}
                  placeholder="123 rue de la Paix"
                />
              </div>
              <div>
                <Label htmlFor="address_line2">Adresse ligne 2</Label>
                <Input
                  id="address_line2"
                  value={formAddressLine2}
                  onChange={(e) => setFormAddressLine2(e.target.value)}
                  placeholder="Bâtiment A, 2ème étage"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="postal_code">Code postal</Label>
                  <Input
                    id="postal_code"
                    value={formPostalCode}
                    onChange={(e) => setFormPostalCode(e.target.value)}
                    placeholder="75001"
                  />
                </div>
                <div>
                  <Label htmlFor="city">Ville</Label>
                  <Input
                    id="city"
                    value={formCity}
                    onChange={(e) => setFormCity(e.target.value)}
                    placeholder="Paris"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="country">Pays</Label>
                <Input
                  id="country"
                  value={formCountry}
                  onChange={(e) => setFormCountry(e.target.value)}
                  placeholder="France"
                />
              </div>
            </div>

            {/* Legal Info Section */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">Informations légales</Label>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="siret">SIRET</Label>
                  <Input
                    id="siret"
                    value={formSiret}
                    onChange={(e) => setFormSiret(e.target.value)}
                    placeholder="123 456 789 00012"
                  />
                </div>
                <div>
                  <Label htmlFor="vat_number">N° TVA</Label>
                  <Input
                    id="vat_number"
                    value={formVatNumber}
                    onChange={(e) => setFormVatNumber(e.target.value)}
                    placeholder="FR12345678901"
                  />
                </div>
              </div>
            </div>

            {/* Banking Info Section */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Landmark className="h-4 w-4 text-muted-foreground" />
                <Label className="text-base font-semibold">Informations bancaires</Label>
              </div>
              <div>
                <Label htmlFor="iban">IBAN</Label>
                <Input
                  id="iban"
                  value={formIban}
                  onChange={(e) => setFormIban(e.target.value.toUpperCase())}
                  placeholder="FR76 1234 5678 9012 3456 7890 123"
                />
                {editingClient?.iban_masked && !formIban && (
                  <p className="text-xs text-muted-foreground mt-1">
                    <CreditCard className="h-3 w-3 inline mr-1" />
                    IBAN actuel : {editingClient.iban_masked}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  L'IBAN est stocké de manière chiffrée et sécurisée
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="bic">BIC / SWIFT</Label>
                  <Input
                    id="bic"
                    value={formBic}
                    onChange={(e) => setFormBic(e.target.value.toUpperCase())}
                    placeholder="BNPAFRPP"
                  />
                </div>
                <div>
                  <Label htmlFor="bank_name">Nom de la banque</Label>
                  <Input
                    id="bank_name"
                    value={formBankName}
                    onChange={(e) => setFormBankName(e.target.value)}
                    placeholder="BNP Paribas"
                  />
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateOpen(false);
                setEditingClient(null);
                resetForm();
              }}
            >
              Annuler
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={
                !formName ||
                createMutation.isPending ||
                updateMutation.isPending
              }
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Enregistrement..."
                : editingClient
                ? "Enregistrer"
                : "Créer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
