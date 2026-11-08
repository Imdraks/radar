import { LandingHeader, LandingFooter, ForceLightMode } from '@/components/landing';
import { PlanCatalog } from '@/components/subscription/PlanCatalog';
export default function PricingPage() {
 return <ForceLightMode><div className="radar-public"><LandingHeader /><main className="radar-site-container pt-36 pb-24"><p className="radar-kicker">Les abonnements</p><h1 className="radar-display mt-5">Les bons outils.<br />Le bon périmètre.</h1><p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">Core pour organiser, Premium pour développer vos parcours métier, Business pour piloter votre activité commerciale.</p><div className="mt-12"><PlanCatalog /></div></main><LandingFooter /></div></ForceLightMode>;
}
