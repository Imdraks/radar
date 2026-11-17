import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, BookOpen, Compass, MessageSquare, Wrench } from 'lucide-react';
import { documentation, docCategories } from '@/content/documentation';

export const metadata: Metadata = {
  title: 'Documentation Radar — Guides et aide',
  description: 'Les guides de Radar : projets, production, artistes, événements, CRM, factures, abonnements et connexion ChatGPT / MCP.',
  alternates: { canonical: '/doc' },
};

export default function DocumentationPage() {
  return <>
    <header className="rounded-3xl border border-primary/10 bg-white p-6 sm:p-10"><p className="radar-kicker"><BookOpen size={15} />Le centre de repères</p><h1 className="mt-5 text-3xl font-semibold tracking-[-0.045em] sm:text-5xl">Bien prendre Radar en main.</h1><p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground">Du premier projet à la recherche artistique, retrouvez les parcours, les conditions d’accès et les limites de chaque outil.</p><Link href="/doc/demarrer" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary">Commencer avec Radar<ArrowRight size={16} /></Link></header>
    <div className="mt-6 grid gap-4 md:grid-cols-3">{[
      { title: 'Vos premiers pas', text: 'Compte, équipe et premier projet.', href: '/doc/demarrer', icon: Compass },
      { title: 'Radar dans ChatGPT', text: 'Connexion, outils et autorisations.', href: '/doc/mcp', icon: MessageSquare },
      { title: 'Besoin d’un dépannage ?', text: 'Les vérifications à effectuer.', href: '/doc/depannage', icon: Wrench },
    ].map(({ title, text, href, icon: Icon }) => <Link key={href} href={href} className="radar-domain-card rounded-2xl border bg-white p-5"><Icon size={20} className="text-primary" /><h2 className="mt-4 text-sm font-semibold">{title}</h2><p className="mt-2 text-xs leading-relaxed text-muted-foreground">{text}</p></Link>)}</div>
    <div className="mt-12 space-y-10">{docCategories.map(category => <section key={category}><h2 className="mb-4 text-lg font-semibold tracking-tight">{category}</h2><div className="grid gap-4 xl:grid-cols-2">{documentation.filter(article => article.category === category).map(article => <Link key={article.slug} href={`/doc/${article.slug}`} className="radar-domain-card group flex items-start justify-between gap-4 rounded-2xl border bg-white p-5"><div><h3 className="text-sm font-semibold group-hover:text-primary">{article.title}</h3><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{article.description}</p></div><ArrowRight size={16} className="mt-1 shrink-0 text-primary" /></Link>)}</div></section>)}</div>
    <div className="mt-12 rounded-2xl border p-6"><h2 className="font-semibold">Une question liée à votre agence ?</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Les fonctions disponibles dépendent de votre rôle, de l’offre et des intégrations connectées à votre workspace.</p><Link href="/contact" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-primary">Contacter l’équipe<ArrowRight size={15} /></Link></div>
  </>;
}
