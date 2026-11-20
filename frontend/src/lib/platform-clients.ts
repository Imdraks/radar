import { api } from './api';
export type ClientSummary = { id: number; name: string; owner_user_id: number; owner_name: string | null; owner_email: string | null; owner_last_login_at: string | null; plan: string; plan_display_name: string; max_seats: number; current_seats: number; is_suspended: boolean; suspension_reason: string | null; suspended_at: string | null; pending_orders: number; created_at: string; plan_expires_at: string | null };
export type Person = { id?: number; user_id: number; name: string | null; email: string | null; role?: string; must_change_password: boolean; is_active?: boolean; last_login_at?: string | null };
export type Invitation = { id: string; user_id: number; kind: string; status: string; created_at: string; sent_at: string | null; expires_at: string | null; error_code: string | null };
export type Order = { id: number; kind: string; value: string; status: string; created_at: string; decided_at: string | null; authorization_reference: string | null; contract_acceptance_id: number | null };
export type Acceptance = { id: number; bundle_id: number; plan: string; version: string; reference: string; accepted_at: string; representative: { name?: string; email?: string }; content_hash: string };
export type PlatformQuote = { id: number; reference: string; status: string; created_at: string; valid_until: string; total_ht: string; total_tax: string; total_ttc: string; order_id: number | null };
export type ExternalContract = { id: number; reference: string; signer: string; signed_on: string; status: string; plan: string | null; order_id: number; reviewed_at: string | null; document_hash: string };
export type ClientDetail = ClientSummary & { company: Record<string, string | null>; owner: Person | null; members: Person[]; invitations: Invitation[]; orders: Order[]; acceptances: Acceptance[]; history: { id: string; action: string; created_at: string; actor: string | null; details: Record<string, unknown> }[]; subscription: { available_features: string[] }; integrations?: { drive_url: string | null; calendar_id: string | null }; quotes?: PlatformQuote[]; external_contracts?: ExternalContract[] };
export async function clientRequest<T>(path: string, method = 'GET', data?: unknown): Promise<T> { return (await api.request<T>({ url: '/admin/clients' + path, method, data })).data; }
export class ClientActionError extends Error {}
export function clientError(error: unknown) {
  if (error instanceof ClientActionError) return error.message;
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return 'Vérifiez les champs requis et leur format.';
  return 'L’opération n’a pas pu être confirmée. Réessayez après avoir vérifié la connexion.';
}
export function clientDate(value?: string | null) { return value ? new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? value + 'T00:00:00Z' : value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z').toLocaleDateString('fr-FR') : 'Non renseigné'; }
export async function downloadClientFile(path: string, filename: string) {
  const response = await api.get('/admin/clients' + path, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
