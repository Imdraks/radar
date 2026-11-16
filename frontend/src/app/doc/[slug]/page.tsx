import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, ArrowRight, Info } from 'lucide-react';
import { documentation, documentationUpdated, docSectionId, getDocArticle } from '@/content/documentation';

type Props = { params: Promise<{ slug: string }> };
export function generateStaticParams() { return documentation.map(({ slug }) => ({ slug })); }
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const article = getDocArticle((await params).slug);
  return article ? { title: `${article.title} — Documentation`, description: article.description, alternates: { canonical: `/doc/${article.slug}` } } : { title: 'Guide introuvable' };
}

export default async function ArticlePage({ params }: Props) {
  const article = getDocArticle((await params).slug);
  if (!article) notFound();
  const index = documentation.indexOf(article);
  const next = documentation[index + 1];
  return <article className="mx-auto max-w-3xl">
    <nav aria-label="Fil d’Ariane" className="mb-7 flex flex-wrap items-center gap-2 text-xs text-muted-foreground"><Link href="/doc" className="hover:text-primary">Documentation</Link><span aria-hidden="true">/</span><span>{article.category}</span></nav>
    <header className="border-b pb-7"><p className="radar-kicker">Guide Radar</p><h1 className="mt-4 text-3xl font-semibold leading-tight tracking-[-0.04em] sm:text-4xl">{article.title}</h1><p className="mt-4 text-base leading-relaxed text-muted-foreground">{article.description}</p><p className="mt-5 text-xs text-muted-foreground">Mis à jour le <time dateTime={documentationUpdated}>16 novembre 2026</time></p></header>
    <nav aria-label="Dans ce guide" className="my-8 rounded-2xl border bg-white p-5"><p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Dans ce guide</p><ul className="space-y-2">{article.sections.map((section, i) => <li key={section.title}><a href={`#${docSectionId(i)}`} className="text-sm text-primary underline-offset-4 hover:underline">{section.title}</a></li>)}</ul></nav>
    <div className="space-y-10">{article.sections.map((section, i) => <section key={section.title} id={docSectionId(i)} className="scroll-mt-28"><h2 className="mb-4 text-xl font-semibold tracking-tight">{section.title}</h2><div className="space-y-4">{section.paragraphs.map(paragraph => <p key={paragraph} className="text-sm leading-7 text-muted-foreground sm:text-base">{paragraph}</p>)}</div>{section.steps && <ol className="mt-5 list-decimal space-y-3 rounded-2xl border bg-white py-5 pl-11 pr-5 marker:font-semibold marker:text-primary">{section.steps.map(step => <li key={step} className="pl-1 text-sm leading-relaxed">{step}</li>)}</ol>}{section.note && <aside className="mt-5 flex gap-3 rounded-xl border border-primary/15 bg-primary/[0.04] p-4"><Info size={18} className="mt-0.5 shrink-0 text-primary" /><p className="text-sm leading-relaxed">{section.note}</p></aside>}</section>)}</div>
    <section className="mt-12 border-t pt-7"><h2 className="text-sm font-semibold">Pour aller plus loin</h2><ul className="mt-4 flex flex-wrap gap-3">{article.links.map(link => <li key={link.href}><Link href={link.href} className="inline-flex items-center gap-2 rounded-xl border bg-white px-4 py-2.5 text-sm text-primary hover:border-primary/40">{link.label}<ArrowRight size={14} /></Link></li>)}</ul></section>
    <nav aria-label="Parcourir les guides" className="mt-10 flex flex-wrap justify-between gap-4 border-t pt-6 text-sm"><Link href="/doc" className="inline-flex items-center gap-2 text-muted-foreground"><ArrowLeft size={15} />Tous les guides</Link>{next && <Link href={`/doc/${next.slug}`} className="inline-flex items-center gap-2 text-primary">{next.title}<ArrowRight size={15} /></Link>}</nav>
  </article>;
}
