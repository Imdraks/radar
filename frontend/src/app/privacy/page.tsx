"use client";

import Link from "next/link";
import legal from "@/config/legal.json";
import { RadarLogo } from "@/components/brand/RadarBrand";
import { ArrowLeft, Shield, Database, Settings, Globe, Lock, UserCheck, Cookie, Mail, RefreshCw } from "lucide-react";

export default function PrivacyPage() {
  const sections = [
    {
      icon: Shield,
      color: "purple",
      title: "Introduction",
      content: (
        <p>
          Radar (&quot;nous&quot;, &quot;notre&quot;, &quot;nos&quot;) s&apos;engage à protéger la vie privée des utilisateurs
          de notre plateforme accessible à l&apos;adresse{" "}
          <strong className="text-gray-900">https://radarapp.fr</strong>. Cette politique
          de confidentialité explique comment nous collectons, utilisons et protégeons vos
          informations personnelles.
        </p>
      ),
    },
    {
      icon: Database,
      color: "blue",
      title: "Données collectées",
      content: (
        <>
          <p>Nous collectons les types de données suivants :</p>
          <ul className="mt-3 space-y-2">
            {[
              "Informations de compte : nom, adresse e-mail",
              "Données d'authentification via Google OAuth",
              "Données d'utilisation de la plateforme",
              "Informations relatives à vos projets et clients",
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
      icon: Settings,
      color: "green",
      title: "Utilisation des données",
      content: (
        <>
          <p>Vos données sont utilisées pour :</p>
          <ul className="mt-3 space-y-2">
            {[
              "Fournir et améliorer nos services",
              "Authentifier votre accès à la plateforme",
              "Synchroniser avec Google Drive et Google Calendar (si autorisé)",
              "Vous envoyer des notifications relatives à votre compte",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-green-500 flex-shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </>
      ),
    },
    {
      icon: Globe,
      color: "orange",
      title: "Intégrations Google",
      content: (
        <>
          <p>Notre application utilise les API Google pour les fonctionnalités suivantes :</p>
          <div className="mt-3 grid gap-2">
            {[
              { name: "Google OAuth", desc: "Connexion sécurisée à votre compte" },
              { name: "Google Drive", desc: "Stockage et organisation de vos fichiers projets" },
              { name: "Google Calendar", desc: "Synchronisation de vos événements" },
            ].map((item) => (
              <div key={item.name} className="flex items-center gap-3 rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-semibold text-gray-900">{item.name}</span>
                <span className="text-sm text-gray-500">— {item.desc}</span>
              </div>
            ))}
          </div>
          <p className="mt-3">
            Les intégrations que vous activez transmettent les données nécessaires aux prestataires concernés. Les services, finalités, lieux de traitement et garanties applicables doivent figurer dans l’accord de traitement des données de votre organisation.
          </p>
        </>
      ),
    },
    {
      icon: Lock,
      color: "red",
      title: "Stockage et sécurité",
      content: (
        <p>
          Le lieu d’hébergement et les sous-traitants sont précisés dans les informations contractuelles de l’instance. Aucun hébergement en Europe n’est garanti par cette version de validation.
          Nous utilisons le chiffrement SSL/TLS pour toutes les communications
          et appliquons les meilleures pratiques de sécurité pour protéger vos informations.
        </p>
      ),
    },
    {
      icon: UserCheck,
      color: "purple",
      title: "Vos droits (RGPD)",
      content: (
        <>
          <p>Conformément au RGPD, vous disposez des droits suivants :</p>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              "Droit d'accès",
              "Droit de rectification",
              "Droit à l'effacement",
              "Droit à la portabilité",
              "Droit d'opposition",
            ].map((right) => (
              <div key={right} className="flex items-center gap-2 rounded-lg bg-gray-50 p-3">
                <UserCheck className="h-4 w-4 text-purple-500 flex-shrink-0" />
                <span className="text-sm">{right}</span>
              </div>
            ))}
          </div>
          <p className="mt-3">
            Pour exercer ces droits : <strong className="text-gray-900">{legal.privacyContact || legal.contactEmail || "Contact à renseigner"}</strong>
          </p>
        </>
      ),
    },
    {
      icon: Cookie,
      color: "yellow",
      title: "Cookies",
      content: (
        <>
          <p>
            Nous utilisons des <strong className="text-gray-900">cookies essentiels</strong> pour
            le fonctionnement de la plateforme (authentification, préférences utilisateur).
          </p>
          <p className="mt-3">
            Nous utilisons également <strong className="text-gray-900">Google Analytics (GA4)</strong> à
            des fins de mesure d&apos;audience. Ces cookies analytiques ne sont déposés qu&apos;après votre
            consentement explicite via le bandeau de gestion des cookies, conformément au RGPD
            et aux recommandations de la CNIL.
          </p>
          <p className="mt-3">
            Vous pouvez modifier vos choix à tout moment en supprimant vos cookies
            et en rechargeant la page.
          </p>
        </>
      ),
    },
    {
      icon: Mail,
      color: "blue",
      title: "Contact",
      content: (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
            <div className="flex flex-col rounded-lg bg-gray-50 p-3">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Email</span>
              <span className="text-sm text-gray-900 mt-1">{legal.privacyContact || legal.contactEmail || "Contact à renseigner"}</span>
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
            </Link>{" "}et nos{" "}
            <Link href="/terms" className="text-purple-600 hover:text-purple-700 font-medium">
              Conditions Générales d&apos;Utilisation
            </Link>.
          </p>
        </>
      ),
    },
    {
      icon: RefreshCw,
      color: "gray",
      title: "Modifications",
      content: (
        <p>
          Cette politique de confidentialité peut être mise à jour occasionnellement.
          Les modifications seront publiées sur cette page.
        </p>
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
            <Shield className="h-4 w-4" />
            Confidentialité
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">
            Politique de Confidentialité
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
