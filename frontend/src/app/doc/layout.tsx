import { PublicPage } from '@/components/landing/PublicPage';
import { DocNavigation } from '@/components/documentation/DocNavigation';

export default function DocLayout({ children }: { children: React.ReactNode }) {
  return <PublicPage><main id="main-content" className="radar-site-container pb-20 pt-28 sm:pt-32"><div className="flex min-w-0 flex-col gap-8 lg:flex-row lg:gap-12"><DocNavigation /><div className="min-w-0 flex-1">{children}</div></div></main></PublicPage>;
}
