"use client";

import { Layers, FileText, BarChart3, Shield, Music2, Eye } from "lucide-react";

const reasons = [
  {
    icon: Layers,
    title: "Tout-en-un pour les agences",
    description: "Pipeline, projets, production, facturation, analytics, Drive — plus besoin de jongler entre 10 outils.",
  },
  {
    icon: Music2,
    title: "Découverte & Scoring artistes",
    description: "Analysez, comparez et scorez les artistes automatiquement. Repérez les talents avant tout le monde.",
  },
  {
    icon: Eye,
    title: "Veille & Analytics avancés",
    description: "Organisation, événements et intelligence artistique réunis autour de vos projets.",
  },
  {
    icon: Shield,
    title: "RGPD & hébergement France",
    description: "Données hébergées en France. Rôles et permissions granulaires. Audit trail complet.",
  },
];

export function WhyRadar() {
  return (
    <section className="py-20 bg-gray-50">
      <div className="container mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
            Pourquoi Radar fonctionne
          </h2>
          <p className="text-gray-600 max-w-xl mx-auto">
            Conçu pour les agences de production qui veulent sortir du chaos opérationnel.
          </p>
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {reasons.map((reason) => (
            <div
              key={reason.title}
              className="bg-white rounded-xl p-6 border border-gray-200 card-hover"
            >
              <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center mb-4">
                <reason.icon className="h-5 w-5 text-purple-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">
                {reason.title}
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                {reason.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
