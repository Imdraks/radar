import type { Metadata } from 'next';
import { PasswordRecovery } from '@/components/auth/PasswordRecovery';
export const metadata: Metadata = { title: 'Mot de passe oublié', robots: { index: false, follow: false }, referrer: 'no-referrer' };
export default function ForgotPasswordPage() { return <PasswordRecovery />; }
