"use client";

import { Shield, Server, Lock, Users, Eye, FileCheck } from "lucide-react";

const securityFeatures = [
  {
    icon: Server,
    title: "Hébergé en Europe",
    description: "La localisation et les engagements d’hébergement sont précisés dans votre contrat.",
  },
  {
    icon: Shield,
    title: "Protection des données",
    description: "Les conditions de traitement des données sont disponibles auprès de notre équipe.",
  },
  {
    icon: Lock,
    title: "Chiffrement SSL",
    description: "Les échanges utilisent HTTPS lorsque votre instance est déployée avec TLS.",
  },
  {
    icon: Users,
    title: "Rôles & Permissions",
    description: "Contrôlez qui voit quoi. Admin, Manager, Viewer.",
  },
  {
    icon: Eye,
    title: "Audit Trail",
    description: "Les activations d’abonnement conservent leur décision et leur référence d’autorisation.",
  },
  {
    icon: FileCheck,
    title: "Sauvegarde et restauration",
    description: "La politique de sauvegarde dépend de l’exploitation de votre instance.",
  },
];

export function Security() {
  return (
    <section id="securite" className="py-24 bg-white">
      <div className="container mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-100 rounded-full text-sm text-green-700 mb-4">
            <Shield className="h-4 w-4" />
            Sécurité & Conformité
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Vos données en sécurité
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Radar est conçu pour les agences qui prennent la sécurité au sérieux.
            Contrôles d’accès par organisation et autorisations côté serveur.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {securityFeatures.map((feature) => (
            <div
              key={feature.title}
              className="flex items-start gap-4 bg-gray-50 border border-gray-200 rounded-xl p-5 hover:border-green-300 transition-colors"
            >
              <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
                <feature.icon className="h-5 w-5 text-green-700" />
              </div>
              <div>
                <h3 className="text-gray-900 font-semibold mb-1">{feature.title}</h3>
                <p className="text-gray-600 text-sm">{feature.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
