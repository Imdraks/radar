'use client';
import { PlanCatalog } from '@/components/subscription/PlanCatalog';
export function Pricing() {
  return <section id="pricing" className="py-16 bg-gray-50 text-gray-900"><div className="max-w-6xl mx-auto px-6 space-y-8"><h2 className="text-3xl font-semibold">Des offres adaptées à votre agence</h2><PlanCatalog /></div></section>;
}
