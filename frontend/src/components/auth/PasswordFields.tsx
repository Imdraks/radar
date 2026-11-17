'use client';
import { useQuery } from '@tanstack/react-query';
import { authApi } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export type PasswordPolicy = { min_length: number; max_bytes: number; uppercase: boolean; lowercase: boolean; digit: boolean; special: boolean; reset_expiry_minutes: number };
export function usePasswordPolicy() {
  return useQuery<PasswordPolicy>({ queryKey: ['password-policy'], queryFn: authApi.passwordPolicy, staleTime: 300000 });
}
export function passwordChecks(policy: PasswordPolicy, value: string) {
  return [
    { label: `Au moins ${policy.min_length} caractères`, valid: Array.from(value).length >= policy.min_length },
    { label: 'Une majuscule (A–Z)', valid: !policy.uppercase || /[A-Z]/.test(value) },
    { label: 'Une minuscule (a–z)', valid: !policy.lowercase || /[a-z]/.test(value) },
    { label: 'Un chiffre (0–9)', valid: !policy.digit || /[0-9]/.test(value) },
    { label: 'Un caractère spécial (!, ?, #, _…)', valid: !policy.special || /[^\p{L}\p{N}\s]/u.test(value) },
    { label: `Au maximum ${policy.max_bytes} octets UTF-8`, valid: value.length > 0 && new TextEncoder().encode(value).length <= policy.max_bytes },
  ];
}
export function passwordError(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : 'La demande a échoué. Réessayez plus tard.';
}
export function PasswordFields({ password, confirm, onPassword, onConfirm, disabled, policy, prefix = 'new' }: {
  password: string; confirm: string; onPassword: (value: string) => void; onConfirm: (value: string) => void; disabled?: boolean; policy: PasswordPolicy; prefix?: string;
}) {
  return <div className="space-y-4"><div className="space-y-2"><Label htmlFor={`${prefix}-password`}>Nouveau mot de passe</Label><Input id={`${prefix}-password`} type="password" autoComplete="new-password" value={password} onChange={event => onPassword(event.target.value)} disabled={disabled} required maxLength={128} /></div>
    <ul aria-label="Critères de sécurité du mot de passe" className="space-y-1 text-xs">{passwordChecks(policy, password).map(check => <li key={check.label} className={check.valid ? 'text-green-700 dark:text-green-300' : 'text-muted-foreground'}><span aria-hidden="true">{check.valid ? '✓' : '○'} </span>{check.label}<span className="sr-only">{check.valid ? ' : respecté' : ' : non respecté'}</span></li>)}</ul>
    <p className="text-xs text-muted-foreground">Utilisez un mot de passe unique. Les mots de passe trop courants et le précédent mot de passe sont refusés.</p>
    <div className="space-y-2"><Label htmlFor={`${prefix}-confirm`}>Confirmer le nouveau mot de passe</Label><Input id={`${prefix}-confirm`} type="password" autoComplete="new-password" value={confirm} onChange={event => onConfirm(event.target.value)} disabled={disabled} required maxLength={128} />{confirm && password !== confirm && <p role="status" className="text-xs text-destructive">Les deux mots de passe ne correspondent pas.</p>}</div>
  </div>;
}
