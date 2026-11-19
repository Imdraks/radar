'use client';
import Link from 'next/link';
import { useState } from 'react';
import { Menu, ArrowUpRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { Sheet, SheetContent, SheetTitle, SheetDescription, SheetTrigger } from '@/components/ui/sheet';
import { PublicAccountMenu, usePublicAccount } from './PublicAccount';
import { PUBLIC_NAV_LINKS as links } from './navigation';

export function LandingHeader() {
  const [open, setOpen] = useState(false);
  const { account, checking, signOut } = usePublicAccount();
  return <header className="radar-public-header fixed inset-x-0 top-0 z-40 border-b border-border/70 bg-white/95 backdrop-blur-xl">
    <div className="mx-auto flex h-[56px] max-w-[1360px] items-center justify-between gap-4 px-5 sm:px-8">
      <Link href="/" aria-label="Radar — Accueil"><RadarLogo className="gap-2 [&>svg]:h-[30px] [&>svg]:w-[30px] [&>span]:text-[22px]" /></Link>
      <nav aria-label="Navigation du site" className="hidden items-center gap-6 xl:flex">{links.map(link => <Link key={link.href} href={link.href} className="text-sm font-medium text-muted-foreground hover:text-primary">{link.label}</Link>)}</nav>
      <div className="flex items-center gap-3">{account ? <PublicAccountMenu account={account} onLogout={signOut} /> : checking ? <span role="status" aria-label="Vérification de la session" className="h-[40px] w-[40px] rounded-full border border-primary/20 bg-primary/5" /> : <div className="hidden items-center gap-2 xl:flex"><Button asChild variant="ghost"><Link href="/login">Se connecter</Link></Button><Button asChild className="gap-2"><Link href="/contact">Parlons de votre agence<ArrowUpRight size={16} /></Link></Button></div>}
      <Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild><Button variant="outline" size="icon" className="xl:hidden" aria-label="Ouvrir le menu du site"><Menu size={20} /></Button></SheetTrigger><SheetContent className="radar-public bg-white" closeLabel="Fermer le menu du site"><SheetTitle className="sr-only">Navigation du site Radar</SheetTitle><SheetDescription className="sr-only">Plateforme, connecteur ChatGPT, documentation, abonnements et connexion.</SheetDescription><RadarLogo /><nav className="mt-10 flex flex-col gap-2" aria-label="Navigation mobile du site">{links.map(link => <Link key={link.href} href={link.href} className="rounded-xl p-3 text-base hover:bg-primary/5" onClick={() => setOpen(false)}>{link.label}</Link>)}<Button asChild className="mt-4"><Link href={account ? "/today" : "/login"} onClick={() => setOpen(false)}>{account ? "Ouvrir mon espace" : "Se connecter"}</Link></Button></nav></SheetContent></Sheet></div>
    </div>
  </header>;
}
