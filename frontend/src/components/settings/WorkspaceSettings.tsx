"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useEffect, useState, useCallback } from "react";
import {
  Building2,
  Users,
  Landmark,
  Plus,
  Trash2,
  Crown,
  Shield,
  Eye,
  RefreshCw,
  UserPlus,
  MoreVertical,
  Save,
  AlertTriangle,
  Loader2,
  Settings2,
  ChevronRight,
  Lock,
  Mail,
  KeyRound,
  Copy,
  Check,
  Clock,
  MailPlus,
  CheckCircle2,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/auth";
import { useBankingStore } from "@/store/bankingStore";
import { BankStatusBadge, SyncStatusBadge } from "@/components/banking";
import { ExternalLink, Unplug } from "lucide-react";

// ============================================================================
// TYPES
// ============================================================================

interface WorkspaceMember {
  id: number;
  user_id: number;
  role: "admin" | "member" | "viewer";
  user_name: string | null;
  user_email: string | null;
  user_avatar: string | null;
  invited_at: string | null;
  accepted_at: string | null;
}

interface WorkspaceDetail {
  id: number;
  name: string;
  owner_user_id: number;
  owner_name: string | null;
  drive_root_folder_id: string | null;
  drive_url: string | null;
  templates_folder_id: string | null;
  calendar_id: string | null;
  settings: Record<string, any> | null;
  members_count: number;
  members: WorkspaceMember[];
  created_at: string;
  updated_at: string;
  // Company / Legal info
  legal_name: string | null;
  legal_address: string | null;
  legal_city: string | null;
  legal_postal_code: string | null;
  legal_country: string | null;
  legal_phone: string | null;
  legal_email: string | null;
  siret: string | null;
  vat_number: string | null;
  forme_juridique: string | null;
  capital_social: string | null;
  rcs_city: string | null;
  tva_franchise: boolean | null;
}

interface InviteEmail {
  id: number;
  workspace_id: number;
  email: string;
  role: "admin" | "member" | "viewer";
  claimed: boolean;
  claimed_at: string | null;
  created_at: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function WorkspaceSettings() {
  const { user } = useAuthStore();
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("general");

  // Determine workspace ID from localStorage
  const workspaceId =
    typeof window !== "undefined"
      ? localStorage.getItem("current_workspace_id")
      : null;

  // Determine if user is workspace admin
  const isOwner = workspace?.owner_user_id === user?.id;
  const memberEntry = workspace?.members.find((m) => m.user_id === user?.id);
  const isWsAdmin = isOwner || memberEntry?.role === "admin" || user?.is_superuser === true;

  const fetchWorkspace = useCallback(async () => {
    if (!workspaceId) return;
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/workspaces/${workspaceId}`);
      setWorkspace(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Impossible de charger l'espace de travail");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchWorkspace();
  }, [fetchWorkspace]);

  if (!workspaceId) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-gray-400">
          Aucun espace de travail sélectionné.
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 flex items-center justify-center gap-2 text-sm text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Chargement…
        </CardContent>
      </Card>
    );
  }

  if (error || !workspace) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-red-500">
          {error || "Erreur inconnue"}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="general" className="text-xs">
            <Building2 className="h-3.5 w-3.5 mr-1.5" />
            Général
          </TabsTrigger>
          <TabsTrigger value="members" className="text-xs">
            <Users className="h-3.5 w-3.5 mr-1.5" />
            Membres
          </TabsTrigger>
          <TabsTrigger value="banking" className="text-xs">
            <Landmark className="h-3.5 w-3.5 mr-1.5" />
            Banques
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <GeneralSection
            workspace={workspace}
            isAdmin={isWsAdmin}
            onUpdated={fetchWorkspace}
          />
        </TabsContent>

        <TabsContent value="members">
          <MembersSection
            workspace={workspace}
            isAdmin={isWsAdmin}
            isSuperUser={user?.is_superuser === true}
            currentUserId={user?.id || 0}
            onUpdated={fetchWorkspace}
          />
        </TabsContent>

        <TabsContent value="banking">
          <BankingSection isAdmin={isWsAdmin} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// GENERAL SECTION
// ============================================================================

function GeneralSection({
  workspace,
  isAdmin,
  onUpdated,
}: {
  workspace: WorkspaceDetail;
  isAdmin: boolean;
  onUpdated: () => void;
}) {
  const [name, setName] = useState(workspace.name);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await api.patch(`/workspaces/${workspace.id}`, { name: name.trim() });
      setSuccess(true);
      onUpdated();
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-purple-600" />
          Informations de l&apos;espace de travail
        </CardTitle>
        <CardDescription>
          Paramètres généraux de votre espace de travail
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Workspace Name */}
        <div className="space-y-2">
          <Label htmlFor="ws_name">Nom de l&apos;espace de travail</Label>
          <div className="flex items-center gap-2">
            <Input
              id="ws_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!isAdmin}
              placeholder="Mon Agence"
            />
            {isAdmin && (
              <Button onClick={handleSave} disabled={saving || !name.trim() || name === workspace.name} size="sm">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              </Button>
            )}
          </div>
          {success && (
            <p className="text-xs text-emerald-600">✓ Enregistré</p>
          )}
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <InfoBlock label="Propriétaire" value={workspace.owner_name || "—"} />
          <InfoBlock label="Membres" value={`${workspace.members_count} utilisateur${workspace.members_count > 1 ? "s" : ""}`} />
          <InfoBlock label="Créé le" value={formatDate(workspace.created_at)} />
          <InfoBlock label="Dernière modification" value={formatDate(workspace.updated_at)} />
        </div>

        {/* Google Drive */}
        {workspace.drive_url && (
          <div className="rounded-lg border border-gray-200 dark:border-slate-700 p-4">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Google Drive
            </p>
            <a
              href={workspace.drive_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-purple-600 hover:underline"
            >
              Ouvrir le dossier Drive →
            </a>
          </div>
        )}
      </CardContent>
    </Card>

    {/* Company / Legal Info */}
    <CompanyInfoSection workspace={workspace} isAdmin={isAdmin} onUpdated={onUpdated} />
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 dark:bg-slate-800/50 px-4 py-3">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

// ============================================================================
// COMPANY INFO SECTION
// ============================================================================

function CompanyInfoSection({
  workspace,
  isAdmin,
  onUpdated,
}: {
  workspace: WorkspaceDetail;
  isAdmin: boolean;
  onUpdated: () => void;
}) {
  const [form, setForm] = useState({
    legal_name: workspace.legal_name || "",
    legal_address: workspace.legal_address || "",
    legal_city: workspace.legal_city || "",
    legal_postal_code: workspace.legal_postal_code || "",
    legal_country: workspace.legal_country || "France",
    legal_phone: workspace.legal_phone || "",
    legal_email: workspace.legal_email || "",
    siret: workspace.siret || "",
    vat_number: workspace.vat_number || "",
    forme_juridique: workspace.forme_juridique || "",
    capital_social: workspace.capital_social || "",
    rcs_city: workspace.rcs_city || "",
    tva_franchise: workspace.tva_franchise || false,
  });
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // SIRET lookup
  const [siretSearch, setSiretSearch] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const searchSiret = async () => {
    const clean = siretSearch.replace(/\s/g, "");
    if (!clean) return;
    setSearching(true);
    setSearchResults([]);
    setSearchError(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await workspaceFetch(
        `/api/v1/workspaces/siret/search?q=${encodeURIComponent(clean)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        if (data.results && data.results.length > 0) {
          setSearchResults(data.results);
          setShowResults(true);
        } else {
          setSearchError("Aucune entreprise trouvée");
        }
      } else {
        setSearchError("Erreur lors de la recherche");
      }
    } catch (err) {
      console.error("SIRET lookup error", err);
      setSearchError("Erreur de connexion");
    } finally {
      setSearching(false);
    }
  };

  const selectCompany = (company: any) => {
    const siege = company.siege || {};

    // Build street address from parts
    const addrParts: string[] = [];
    if (siege.numero_voie) addrParts.push(siege.numero_voie);
    if (siege.indice_repetition) addrParts.push(siege.indice_repetition);
    if (siege.type_voie) addrParts.push(siege.type_voie);
    if (siege.libelle_voie) addrParts.push(siege.libelle_voie);
    const streetAddress = addrParts.join(" ");

    // Compute TVA intracommunautaire from SIREN
    const siren = company.siren || "";
    let vatNumber = "";
    if (siren && siren.length === 9) {
      const sirenNum = parseInt(siren, 10);
      if (!isNaN(sirenNum)) {
        const key = (12 + 3 * (sirenNum % 97)) % 97;
        vatNumber = `FR${key.toString().padStart(2, "0")}${siren}`;
      }
    }

    setForm({
      ...form,
      legal_name: company.nom_complet || company.nom_raison_sociale || "",
      legal_address: streetAddress || siege.complement_adresse || "",
      legal_city: siege.libelle_commune || "",
      legal_postal_code: siege.code_postal || "",
      legal_country: "France",
      siret: siege.siret || "",
      vat_number: vatNumber || form.vat_number,
      forme_juridique: company.nature_juridique || form.forme_juridique,
      rcs_city: siege.libelle_commune || form.rcs_city,
      capital_social: form.capital_social,
      tva_franchise: form.tva_franchise,
      legal_phone: form.legal_phone,
      legal_email: form.legal_email,
    });

    setShowResults(false);
    setSiretSearch("");
    setSearchResults([]);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/workspaces/${workspace.id}`, form);
      setSuccess(true);
      onUpdated();
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-purple-600" />
          Informations de l&apos;entreprise
        </CardTitle>
        <CardDescription>
          Ces informations apparaîtront sur vos devis et factures.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* SIRET Lookup */}
        {isAdmin && (
          <div className="relative">
            <Label className="text-sm font-medium mb-1.5 block">Recherche par SIRET ou nom d&apos;entreprise</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={siretSearch}
                  onChange={(e) => {
                    setSiretSearch(e.target.value);
                    setSearchError(null);
                    if (!e.target.value) {
                      setShowResults(false);
                      setSearchResults([]);
                    }
                  }}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); searchSiret(); } }}
                  placeholder="Ex: 123 456 789 00012 ou Nom de l'entreprise"
                  className="pl-9"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={searchSiret}
                disabled={searching || !siretSearch.trim()}
                className="shrink-0"
              >
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>Rechercher</>
                )}
              </Button>
            </div>
            {searchError && (
              <p className="text-xs text-red-500 mt-1.5">{searchError}</p>
            )}
            {/* Search results dropdown */}
            {showResults && searchResults.length > 0 && (
              <div className="absolute z-50 mt-1 w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-72 overflow-auto">
                {searchResults.map((company, idx) => {
                  const siege = company.siege || {};
                  return (
                    <button
                      key={idx}
                      type="button"
                      className="w-full text-left px-4 py-3 hover:bg-purple-50 dark:hover:bg-purple-900/20 border-b border-gray-100 dark:border-gray-800 last:border-0 transition-colors"
                      onClick={() => selectCompany(company)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm text-gray-900 dark:text-white">
                          {company.nom_complet}
                        </span>
                        <span className="text-xs font-mono text-purple-600 bg-purple-50 dark:bg-purple-900/30 px-2 py-0.5 rounded">
                          {siege.siret}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {siege.adresse || "Adresse non renseignée"}
                      </p>
                      {company.etat_administratif === "C" && (
                        <span className="inline-block text-xs text-red-600 bg-red-50 px-1.5 py-0.5 rounded mt-1">
                          Cessée
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Nom société + SIRET */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="legal_name">Raison sociale</Label>
            <Input
              id="legal_name"
              value={form.legal_name}
              onChange={(e) => handleChange("legal_name", e.target.value)}
              disabled={!isAdmin}
              placeholder="Mon Agence SAS"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="siret">SIRET</Label>
            <Input
              id="siret"
              value={form.siret}
              onChange={(e) => handleChange("siret", e.target.value)}
              disabled={!isAdmin}
              placeholder="123 456 789 00012"
            />
          </div>
        </div>

        {/* TVA */}
        <div className="space-y-1.5">
          <Label htmlFor="vat_number">N° TVA intracommunautaire</Label>
          <Input
            id="vat_number"
            value={form.vat_number}
            onChange={(e) => handleChange("vat_number", e.target.value)}
            disabled={!isAdmin}
            placeholder="FR 12 345678901"
          />
        </div>

        {/* Forme juridique, Capital, RCS */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="forme_juridique">Forme juridique</Label>
            <Input
              id="forme_juridique"
              value={typeof form.forme_juridique === 'string' ? form.forme_juridique : ''}
              onChange={(e) => handleChange("forme_juridique", e.target.value)}
              disabled={!isAdmin}
              placeholder="SAS, SARL, EURL, EI..."
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="capital_social">Capital social</Label>
            <Input
              id="capital_social"
              value={typeof form.capital_social === 'string' ? form.capital_social : ''}
              onChange={(e) => handleChange("capital_social", e.target.value)}
              disabled={!isAdmin}
              placeholder="10 000 €"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="rcs_city">Ville RCS</Label>
            <Input
              id="rcs_city"
              value={typeof form.rcs_city === 'string' ? form.rcs_city : ''}
              onChange={(e) => handleChange("rcs_city", e.target.value)}
              disabled={!isAdmin}
              placeholder="Paris"
            />
          </div>
        </div>

        {/* Franchise TVA */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="tva_franchise"
            checked={!!form.tva_franchise}
            onChange={(e) => setForm({ ...form, tva_franchise: e.target.checked })}
            disabled={!isAdmin}
            className="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
          />
          <Label htmlFor="tva_franchise" className="text-sm">
            Franchise en base de TVA (art. 293 B du CGI)
          </Label>
        </div>

        {/* Adresse */}
        <div className="space-y-1.5">
          <Label htmlFor="legal_address">Adresse</Label>
          <Input
            id="legal_address"
            value={form.legal_address}
            onChange={(e) => handleChange("legal_address", e.target.value)}
            disabled={!isAdmin}
            placeholder="12 rue de la Paix"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="legal_postal_code">Code postal</Label>
            <Input
              id="legal_postal_code"
              value={form.legal_postal_code}
              onChange={(e) => handleChange("legal_postal_code", e.target.value)}
              disabled={!isAdmin}
              placeholder="75001"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="legal_city">Ville</Label>
            <Input
              id="legal_city"
              value={form.legal_city}
              onChange={(e) => handleChange("legal_city", e.target.value)}
              disabled={!isAdmin}
              placeholder="Paris"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="legal_country">Pays</Label>
            <Input
              id="legal_country"
              value={form.legal_country}
              onChange={(e) => handleChange("legal_country", e.target.value)}
              disabled={!isAdmin}
              placeholder="France"
            />
          </div>
        </div>

        {/* Contact */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="legal_email">Email de facturation</Label>
            <Input
              id="legal_email"
              type="email"
              value={form.legal_email}
              onChange={(e) => handleChange("legal_email", e.target.value)}
              disabled={!isAdmin}
              placeholder="facturation@monagence.fr"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="legal_phone">Téléphone</Label>
            <Input
              id="legal_phone"
              value={form.legal_phone}
              onChange={(e) => handleChange("legal_phone", e.target.value)}
              disabled={!isAdmin}
              placeholder="+33 1 23 45 67 89"
            />
          </div>
        </div>

        {/* Save */}
        {isAdmin && (
          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={saving} size="sm">
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
              ) : (
                <Save className="h-4 w-4 mr-1.5" />
              )}
              Enregistrer
            </Button>
            {success && (
              <p className="text-xs text-emerald-600">✓ Informations enregistrées</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// MEMBERS SECTION
// ============================================================================

function MembersSection({
  workspace,
  isAdmin,
  isSuperUser,
  currentUserId,
  onUpdated,
}: {
  workspace: WorkspaceDetail;
  isAdmin: boolean;
  isSuperUser: boolean;
  currentUserId: number;
  onUpdated: () => void;
}) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addRole, setAddRole] = useState<"admin" | "member" | "viewer">("member");
  const [addAuthProvider, setAddAuthProvider] = useState<"credentials" | "google">("credentials");
  const [addPassword, setAddPassword] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Reset password state
  const [showResetDialog, setShowResetDialog] = useState(false);
  const [resetMember, setResetMember] = useState<WorkspaceMember | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Invite (authorized emails) state
  const [invites, setInvites] = useState<InviteEmail[]>([]);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "member" | "viewer">("member");
  const [isInviting, setIsInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  // Fetch invites
  const fetchInvites = useCallback(async () => {
    if (!isAdmin) return;
    setInvitesLoading(true);
    try {
      const { data } = await api.get(`/workspaces/${workspace.id}/invites`);
      setInvites(data.items || []);
    } catch (err) {
      console.error("Failed to fetch invites", err);
    } finally {
      setInvitesLoading(false);
    }
  }, [workspace.id, isAdmin]);

  useEffect(() => {
    fetchInvites();
  }, [fetchInvites]);

  const handleAddInvite = async () => {
    if (!inviteEmail.trim()) return;
    setIsInviting(true);
    setInviteError(null);
    try {
      await api.post(`/workspaces/${workspace.id}/invites`, {
        email: inviteEmail.trim().toLowerCase(),
        role: inviteRole,
      });
      setInviteEmail("");
      setInviteRole("member");
      setShowInviteDialog(false);
      fetchInvites();
    } catch (err: any) {
      setInviteError(err?.response?.data?.detail || "Erreur lors de l'ajout");
    } finally {
      setIsInviting(false);
    }
  };

  const handleRemoveInvite = async (inviteId: number) => {
    try {
      await api.delete(`/workspaces/${workspace.id}/invites/${inviteId}`);
      fetchInvites();
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetPassword = async (member: WorkspaceMember) => {
    setResetMember(member);
    setGeneratedPassword(null);
    setResetError(null);
    setCopied(false);
    setShowResetDialog(true);
  };

  const confirmResetPassword = async () => {
    if (!resetMember) return;
    setIsResetting(true);
    setResetError(null);
    try {
      const { data } = await api.post(
        `/workspaces/${workspace.id}/members/${resetMember.id}/reset-password`,
        {}
      );
      setGeneratedPassword(data.generated_password);
    } catch (err: any) {
      setResetError(err?.response?.data?.detail || "Erreur lors de la réinitialisation");
    } finally {
      setIsResetting(false);
    }
  };

  const copyPassword = () => {
    if (generatedPassword) {
      navigator.clipboard.writeText(generatedPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleAddMember = async () => {
    if (!addEmail.trim()) return;
    if (isSuperUser && addAuthProvider === "credentials" && addPassword.length < 6) {
      setAddError("Le mot de passe doit contenir au moins 6 caractères");
      return;
    }
    setIsAdding(true);
    setAddError(null);
    try {
      const payload: Record<string, string> = {
        user_email: addEmail.trim().toLowerCase(),
        role: addRole,
      };
      if (isSuperUser) {
        payload.auth_provider = addAuthProvider;
        if (addAuthProvider === "credentials") {
          payload.password = addPassword;
        }
      }
      await api.post(`/workspaces/${workspace.id}/members`, payload);
      setAddEmail("");
      setAddRole("member");
      setAddAuthProvider("credentials");
      setAddPassword("");
      setShowAddDialog(false);
      onUpdated();
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || "Erreur lors de l'ajout");
    } finally {
      setIsAdding(false);
    }
  };

  const handleUpdateRole = async (memberId: number, newRole: string) => {
    try {
      await api.patch(`/workspaces/${workspace.id}/members/${memberId}`, {
        role: newRole,
      });
      onUpdated();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    if (!confirm("Êtes-vous sûr de vouloir retirer ce membre ?")) return;
    try {
      await api.delete(`/workspaces/${workspace.id}/members/${memberId}`);
      onUpdated();
    } catch (err) {
      console.error(err);
    }
  };

  const roleIcon = (role: string) => {
    switch (role) {
      case "admin": return <Shield className="h-3.5 w-3.5 text-purple-600" />;
      case "member": return <Users className="h-3.5 w-3.5 text-blue-600" />;
      case "viewer": return <Eye className="h-3.5 w-3.5 text-gray-400" />;
      default: return null;
    }
  };

  const roleLabel = (role: string) => {
    switch (role) {
      case "admin": return "Admin";
      case "member": return "Membre";
      case "viewer": return "Lecteur";
      default: return role;
    }
  };

  const roleBadgeColor = (role: string) => {
    switch (role) {
      case "admin": return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
      case "member": return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
      case "viewer": return "bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-400";
      default: return "";
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-600" />
                Membres de l&apos;espace
              </CardTitle>
              <CardDescription>
                {workspace.members_count} membre{workspace.members_count > 1 ? "s" : ""}
              </CardDescription>
            </div>
            {isAdmin && (
              <Button size="sm" onClick={() => setShowAddDialog(true)}>
                <UserPlus className="h-4 w-4 mr-2" />
                Ajouter
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-gray-100 dark:divide-slate-800">
            {/* Owner row */}
            <div className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0">
                  <Crown className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {workspace.owner_name || "Propriétaire"}
                  </p>
                  <p className="text-xs text-gray-400">Propriétaire</p>
                </div>
              </div>
              <span className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
              )}>
                <Crown className="h-3 w-3" />
                Propriétaire
              </span>
            </div>

            {/* Members */}
            {workspace.members.map((member) => (
              <div key={member.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gray-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
                    {member.user_avatar ? (
                      <img
                        src={member.user_avatar}
                        alt=""
                        className="w-9 h-9 rounded-full object-cover"
                      />
                    ) : (
                      <span className="text-sm font-medium text-gray-500">
                        {(member.user_name || member.user_email || "?")
                          .charAt(0)
                          .toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {member.user_name || member.user_email}
                    </p>
                    {member.user_email && member.user_name && (
                      <p className="text-xs text-gray-400">{member.user_email}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={cn(
                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                    roleBadgeColor(member.role)
                  )}>
                    {roleIcon(member.role)}
                    {roleLabel(member.role)}
                  </span>

                  {isAdmin && member.user_id !== currentUserId && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-44">
                        <DropdownMenuItem onClick={() => handleUpdateRole(member.id, "admin")}>
                          <Shield className="h-4 w-4 mr-2 text-purple-600" />
                          Passer Admin
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleUpdateRole(member.id, "member")}>
                          <Users className="h-4 w-4 mr-2 text-blue-600" />
                          Passer Membre
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleUpdateRole(member.id, "viewer")}>
                          <Eye className="h-4 w-4 mr-2 text-gray-400" />
                          Passer Lecteur
                        </DropdownMenuItem>
                        {isSuperUser && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => handleResetPassword(member)}>
                              <KeyRound className="h-4 w-4 mr-2 text-amber-600" />
                              Réinitialiser le mot de passe
                            </DropdownMenuItem>
                          </>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => handleRemoveMember(member.id)}
                          className="text-red-600 dark:text-red-400"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Retirer
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </div>
            ))}

            {workspace.members.length === 0 && (
              <div className="py-6 text-center text-sm text-gray-400">
                Aucun membre ajouté. Invitez votre équipe !
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Authorized Emails Section */}
      {isAdmin && (
        <Card className="mt-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <MailPlus className="h-5 w-5 text-purple-600" />
                  Emails Autorisés
                </CardTitle>
                <CardDescription>
                  Les utilisateurs avec ces emails seront automatiquement ajoutés à ce workspace lors de leur connexion.
                </CardDescription>
              </div>
              <Button size="sm" onClick={() => setShowInviteDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Ajouter un Email
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {invitesLoading ? (
              <div className="py-6 flex items-center justify-center gap-2 text-sm text-gray-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                Chargement…
              </div>
            ) : invites.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-400">
                Aucun email autorisé. Ajoutez des emails pour permettre l&apos;accès automatique.
              </div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-slate-800">
                {invites.map((invite) => (
                  <div key={invite.id} className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
                        <Mail className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {invite.email}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={cn(
                            "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium",
                            roleBadgeColor(invite.role)
                          )}>
                            {roleIcon(invite.role)}
                            {roleLabel(invite.role)}
                          </span>
                          {invite.claimed ? (
                            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400">
                              <CheckCircle2 className="h-3 w-3" />
                              Activé
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400">
                              <Clock className="h-3 w-3" />
                              En attente
                            </span>
                          )}
                          <span className="text-[10px] text-gray-400">
                            Ajouté le {new Date(invite.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
                          </span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30"
                      onClick={() => handleRemoveInvite(invite.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Add Invite Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MailPlus className="h-5 w-5 text-purple-600" />
              Ajouter un Email Autorisé
            </DialogTitle>
            <DialogDescription>
              L&apos;utilisateur avec cet email sera automatiquement ajouté au workspace lors de sa connexion.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                placeholder="exemple@email.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label>Rôle dans le workspace</Label>
              <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">
                    <span className="flex items-center gap-2">
                      <Shield className="h-3.5 w-3.5 text-purple-600" />
                      Admin
                    </span>
                  </SelectItem>
                  <SelectItem value="member">
                    <span className="flex items-center gap-2">
                      <Users className="h-3.5 w-3.5 text-blue-600" />
                      Membre - Lecture/Écriture
                    </span>
                  </SelectItem>
                  <SelectItem value="viewer">
                    <span className="flex items-center gap-2">
                      <Eye className="h-3.5 w-3.5 text-gray-400" />
                      Lecteur
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {inviteError && (
              <p className="text-sm text-red-500 flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                {inviteError}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInviteDialog(false)}>
              Annuler
            </Button>
            <Button
              onClick={handleAddInvite}
              disabled={!inviteEmail.trim() || isInviting}
            >
              {isInviting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Ajouter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Member Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-blue-600" />
              Ajouter un membre
            </DialogTitle>
            <DialogDescription>
              {isSuperUser
                ? "Invitez un utilisateur existant ou créez un nouveau compte."
                : "Invitez un utilisateur existant par son adresse email."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                placeholder="utilisateur@email.com"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label>Rôle</Label>
              <Select value={addRole} onValueChange={(v) => setAddRole(v as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="member">Membre</SelectItem>
                  <SelectItem value="viewer">Lecteur</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {isSuperUser && (
              <>
                <div className="space-y-2">
                  <Label>Type de compte</Label>
                  <Select value={addAuthProvider} onValueChange={(v) => setAddAuthProvider(v as "credentials" | "google")}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="credentials">
                        <span className="flex items-center gap-2">
                          <Lock className="h-3.5 w-3.5" />
                          Email &amp; mot de passe
                        </span>
                      </SelectItem>
                      <SelectItem value="google">
                        <span className="flex items-center gap-2">
                          <Mail className="h-3.5 w-3.5" />
                          Compte Google (SSO)
                        </span>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-400">
                    {addAuthProvider === "google"
                      ? "L'utilisateur se connectera via Google Sign-In."
                      : "L'utilisateur se connectera avec un email et un mot de passe."}
                  </p>
                </div>

                {addAuthProvider === "credentials" && (
                  <div className="space-y-2">
                    <Label>Mot de passe temporaire</Label>
                    <Input
                      type="password"
                      placeholder="Min. 6 caractères"
                      value={addPassword}
                      onChange={(e) => setAddPassword(e.target.value)}
                    />
                  </div>
                )}
              </>
            )}

            {addError && (
              <p className="text-sm text-red-500 flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                {addError}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Annuler
            </Button>
            <Button
              onClick={handleAddMember}
              disabled={!addEmail.trim() || isAdding}
            >
              {isAdding ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <UserPlus className="h-4 w-4 mr-2" />
              )}
              Ajouter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={showResetDialog} onOpenChange={(open) => {
        if (!open) {
          setShowResetDialog(false);
          setGeneratedPassword(null);
          setResetError(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-amber-600" />
              Réinitialiser le mot de passe
            </DialogTitle>
            <DialogDescription>
              {generatedPassword
                ? "Le nouveau mot de passe a été généré. Transmettez-le à l'utilisateur."
                : `Générer un nouveau mot de passe pour ${resetMember?.user_name || resetMember?.user_email || "cet utilisateur"} ?`}
            </DialogDescription>
          </DialogHeader>

          {!generatedPassword && !resetError && (
            <div className="py-2">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Un mot de passe aléatoire sera généré. L&apos;utilisateur devra l&apos;utiliser pour se reconnecter.
              </p>
            </div>
          )}

          {generatedPassword && (
            <div className="space-y-3">
              <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4">
                <p className="text-xs text-amber-600 dark:text-amber-400 mb-1 font-medium">Nouveau mot de passe :</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-lg font-mono font-bold text-amber-800 dark:text-amber-300 select-all">
                    {generatedPassword}
                  </code>
                  <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" onClick={copyPassword}>
                    {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Ce mot de passe ne sera plus affiché après fermeture.
              </p>
            </div>
          )}

          {resetError && (
            <p className="text-sm text-red-500 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              {resetError}
            </p>
          )}

          <DialogFooter>
            {!generatedPassword ? (
              <>
                <Button variant="outline" onClick={() => setShowResetDialog(false)}>
                  Annuler
                </Button>
                <Button
                  onClick={confirmResetPassword}
                  disabled={isResetting}
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                >
                  {isResetting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <KeyRound className="h-4 w-4 mr-2" />
                  )}
                  Générer un nouveau mot de passe
                </Button>
              </>
            ) : (
              <Button onClick={() => setShowResetDialog(false)}>
                Fermer
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ============================================================================
// BANKING SECTION — Revolut-style design
// ============================================================================

function BankingSection({ isAdmin }: { isAdmin: boolean }) {
  const {
    dashboard,
    connections,
    selectedConnection,
    isLoading,
    error,
    fetchDashboard,
    fetchConnectionDetail,
    isSyncing,
    triggerSync,
    updateConnection,
    deleteConnection,
    // Revolut
    revolutStatus,
    fetchRevolutStatus,
    connectRevolut,
    syncRevolut,
    disconnectRevolut,
  } = useBankingStore();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [revolutConnecting, setRevolutConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);

  useEffect(() => {
    fetchDashboard();
    fetchRevolutStatus();
  }, [fetchDashboard, fetchRevolutStatus]);

  useEffect(() => {
    if (selectedId) {
      fetchConnectionDetail(selectedId);
    }
  }, [selectedId, fetchConnectionDetail]);

  const handleConnectRevolut = async () => {
    setRevolutConnecting(true);
    setShowAddDialog(false);
    const url = await connectRevolut();
    setRevolutConnecting(false);
    if (url) {
      window.location.href = url;
    }
  };

  const handleDeleteConnection = async (conn: typeof selectedConnection) => {
    if (!conn) return;
    const label = conn.bank_name || "cette banque";
    if (!confirm(`Supprimer ${label} ? Les comptes et données liés seront supprimés.`)) return;
    setIsDisconnecting(true);
    if (conn.provider === "revolut") {
      await disconnectRevolut();
      fetchRevolutStatus();
    } else {
      await deleteConnection(conn.id);
    }
    setIsDisconnecting(false);
    setSelectedId(null);
    fetchDashboard();
  };

  const formatCurrency = (val: number, currency: string = "EUR") =>
    new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(val);

  const formatDateShort = (d?: string | null) => {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusInfo = (s: string) => {
    switch (s) {
      case "CONNECTED":
        return { label: "Actif", cls: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800" };
      case "CONNECTING":
        return { label: "Connexion en cours", cls: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800" };
      case "SYNC_ERROR":
        return { label: "Erreur de synchronisation", cls: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800" };
      case "CONSENT_EXPIRED":
        return { label: "Consentement expiré", cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800" };
      case "SUSPENDED":
        return { label: "Suspendu", cls: "bg-gray-50 text-gray-600 border-gray-200 dark:bg-slate-800 dark:text-gray-400 dark:border-slate-700" };
      case "NOT_CONNECTED":
      case "REVOKED":
        return { label: "Identification nécessaire", cls: "bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800" };
      default:
        return { label: s, cls: "bg-gray-50 text-gray-600 border-gray-200" };
    }
  };

  // ── Not enabled ──
  if (dashboard && !dashboard.banking_enabled) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-12 text-center">
        <div className="w-14 h-14 rounded-2xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mx-auto mb-4">
          <Landmark className="h-7 w-7 text-purple-600 dark:text-purple-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Connexions bancaires
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
          Cette fonctionnalité n&apos;est pas activée pour votre espace de travail.
          Souscrivez à l&apos;addon <strong>Radar Business</strong> pour en bénéficier.
        </p>
      </div>
    );
  }

  // ── Detail view (Administrer) ──
  if (selectedId && selectedConnection) {
    return (
      <div className="space-y-4">
        {/* Back button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSelectedId(null)}
          className="text-gray-500 hover:text-gray-900 dark:hover:text-white -ml-2"
        >
          ← Retour aux comptes
        </Button>

        <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
          {/* Connection header */}
          <div className="px-6 py-5 border-b border-gray-100 dark:border-slate-800 flex items-center gap-4">
            {selectedConnection.provider === "revolut" ? (
              <img src="/revolut-logo.webp" alt="Revolut" className="w-10 h-10 rounded-xl flex-shrink-0" />
            ) : selectedConnection.bank_logo_url ? (
              <img
                src={selectedConnection.bank_logo_url}
                alt=""
                className="w-10 h-10 rounded-xl object-contain bg-gray-50 dark:bg-slate-800 p-1"
              />
            ) : (
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
                <Landmark className="h-5 w-5 text-white" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                {selectedConnection.bank_name}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <BankStatusBadge status={selectedConnection.status} size="sm" />
                {selectedConnection.last_sync_at && (
                  <span className="text-xs text-gray-400">
                    Dernière sync : {formatDateShort(selectedConnection.last_sync_at)}
                  </span>
                )}
              </div>
            </div>
            {isAdmin && (selectedConnection.status === "CONNECTED" || selectedConnection.status === "SYNC_ERROR") && (
              <Button
                variant="outline"
                size="sm"
                className="text-pink-600 border-pink-200 hover:bg-pink-50 dark:text-pink-400 dark:border-pink-800 dark:hover:bg-pink-950/30"
                onClick={() => triggerSync(selectedConnection.id)}
                disabled={isSyncing[selectedConnection.id]}
              >
                <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", isSyncing[selectedConnection.id] && "animate-spin")} />
                {isSyncing[selectedConnection.id] ? "Sync…" : "Synchroniser"}
              </Button>
            )}
          </div>

          {/* Accounts */}
          <div className="px-6 py-4">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Comptes ({selectedConnection.accounts.length})
            </h4>

            {selectedConnection.accounts.length > 0 ? (
              <div className="divide-y divide-gray-100 dark:divide-slate-800">
                {selectedConnection.accounts.map((acc, i) => (
                  <div key={acc.id} className="flex items-center justify-between py-3.5">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full border-2 border-gray-200 dark:border-slate-600 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-gray-600 dark:text-gray-400">
                          {i + 1}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                          {acc.account_name}
                        </p>
                        <p className="text-xs text-gray-400">
                          {acc.account_type} · {acc.currency}
                          {acc.iban_masked ? ` · ${acc.iban_masked}` : ""}
                        </p>
                      </div>
                    </div>
                    <p className="text-sm font-bold text-gray-900 dark:text-white ml-4 flex-shrink-0">
                      {acc.balance != null
                        ? formatCurrency(acc.balance, acc.currency || "EUR")
                        : "—"}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">
                Aucun compte. Lancez une synchronisation.
              </p>
            )}
          </div>

          {/* Admin settings */}
          {isAdmin && (
            <div className="px-6 py-4 border-t border-gray-100 dark:border-slate-800 space-y-4">
              {/* Auto-sync toggle */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-slate-800/50">
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Synchronisation automatique
                  </p>
                  <p className="text-xs text-gray-400">
                    Toutes les {selectedConnection.sync_frequency_hours}h
                  </p>
                </div>
                <button
                  onClick={() =>
                    updateConnection(selectedConnection.id, {
                      auto_sync_enabled: !selectedConnection.auto_sync_enabled,
                    })
                  }
                  className={cn(
                    "relative w-11 h-6 rounded-full transition-colors",
                    selectedConnection.auto_sync_enabled
                      ? "bg-pink-500"
                      : "bg-gray-300 dark:bg-gray-600",
                  )}
                >
                  <span
                    className={cn(
                      "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform",
                      selectedConnection.auto_sync_enabled && "translate-x-5",
                    )}
                  />
                </button>
              </div>

              {/* Recent syncs */}
              {selectedConnection.recent_syncs.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    Historique de synchronisation
                  </h4>
                  <div className="space-y-1.5">
                    {selectedConnection.recent_syncs.slice(0, 5).map((sync) => (
                      <div
                        key={sync.id}
                        className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50 dark:bg-slate-800/50 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <SyncStatusBadge status={sync.status} />
                          <span className="text-gray-500">
                            {formatDateShort(sync.started_at)}
                          </span>
                        </div>
                        <span className="text-gray-400">
                          {sync.accounts_synced} comptes
                          {sync.duration_ms != null &&
                            ` · ${(sync.duration_ms / 1000).toFixed(1)}s`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Delete / disconnect button */}
              <div className="pt-3 mt-3 border-t border-gray-100 dark:border-slate-800">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDeleteConnection(selectedConnection)}
                  disabled={isDisconnecting}
                  className="w-full text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-900/20"
                >
                  {isDisconnecting ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  Supprimer {selectedConnection.bank_name}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Main list view — Revolut-style ──
  return (
    <div className="space-y-4">
      {/* Error banner */}
      {error && (
        <div className="px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm flex items-center gap-2 border border-red-200 dark:border-red-800/50">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Consent alert */}
      {dashboard && dashboard.expiring_consents > 0 && (
        <div className="px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 text-amber-700 dark:text-amber-400 text-sm flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {dashboard.expiring_consents} consentement
          {dashboard.expiring_consents > 1 ? "s" : ""} expire
          {dashboard.expiring_consents > 1 ? "nt" : ""} bientôt.
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
        {/* Section header */}
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-800">
          <h3 className="text-base font-bold text-gray-900 dark:text-white">
            Comptes et cartes
          </h3>
        </div>

        {/* Accounts / connections list */}
        <div className="divide-y divide-gray-100 dark:divide-slate-800">
          {isLoading && connections.length === 0 ? (
            <div className="px-6 py-12 flex items-center justify-center gap-2 text-sm text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Chargement…
            </div>
          ) : connections.length > 0 ? (
            connections.map((conn, index) => {
              const si = getStatusInfo(conn.status);
              return (
                <div
                  key={conn.id}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50/60 dark:hover:bg-slate-800/30 transition-colors"
                >
                  {/* Bank logo */}
                  {conn.provider === "revolut" ? (
                    <img src="/revolut-logo.webp" alt="Revolut" className="w-10 h-10 rounded-xl flex-shrink-0" />
                  ) : conn.bank_logo_url ? (
                    <img src={conn.bank_logo_url} alt="" className="w-10 h-10 rounded-xl object-contain bg-gray-50 dark:bg-slate-800 p-1 flex-shrink-0" />
                  ) : (
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                      <Landmark className="h-5 w-5 text-white" />
                    </div>
                  )}

                  {/* Name + subtitle */}
                  <div className="min-w-0 flex-shrink-0">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {conn.accounts_count === 1 && conn.provider === "revolut"
                        ? "Pocket EUR"
                        : conn.bank_name}
                    </p>
                    <p className="text-xs text-gray-400">{conn.bank_name}</p>
                  </div>

                  {/* Status badge */}
                  <span
                    className={cn(
                      "inline-flex items-center px-2.5 py-0.5 rounded border text-[11px] font-medium whitespace-nowrap",
                      si.cls,
                    )}
                  >
                    {si.label}
                  </span>

                  {/* Spacer */}
                  <div className="flex-1" />

                  {/* Balance */}
                  <p className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
                    {conn.total_balance != null
                      ? formatCurrency(conn.total_balance)
                      : "0,00 €"}
                  </p>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {isAdmin &&
                      (conn.status === "CONNECTED" ||
                        conn.status === "SYNC_ERROR") && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-pink-600 border-pink-200 hover:bg-pink-50 dark:text-pink-400 dark:border-pink-800 dark:hover:bg-pink-950/30 h-8 text-xs rounded-lg"
                          onClick={(e) => {
                            e.stopPropagation();
                            triggerSync(conn.id);
                          }}
                          disabled={isSyncing[conn.id]}
                        >
                          <RefreshCw
                            className={cn(
                              "h-3.5 w-3.5 mr-1.5",
                              isSyncing[conn.id] && "animate-spin",
                            )}
                          />
                          Vérifier
                        </Button>
                      )}
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs rounded-lg"
                      onClick={() => setSelectedId(conn.id)}
                    >
                      <Settings2 className="h-3.5 w-3.5 mr-1.5" />
                      Administrer
                    </Button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="px-6 py-14 text-center">
              <div className="w-12 h-12 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-3">
                <Landmark className="h-6 w-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Aucun compte connecté
              </p>
              <p className="text-xs text-gray-400 mt-1 max-w-xs mx-auto">
                Connectez votre première banque pour centraliser vos comptes professionnels.
              </p>
            </div>
          )}
        </div>

        {/* Add account/card button — pink pill */}
        {isAdmin && (
          <div className="px-6 py-5 flex justify-center border-t border-gray-100 dark:border-slate-800">
            <Button
              className="bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white rounded-full px-6 h-10 text-sm font-medium shadow-sm"
              onClick={() => setShowAddDialog(true)}
              disabled={revolutConnecting}
            >
              {revolutConnecting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              {revolutConnecting ? "Connexion en cours…" : "Ajouter un compte ou une carte"}
            </Button>
          </div>
        )}
      </div>

      {/* Add Bank Dialog — for now, only Revolut is available */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Landmark className="h-5 w-5 text-purple-600" />
              Connecter une banque
            </DialogTitle>
            <DialogDescription>
              Sélectionnez le service bancaire à connecter.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 py-2">
            {/* Revolut option */}
            <button
              onClick={handleConnectRevolut}
              disabled={revolutConnecting || revolutStatus?.connected}
              className={cn(
                "w-full flex items-center gap-4 px-4 py-3.5 rounded-xl text-left transition-all border",
                revolutStatus?.connected
                  ? "bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800/50 cursor-default"
                  : "hover:bg-purple-50 dark:hover:bg-purple-900/20 border-gray-200 dark:border-slate-700 hover:border-purple-300 dark:hover:border-purple-700",
              )}
            >
              <img src="/revolut-logo.webp" alt="Revolut" className="w-10 h-10 rounded-xl flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">
                  Revolut Business
                </p>
                <p className="text-xs text-gray-400">
                  {revolutStatus?.connected
                    ? `Déjà connecté · ${revolutStatus.accounts_count} compte(s)`
                    : "Comptes professionnels, cartes, virements"}
                </p>
              </div>
              {revolutStatus?.connected ? (
                <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Connecté
                </span>
              ) : (
                <ExternalLink className="h-4 w-4 text-gray-400" />
              )}
            </button>

            {/* More banks coming soon */}
            <div className="flex items-center gap-4 px-4 py-3.5 rounded-xl border border-dashed border-gray-200 dark:border-slate-700 opacity-50">
              <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
                <Landmark className="h-5 w-5 text-gray-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Autres banques
                </p>
                <p className="text-xs text-gray-400">
                  BNP, Société Générale, Crédit Agricole… Bientôt disponible
                </p>
              </div>
              <span className="text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                SOON
              </span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// HELPERS
// ============================================================================

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}
