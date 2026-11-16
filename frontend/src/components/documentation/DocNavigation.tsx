'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useId, useState } from 'react';
import { BookOpen, ChevronDown, Search } from 'lucide-react';
import { docCategories, searchDocs } from '@/content/documentation';

export function DocNavigation() {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const inputId = useId();
  const panelId = useId();
  const articles = searchDocs(query);
  return <aside className="min-w-0 lg:w-64 lg:shrink-0" aria-label="Guides Radar">
    <div className="rounded-2xl border bg-white p-4 lg:sticky lg:top-28 lg:max-h-[calc(100dvh-8rem)] lg:overflow-y-auto">
      <div className="flex items-center justify-between gap-3"><Link href="/doc" className="inline-flex items-center gap-2 text-sm font-semibold"><BookOpen size={17} className="text-primary" />Documentation</Link><button type="button" className="rounded-lg border p-2 lg:hidden" aria-label="Afficher les guides" aria-controls={panelId} aria-expanded={open} onClick={() => setOpen(!open)}><ChevronDown size={17} className={open ? 'rotate-180' : ''} /></button></div>
      <div id={panelId} className={`${open ? 'block' : 'hidden'} mt-5 lg:block`}>
        <label htmlFor={inputId} className="text-xs font-medium text-muted-foreground">Rechercher dans les guides</label>
        <div className="relative mt-2"><Search size={15} className="pointer-events-none absolute left-3 top-3 text-muted-foreground" /><input id={inputId} type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Artistes, factures, MCP…" className="h-10 w-full rounded-xl border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary" /></div>
        {query && <p role="status" className="mt-3 text-xs text-muted-foreground">{articles.length} guide{articles.length > 1 ? 's' : ''} trouvé{articles.length > 1 ? 's' : ''}</p>}
        {!articles.length && <p className="mt-4 text-sm text-muted-foreground">Aucun guide trouvé. Essayez un autre mot ou <Link className="underline" href="/contact">contactez-nous</Link>.</p>}
        <nav aria-label="Sommaire de la documentation" className="mt-5 space-y-5">{docCategories.map(category => {
          const items = articles.filter(article => article.category === category);
          return items.length ? <div key={category}><p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{category}</p><ul className="space-y-1">{items.map(article => <li key={article.slug}><Link href={`/doc/${article.slug}`} onClick={() => setOpen(false)} aria-current={pathname === `/doc/${article.slug}` ? 'page' : undefined} className={`block rounded-lg px-2.5 py-2 text-xs leading-relaxed transition-colors ${pathname === `/doc/${article.slug}` ? 'bg-primary/[0.08] font-medium text-primary' : 'text-muted-foreground hover:bg-background hover:text-foreground'}`}>{article.title}</Link></li>)}</ul></div> : null;
        })}</nav>
      </div>
    </div>
  </aside>;
}
