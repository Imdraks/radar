"use client";

import Link from "next/link";
import { RadarLogo } from "@/components/brand/RadarBrand";
import { ArrowLeft, FileText, Laptop, UserCog, Globe, Copyright, AlertTriangle, Shield, XCircle, RefreshCw, Gavel, Mail } from "lucide-react";

export default function TermsPage() {
  const sections = [
    {
      icon: FileText,
      color: "purple",
      title: "Objet",
      content: (
        <p>
          Les présentes Conditions Générales d&apos;Utilisation (CGU) régissent l&apos;accès et
          l&apos;utilisation de la plateforme Radar, accessible à l&apos;adresse{" "}
          <strong className="text-gray-900">https://radarapp.fr</strong>.
          En utilisant notre service, vous acceptez ces conditions dans leur intégralité.
        </p>
      ),
    },
    {
      icon: Laptop,
      color: "blue",
      title: "Description du service",
      content: (
        <>
          <p>
            Radar est une plateforme de gestion d&apos;opportunités événementielles destinée aux
            professionnels de l&apos;industrie musicale. Le service permet de :
          </p>
          <ul className="mt-3 space-y-2">
            {[
              "Détecter et suivre des opportunités (festivals, événements, appels d'offres)",
              "Gérer des projets et des livrables",
              "Organiser des fichiers via l'intégration Google Drive",
              "Synchroniser des événements avec Google Calendar",
              "Collaborer en équipe au sein d'espaces de travail partagés",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </>
      ),
    },
    {
      icon: UserCog,
      color: "green",
      title: "Accès au service",
      content: (
        <>
          <p>L&apos;accès à Radar nécessite la création d&apos;un compte utilisateur via :</p>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              { name: "Email + mot de passe", desc: "Inscription classique" },
              { name: "Google OAuth", desc: "Connexion rapide et sécurisée" },
            ].map((item) => (
              <div key={item.name} className="flex flex-col rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-semibold text-gray-900">{item.name}</span>
                <span className="text-xs text-gray-500 mt-0.5">{item.desc}</span>
              </div>
            ))}
          </div>
          <p className="mt-3">
            Vous êtes responsable de la confidentialité de vos identifiants
            et de toutes les activités effectuées sous votre compte.
          </p>
        </>
      ),
    },
    {
      icon: Globe,
      color: "orange",
      title: "Utilisation des API Google",
      content: (
        <>
          <p>
            Notre application utilise les API Google conformément aux{" "}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-600 hover:text-purple-700 font-medium"
            >
              Règles relatives aux données utilisateur des services API Google →
            </a>
          </p>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              { name: "Google Drive", desc: "Création de dossiers pour vos projets" },
              { name: "Google Calendar", desc: "Création d'événements pour vos deadlines" },
            ].map((item) => (
              <div key={item.name} className="flex flex-col rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-semibold text-gray-900">{item.name}</span>
                <span className="text-xs text-gray-500 mt-0.5">{item.desc}</span>
              </div>
            ))}
          </div>
          <p className="mt-3">
            Ces intégrations sont optionnelles et activées uniquement avec votre consentement explicite.
            Vous pouvez révoquer ces accès à tout moment depuis les paramètres de votre compte.
          </p>
        </>
      ),
    },
    {
      icon: Copyright,
      color: "red",
      title: "Propriété intellectuelle",
      content: (
        <p>
          Le contenu de la plateforme (interface, logos, textes, code source) est protégé
          par le droit d&apos;auteur. Vous conservez tous les droits sur les données que vous
          importez dans Radar.
        </p>
      ),
    },
    {
      icon: AlertTriangle,
      color: "yellow",
      title: "Responsabilités",
      content: (
        <>
          <p>Radar s&apos;engage à fournir un service de qualité et sécurisé. Cependant :</p>
          <ul className="mt-3 space-y-2">
            {[
              "Le service est fourni \"tel quel\", sans garantie de disponibilité permanente",
              "Nous ne sommes pas responsables des contenus que vous publiez",
              "Les interruptions pour maintenance seront annoncées à l'avance si possible",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-yellow-500 flex-shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </>
      ),
    },
    {
      icon: Shield,
      color: "purple",
      title: "Protection des données",
      content: (
        <p>
          Nous traitons vos données personnelles conformément au RGPD et à notre{" "}
          <Link href="/privacy" className="text-purple-600 hover:text-purple-700 font-medium">
            Politique de Confidentialité
          </Link>.
        </p>
      ),
    },
    {
      icon: XCircle,
      color: "gray",
      title: "Résiliation",
      content: (
        <p>
          Vous pouvez supprimer votre compte à tout moment depuis les paramètres.
          Nous nous réservons le droit de suspendre ou supprimer un compte en cas
          de violation de ces conditions.
        </p>
      ),
    },
    {
      icon: RefreshCw,
      color: "gray",
      title: "Modifications",
      content: (
        <p>
          Ces conditions peuvent être modifiées à tout moment. Les utilisateurs seront
          informés des changements significatifs par email ou notification dans l&apos;application.
        </p>
      ),
    },
    {
      icon: Gavel,
      color: "blue",
      title: "Droit applicable",
      content: (
        <p>
          Ces conditions sont régies par le <strong className="text-gray-900">droit français</strong>.
          Tout litige sera soumis aux tribunaux compétents de Paris.
        </p>
      ),
    },
    {
      icon: Mail,
      color: "green",
      title: "Contact",
      content: (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
            <div className="flex flex-col rounded-lg bg-gray-50 p-3">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Email</span>
              <span className="text-sm text-gray-900 mt-1">contact@radarapp.fr</span>
            </div>
            <div className="flex flex-col rounded-lg bg-gray-50 p-3">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Site</span>
              <span className="text-sm text-gray-900 mt-1">https://radarapp.fr</span>
            </div>
          </div>
          <p>
            Voir également nos{" "}
            <Link href="/legal" className="text-purple-600 hover:text-purple-700 font-medium">
              Mentions Légales
            </Link>{" "}et notre{" "}
            <Link href="/privacy" className="text-purple-600 hover:text-purple-700 font-medium">
              Politique de Confidentialité
            </Link>.
          </p>
        </>
      ),
    },
  ];

  const colorMap: Record<string, { bg: string; text: string }> = {
    purple: { bg: "bg-purple-50", text: "text-purple-600" },
    blue: { bg: "bg-blue-50", text: "text-blue-600" },
    green: { bg: "bg-green-50", text: "text-green-600" },
    orange: { bg: "bg-orange-50", text: "text-orange-600" },
    red: { bg: "bg-red-50", text: "text-red-600" },
    yellow: { bg: "bg-yellow-50", text: "text-yellow-600" },
    gray: { bg: "bg-gray-100", text: "text-gray-600" },
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-6 py-6">
          <Link href="/" aria-label="Radar — Accueil" className="mb-4 block w-fit"><RadarLogo /></Link>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors text-sm"
          >
            <ArrowLeft className="h-4 w-4" />
            Retour à l&apos;accueil
          </Link>
        </div>
      </div>

      <div className="container mx-auto px-6 py-16 max-w-4xl">
        {/* Title */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-50 text-purple-600 text-sm font-medium mb-6">
            <FileText className="h-4 w-4" />
            Conditions d&apos;utilisation
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">
            Conditions Générales d&apos;Utilisation
          </h1>
          <p className="mt-4 text-gray-500 text-sm">
            Dernière mise à jour : 10 avril 2026
          </p>
        </div>

        {/* Content */}
        <div className="space-y-8">
          {sections.map((section, i) => {
            const colors = colorMap[section.color];
            const Icon = section.icon;
            return (
              <section key={i} className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2 rounded-lg ${colors.bg}`}>
                    <Icon className={`h-5 w-5 ${colors.text}`} />
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">{section.title}</h2>
                </div>
                <div className="text-gray-600 text-sm leading-relaxed space-y-2">
                  {section.content}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
