import { api } from './api';
export type ContactInquiry = {
  id: string; name: string; email: string; company: string; phone?: string; plan: string;
  status: 'new' | 'opened' | 'closed'; created_at: string; opened_at: string | null;
  acknowledgement_status: 'not_requested' | 'pending' | 'processing' | 'sent' | 'failed';
  acknowledgement_sent_at?: string | null; acknowledgement_error?: string | null;
  message?: string; privacy_notice_version?: string; opened_by?: number | null;
};
export const inquiryStatus = { new: 'À ouvrir', opened: 'Ouverte', closed: 'Clôturée' };
export const ackStatus = { not_requested: 'Sera demandé à la première ouverture', pending: 'En attente du service d’envoi', processing: 'Envoi en cours de traitement', sent: 'Transmis au service d’envoi', failed: 'Échec d’envoi' };
export async function inquiryRequest<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  return (await api.request<T>({ url: '/admin/contact-requests' + path, method, data })).data;
}
