import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { RadarLogo } from '@/components/brand/RadarBrand';
export function LandingFooter() {
  return <footer className="radar-public border-t bg-white"><div className="mx-auto max-w-[1360px] px-5 py-12 sm:px-8">
    <div className="flex flex-col justify-between gap-8 md:flex-row"><div><Link href="/" aria-label="Radar — Accueil"><RadarLogo /></Link><p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">Le point de repère de votre agence.<br />Organisation, création et activité réunies.</p></div><nav aria-label="Liens de pied de page" className="grid grid-cols-2 gap-x-12 gap-y-3 text-sm"><Link href="/#produit">La plateforme</Link><Link href="/pricing">Abonnements</Link><Link href="/login">Connexion</Link><Link href="/contact" className="flex items-center gap-1">Contact<ArrowUpRight size={13} /></Link></nav></div>
    <div className="mt-10 flex flex-col justify-between gap-4 border-t pt-6 text-xs text-muted-foreground sm:flex-row"><span>Radar · L’espace de travail des agences</span><nav className="flex flex-wrap gap-5" aria-label="Informations légales"><Link href="/legal">Mentions légales</Link><Link href="/privacy">Confidentialité</Link><Link href="/terms">Conditions d’utilisation</Link><Link href="/sales-terms">Conditions commerciales</Link><Link href="/cookies">Cookies</Link><Link href="/reversibility">Réversibilité</Link><Link href="/accessibility">Accessibilité</Link></nav></div>
  </div></footer>;
}
