'use client';
import Link from 'next/link';
import { useState } from 'react';
import { Menu, ArrowUpRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { Sheet, SheetContent, SheetTitle, SheetDescription, SheetTrigger } from '@/components/ui/sheet';

const links = [{ href: '/#produit', label: 'La plateforme' }, { href: '/#workflow', label: 'Votre quotidien' }, { href: '/pricing', label: 'Abonnements' }, { href: '/contact', label: 'Contact' }];
export function LandingHeader() {
  const [open, setOpen] = useState(false);
  return <header className="radar-public-header fixed inset-x-0 top-0 z-40 border-b border-border/70 bg-white/95 backdrop-blur-xl">
    <div className="mx-auto flex h-20 max-w-[1360px] items-center justify-between gap-4 px-5 sm:px-8">
      <Link href="/" aria-label="Radar — Accueil"><RadarLogo /></Link>
      <nav aria-label="Navigation du site" className="hidden items-center gap-8 lg:flex">{links.map(link => <Link key={link.href} href={link.href} className="text-sm font-medium text-muted-foreground hover:text-primary">{link.label}</Link>)}</nav>
      <div className="hidden items-center gap-2 lg:flex"><Button asChild variant="ghost"><Link href="/login">Se connecter</Link></Button><Button asChild className="gap-2"><Link href="/contact">Parlons de votre agence<ArrowUpRight size={16} /></Link></Button></div>
      <Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild><Button variant="outline" size="icon" className="lg:hidden" aria-label="Ouvrir le menu du site"><Menu size={20} /></Button></SheetTrigger><SheetContent className="radar-public bg-white" closeLabel="Fermer le menu du site"><SheetTitle className="sr-only">Navigation du site Radar</SheetTitle><SheetDescription className="sr-only">Plateforme, abonnements et connexion.</SheetDescription><RadarLogo /><nav className="mt-10 flex flex-col gap-2" aria-label="Navigation mobile du site">{links.map(link => <Link key={link.href} href={link.href} className="rounded-xl p-3 text-base hover:bg-primary/5" onClick={() => setOpen(false)}>{link.label}</Link>)}<Button asChild className="mt-4"><Link href="/login" onClick={() => setOpen(false)}>Se connecter</Link></Button></nav></SheetContent></Sheet>
    </div>
  </header>;
}
