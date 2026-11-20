import { api } from "./api";
export type ActivityEntry = {
  id: string;
  user_id: number | null;
  user_tracking_id: string;
  user_name: string | null;
  user_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
};
export type ActivityPage = {
  items: ActivityEntry[];
  total: number;
  page: number;
  limit: number;
  summary: { authors: number; logins: number; last_event_at: string | null };
};
export type ActivityFilters = {
  authors: { id: number; name: string | null; email: string | null }[];
  actions: string[];
  resource_types: string[];
};
export const actionLabels: Record<string, string> = {
  login: "Connexion",
  logout: "Déconnexion",
  login_failed: "Connexion refusée",
  view: "Consultation",
  create: "Création",
  update: "Modification",
  delete: "Suppression",
  search: "Recherche",
  analyze: "Analyse",
  enrich: "Enrichissement",
  export: "Export",
  radar_trigger: "Radar déclenché",
  user_create: "Compte créé",
  user_update: "Compte modifié",
  user_delete: "Compte supprimé",
  whitelist: "Autorisation de connexion modifiée",
  "client.created": "Entreprise créée",
  "client.updated": "Entreprise modifiée",
  "client.suspended": "Espace suspendu",
  "client.reactivated": "Espace réactivé",
  "client.deleted": "Espace retiré du produit",
  "client.invitation_requested": "Invitation demandée",
  "client.invitation_sent": "Invitation transmise",
  "client.member_added": "Membre ajouté",
  "client.member_removed": "Membre retiré",
  "client.member_role_changed": "Rôle d’un membre modifié",
  "client.owner_transferred": "Responsable changé",
  "client.capacity_authorized": "Places autorisées",
  "client.password_reset_email_requested":
    "Récupération du mot de passe demandée",
  "client.order_created": "Commande créée",
  "client.order_decided": "Décision de commande enregistrée",
  "client.quote_created": "Devis créé",
  "client.quote_issued": "Devis émis",
  "client.external_contract_uploaded": "Contrat externe déposé",
  "client.external_contract_reviewed": "Contrat externe contrôlé",
  "contact.opened": "Demande de contact ouverte",
  "contact.status_changed": "État d’une demande modifié",
  "contact.acknowledgement_retry_requested": "Accusé d’ouverture relancé",
  "mfa.method_enabled": "Méthode A2F activée",
  "mfa.method_disabled": "Méthode A2F désactivée",
  "mfa.recovery_regenerated": "Codes de secours renouvelés",
  "passkey.registered": "Clé d’accès ajoutée",
  "passkey.revoked": "Clé d’accès retirée",
  "password.changed": "Mot de passe modifié",
  "password.reset_requested": "Réinitialisation demandée",
  "password.reset_completed": "Mot de passe réinitialisé",
  "account.setup_completed": "Configuration du compte terminée",
};
export const resourceLabels: Record<string, string> = {
  workspace: "Espace de travail",
  user: "Utilisateur",
  project: "Projet",
  client: "Client",
  quote: "Devis",
  invoice: "Facture",
  artist: "Artiste",
  opportunity: "Opportunité",
  dossier: "Dossier",
  contact_inquiry: "Demande de contact",
  session: "Session",
  task: "Tâche",
  event: "Événement",
  file: "Fichier",
};
export function activityLabel(action: string) {
  return actionLabels[action] || action || "Événement sans libellé";
}
export function actorLabel(entry: ActivityEntry) {
  return (
    entry.user_name ||
    entry.user_email ||
    (entry.user_tracking_id === "SYSTEM"
      ? "Service Radar"
      : "Compte indisponible")
  );
}
export function activityTime(
  value: string | null | undefined,
  seconds = false,
) {
  if (!value) return "Non renseigné";
  const parsed = new Date(
    /Z$|[+-]\d\d:\d\d$/.test(value) ? value : value + "Z",
  );
  if (Number.isNaN(parsed.getTime())) return "Date indisponible";
  return new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    ...(seconds ? { second: "2-digit" } : {}),
  }).format(parsed);
}
export async function activityRequest<T>(path: string): Promise<T> {
  return (await api.get("/admin/logs/" + path)).data;
}
