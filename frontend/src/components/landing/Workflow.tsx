"use client";

import { Target, Sparkles, Rocket, FileText, BarChart3, Music2 } from "lucide-react";

const steps = [
  {
    step: "01",
    icon: Music2,
    title: "Découvrir",
    description: "Repérez les artistes prometteurs. Scoring IA multicritère, analyse de tendances et comparaison.",
    color: "from-blue-500 to-cyan-500",
  },
  {
    step: "02",
    icon: Target,
    title: "Qualifier",
    description: "Pipeline visuel pour qualifier vos opportunités. Priorisez avec le scoring automatique.",
    color: "from-purple-500 to-pink-500",
  },
  {
    step: "03",
    icon: Rocket,
    title: "Produire",
    description: "Gérez projets, tâches et livrables. Validations clients, assets centralisés, suivi en temps réel.",
    color: "from-orange-500 to-red-500",
  },
  {
    step: "04",
    icon: FileText,
    title: "Facturer",
    description: "Devis → Facture → Paiement en quelques clics. PDF conforme, sauvegarde Drive automatique.",
    color: "from-green-500 to-emerald-500",
  },
  {
    step: "05",
    icon: BarChart3,
    title: "Analyser",
    description: "Projets, échéances, événements et sélections artistiques dans un espace commun.",
    color: "from-indigo-500 to-purple-500",
  },
];

export function Workflow() {
  return (
    <section id="workflow" className="py-24 bg-gray-50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-50/50 to-transparent" />
      
      <div className="container mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 rounded-full text-sm text-purple-600 mb-4">
            Workflow
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            De la découverte à l&apos;analyse en{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600">
              5 étapes
            </span>
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Un workflow pensé pour les agences de production. Du repérage d&apos;artistes à l&apos;analyse de performance.
          </p>
        </div>

        {/* Steps */}
        <div className="relative">
          {/* Connection Line - Desktop */}
          <div className="hidden lg:block absolute top-24 left-[10%] right-[10%] h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500 opacity-30" />

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 lg:gap-4">
            {steps.map((step, index) => (
              <div key={step.step} className="relative group">
                {/* Card */}
                <div className="bg-white border border-gray-200 rounded-2xl p-6 h-full hover:border-purple-300 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
                  {/* Step Number */}
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-5xl font-bold text-gray-100 group-hover:text-gray-200 transition-colors">
                      {step.step}
                    </span>
                    <div
                      className={`h-12 w-12 rounded-xl bg-gradient-to-r ${step.color} flex items-center justify-center`}
                    >
                      <step.icon className="h-6 w-6 text-white" />
                    </div>
                  </div>

                  {/* Content */}
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{step.title}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">{step.description}</p>
                </div>

                {/* Arrow - Mobile/Tablet */}
                {index < steps.length - 1 && (
                  <div className="lg:hidden flex justify-center my-4">
                    <svg
                      className="h-6 w-6 text-purple-500/50"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 14l-7 7m0 0l-7-7m7 7V3"
                      />
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
