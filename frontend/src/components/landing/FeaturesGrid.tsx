"use client";

import {
  Target,
  FolderKanban,
  HardDrive,
  Calendar,
  FileText,
  BarChart3,
  Sparkles,
  Landmark,
  Music2,
  Eye,
  Inbox,
  Clapperboard,
} from "lucide-react";

const features = [
  {
    icon: Target,
    title: "Pipeline & Deals",
    description: "Kanban visuel pour suivre vos opportunités du premier contact au closing. Scoring et priorisation automatiques.",
  },
  {
    icon: FolderKanban,
    title: "Projets & Production",
    description: "Phases, tâches, livrables et validations clients. Suivi de production en temps réel avec assets centralisés.",
  },
  {
    icon: FileText,
    title: "Devis & Factures",
    description: "Créez vos devis et factures conformes. Export PDF, sauvegarde automatique sur Google Drive.",
  },
  {
    icon: Music2,
    title: "Découverte Artistes",
    description: "Analysez les artistes avec le scoring IA multicritère. Comparez, suivez les tendances et repérez les talents.",
  },
  {
    icon: BarChart3,
    title: "Analytics & Cockpit",
    description: "Dashboard complet : KPIs, taux de conversion, heatmap deadlines, top performers et prédictions.",
  },
  {
    icon: Eye,
    title: "Veille Concurrentielle",
    description: "Reliez vos événements aux projets, artistes, tâches et documents.",
  },
  {
    icon: HardDrive,
    title: "Google Workspace",
    description: "Drive, Calendar et Gmail synchronisés. Arborescence automatique par projet, templates prêts à l'emploi.",
  },
  {
    icon: Landmark,
    title: "Gestion commerciale",
    description: "Avec Radar Business, gérez les devis, factures et le suivi des paiements.",
  },
];

export function FeaturesGrid() {
  return (
    <section id="produit" className="py-24 bg-white">
      <div className="container mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 rounded-full text-sm text-purple-600 mb-4">
            Plateforme tout-en-un
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Tout ce qu&apos;il faut pour piloter une agence de production
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Un seul outil. Zéro dispersion. Du repérage d&apos;artistes à la facturation.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group bg-white border border-gray-200 rounded-2xl p-6 hover:border-purple-300 hover:shadow-lg transition-all duration-300 card-hover"
            >
              {/* Icon */}
              <div className="h-12 w-12 rounded-xl bg-gradient-to-r from-purple-100 to-purple-50 flex items-center justify-center mb-4 group-hover:from-purple-200 group-hover:to-purple-100 transition-colors">
                <feature.icon className="h-6 w-6 text-purple-600" />
              </div>

              {/* Content */}
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-gray-600 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
