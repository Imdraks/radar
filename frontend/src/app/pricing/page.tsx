import { LandingHeader, LandingFooter } from '@/components/landing';
import { PlanCatalog } from '@/components/subscription/PlanCatalog';
export default function PricingPage() {
  return <><LandingHeader /><main className="max-w-6xl mx-auto px-6 py-24 space-y-8"><h1 className="text-3xl font-semibold">Les abonnements Radar</h1><PlanCatalog /></main><LandingFooter /></>;
}
