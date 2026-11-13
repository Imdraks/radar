"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

const faqs = [
  {
    question: "Radar est-il ouvert à tout le monde ?",
    answer:
      "Non. Radar est conçu pour un usage agence. L'accès se fait par création d'un espace ou sur invitation, afin de garantir une expérience cohérente et professionnelle. Ce n'est pas un outil grand public.",
  },
  {
    question: "Qui peut utiliser Radar ?",
    answer:
      "Radar s'adresse aux agences de production, studios créatifs et équipes qui gèrent des projets clients au quotidien. Chaque équipe dispose de son propre espace sécurisé (workspace) avec des données totalement isolées.",
  },
  {
    question: "Qu'est-ce qui est synchronisé avec Google Workspace ?",
    answer:
      "Radar se connecte à Google Drive pour créer automatiquement l'arborescence de vos projets et sauvegarder vos devis et factures en PDF. Il synchronise également vos deadlines et rendez-vous avec Google Calendar.",
  },
  {
    question: "Comment fonctionne la facturation ?",
    answer:
      "Radar Business conserve la création de devis, factures et PDF. La transmission réglementaire de factures électroniques nécessite une intégration spécialisée ; sa conformité complète n’est pas encore validée.",
  },
  {
    question: "Comment fonctionne le scoring IA des leads ?",
    answer:
      "Le scoring analyse plusieurs critères : budget estimé, deadline, correspondance avec vos services, localisation, etc. Radar attribue un score de 0 à 100 pour prioriser vos opportunités. Le dashboard analytics vous montre les taux de conversion et tendances.",
  },
  {
    question: "Comment fonctionne la connexion bancaire ?",
    answer:
      "Les connexions bancaires avancées sont suspendues pendant leur validation technique et commerciale. Le suivi des paiements reste dans Radar Business.",
  },
  {
    question: "Comment gérer les rôles et permissions ?",
    answer:
      "Radar propose 4 rôles : Admin (accès total), BizDev (pipeline, leads), PM (projets, production) et Viewer (lecture seule). Chaque membre ne voit que ce qui le concerne.",
  },
  {
    question: "Peut-on importer des données depuis d'autres outils ?",
    answer:
      "Oui, vous pouvez importer vos clients et projets via fichier CSV. L'import depuis Notion et Airtable est en cours de développement.",
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section id="faq" className="py-24 bg-gray-50">
      <div className="container mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 rounded-full text-sm text-purple-600 mb-4">
            FAQ
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Questions fréquentes
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Tout ce que vous devez savoir avant de commencer avec Radar.
          </p>
        </div>

        {/* FAQ Items */}
        <div className="max-w-3xl mx-auto space-y-4">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className="bg-white border border-gray-200 rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full flex items-center justify-between p-5 text-left hover:bg-gray-50 transition-colors"
              >
                <span className="font-medium text-gray-900 pr-4">{faq.question}</span>
                <ChevronDown
                  className={`h-5 w-5 text-gray-500 flex-shrink-0 transition-transform duration-200 ${
                    openIndex === index ? "rotate-180" : ""
                  }`}
                />
              </button>
              {openIndex === index && (
                <div className="px-5 pb-5">
                  <p className="text-gray-600 leading-relaxed">{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
