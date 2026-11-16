import { ForceLightMode, LandingHeader, LandingFooter } from '@/components/landing';

export function PublicPage({ children }: { children: React.ReactNode }) {
  return <ForceLightMode><div className="radar-public min-h-screen">
    <a href="#main-content" className="sr-only fixed left-4 top-4 z-50 rounded-xl bg-white p-3 text-primary shadow focus:not-sr-only">Aller au contenu</a>
    <LandingHeader />{children}<LandingFooter />
  </div></ForceLightMode>;
}
