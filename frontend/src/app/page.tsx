import {
  LandingWrapper,
  LandingHeader,
  Hero,
  Workflow,
  FeaturesGrid,
  WhyRadar,
  Integrations,
  Security,
  FAQ,
  Pricing,
  FinalCTA,
  LandingFooter,
  ForceLightMode,
} from "@/components/landing";

export const metadata = {
  title: "Radar - Le cockpit pour piloter votre agence de production",
  description:
    "Pipeline, projets, facturation, découverte artistes, production et intelligence artistique — intégré à Google Workspace. La plateforme tout-en-un pour les agences de production musicale.",
  keywords: ["agence", "production musicale", "gestion de projet", "pipeline", "CRM", "facturation", "devis", "découverte artistes", "Google Workspace", "analytics"],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Radar - Le cockpit pour piloter votre agence de production",
    description:
      "Pipeline, projets, facturation, découverte artistes et production — intégré à Google Workspace.",
    url: "/",
    type: "website",
    locale: "fr_FR",
    siteName: "Radar",
  },
  twitter: {
    card: "summary_large_image",
    title: "Radar - Le cockpit pour piloter votre agence de production",
    description:
      "Pipeline, projets, facturation, découverte artistes et analytics — la plateforme tout-en-un pour les agences de production musicale.",
  },
};

export default function HomePage() {
  return (
    <ForceLightMode>
      <LandingWrapper>
        <main className="min-h-screen bg-white text-gray-900">
          <LandingHeader />
          <Hero />
          <FeaturesGrid />
          <WhyRadar />
          <Workflow />
          <Integrations />
          <Security />
          <Pricing />
          <FAQ />
          <FinalCTA />
          <LandingFooter />
        </main>
      </LandingWrapper>
    </ForceLightMode>
  );
}
