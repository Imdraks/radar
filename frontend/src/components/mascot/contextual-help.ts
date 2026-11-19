import { getDocArticle } from '@/content/documentation';

const topics: [string, string][] = [
  ['/settings/subscription', 'abonnements'], ['/settings/security', 'double-authentification'],
  ['/workspace/settings', 'integrations'], ['/settings', 'securite'],
  ['/projects', 'projets'], ['/production', 'taches-production'],
  ['/agency-calendar', 'calendrier'], ['/assets', 'fichiers'],
  ['/discovery', 'discovery'], ['/comparison', 'selections-comparaison'],
  ['/events', 'evenements'], ['/clients', 'clients-prospects'], ['/leads', 'clients-prospects'],
  ['/devis', 'devis'], ['/quotes', 'devis'], ['/factures', 'factures-paiements'],
  ['/today', 'activite-notifications'], ['/inbox', 'activite-notifications'],
];

export function getRadarHelp(pathname: string, canAccess: boolean) {
  const slug = canAccess ? topics.find(([path]) => pathname === path || pathname.startsWith(path + '/'))?.[1] : undefined;
  const article = getDocArticle(slug || 'demarrer')!;
  return {
    title: article.title,
    description: article.description,
    steps: article.sections.flatMap(section => section.steps || []).slice(0, 5),
    note: article.sections.find(section => section.note)?.note,
    href: `/doc/${article.slug}`,
  };
}
