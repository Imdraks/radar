"use client";

import { Check, FolderOpen, Calendar, Landmark, ArrowRight } from "lucide-react";

const integrations = [
  {
    icon: FolderOpen,
    name: "Google Drive",
    description: "Création automatique d'arborescence projet. Sauvegarde des devis et factures en PDF.",
    features: [
      "Dossier par client et projet",
      "Templates de documents",
      "PDF devis & factures",
    ],
    color: "from-blue-500 to-blue-600",
  },
  {
    icon: Calendar,
    name: "Google Calendar",
    description: "Synchronisation automatique des deadlines et rendez-vous clients.",
    features: [
      "Deadlines projets",
      "Rendez-vous clients",
      "Rappels automatiques",
    ],
    color: "from-green-500 to-emerald-500",
  },

];

export function Integrations() {
  return (
    <section id="integrations" className="py-24 bg-gray-50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-50 to-transparent" />
      
      <div className="container mx-auto px-6 relative z-10">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Content */}
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 rounded-full text-sm text-purple-600 mb-4">
              Intégrations
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Unifié avec{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600">
                vos outils
              </span>
            </h2>
            <p className="text-gray-600 mb-8 text-lg">
              Radar se connecte nativement à Google Workspace.
              Retrouvez les fichiers et calendriers associés à vos projets.
            </p>

            {/* Integration Cards */}
            <div className="space-y-4">
              {integrations.map((integration) => (
                <div
                  key={integration.name}
                  className="bg-white border border-gray-200 rounded-xl p-5 hover:border-purple-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`h-12 w-12 rounded-xl bg-gradient-to-r ${integration.color} flex items-center justify-center flex-shrink-0`}
                    >
                      <integration.icon className="h-6 w-6 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-semibold text-gray-900">{integration.name}</h3>
                      </div>
                      <p className="text-gray-600 text-sm mb-3">{integration.description}</p>
                      <div className="flex flex-wrap gap-2">
                        {integration.features.map((feature) => (
                          <span
                            key={feature}
                            className="inline-flex items-center gap-1 text-xs text-gray-700 bg-gray-100 px-2 py-1 rounded-md"
                          >
                            <Check className="h-3 w-3 text-green-600" />
                            {feature}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Diagram */}
          <div className="relative">
            <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-lg">
              {/* Central Radar */}
              <div className="flex flex-col items-center">
                {/* Google Icons */}
                <div className="flex items-center justify-center gap-8 mb-8">
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-16 w-16 bg-blue-100 rounded-xl flex items-center justify-center">
                      <FolderOpen className="h-8 w-8 text-blue-600" />
                    </div>
                    <span className="text-xs text-gray-600">Drive</span>
                  </div>
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-16 w-16 bg-green-100 rounded-xl flex items-center justify-center">
                      <Calendar className="h-8 w-8 text-green-600" />
                    </div>
                    <span className="text-xs text-gray-600">Calendar</span>
                  </div>
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-16 w-16 bg-purple-100 rounded-xl flex items-center justify-center">
                      <Landmark className="h-8 w-8 text-purple-600" />
                    </div>
                    <span className="text-xs text-gray-600">Banques</span>
                  </div>
                </div>

                {/* Arrows */}
                <div className="flex items-center justify-center gap-4 mb-8">
                  <div className="flex items-center text-purple-500">
                    <ArrowRight className="h-6 w-6 rotate-90" />
                  </div>
                </div>

                {/* Radar Logo */}
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl blur-xl opacity-30" />
                  <div className="relative h-24 w-24 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center">
                    <span className="text-3xl font-bold text-white">R</span>
                  </div>
                </div>

                <div className="mt-6 text-center">
                  <p className="text-gray-900 font-semibold">Radar centralise tout</p>
                  <p className="text-gray-600 text-sm">Une seule interface, zéro dispersion</p>
                </div>
              </div>
            </div>

            {/* Floating badge */}
            <div className="absolute -bottom-4 -right-4 bg-green-500 text-white px-4 py-2 rounded-lg font-medium text-sm shadow-lg">
              ✓ Synchro temps réel
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
