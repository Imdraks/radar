'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X, ArrowUpRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { RadarLogo } from '@/components/brand/RadarBrand';
import { PUBLIC_NAV_LINKS } from './navigation';
import legal from '@/config/legal.json';

/** The contact journey keeps the public navigation in one quiet corner. */
export function ContactNavigation() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return <header className="radar-contact-floating-header" aria-label="Navigation Radar">
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="icon" className="radar-contact-menu-trigger rounded-full"
          aria-label={open ? 'Fermer le menu du site' : 'Ouvrir le menu du site'}>
          {open ? <X size={19} aria-hidden="true" /> : <Menu size={19} aria-hidden="true" />}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={12} collisionPadding={16}
        className="radar-public radar-contact-nav-panel z-[70] w-[300px] max-w-[calc(100vw-32px)] rounded-3xl p-3"
        aria-label="Navigation du site Radar">
        <Link href="/" onClick={close} aria-label="Radar — Accueil" className="mb-3 block rounded-2xl border-b px-3 py-4"><RadarLogo className="[&_svg]:h-9 [&_svg]:w-9" /></Link>
        <nav aria-label="Navigation du site" className="space-y-1">
          {PUBLIC_NAV_LINKS.map(link => <Link key={link.href} href={link.href} onClick={close}
            aria-current={link.href === '/contact' ? 'page' : undefined}
            className="radar-contact-nav-link"><span>{link.label}</span><ArrowUpRight size={14} aria-hidden="true" /></Link>)}
        </nav>
        <Button asChild className="mt-3 w-full rounded-full"><Link href="/login" onClick={close}>Se connecter</Link></Button>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t px-3 pt-3 text-[11px] text-muted-foreground">
          <Link href="/privacy#contact" onClick={close}>Confidentialité</Link>
          <Link href="/legal" onClick={close}>Mentions légales</Link>
          {legal.contactEmail && <a href={`mailto:${legal.contactEmail}`} onClick={close}>Contact direct</a>}
        </div>
      </PopoverContent>
    </Popover>
  </header>;
}
