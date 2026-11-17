import type { Metadata } from 'next';
import { PasswordRecovery } from '@/components/auth/PasswordRecovery';
export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'Réinitialiser le mot de passe', robots: { index: false, follow: false }, referrer: 'no-referrer' };
export default function ResetPasswordPage() { return <PasswordRecovery reset />; }
