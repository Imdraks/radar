"use client";

import Link from "next/link";
import legal from "@/config/legal.json";
import { RadarLogo } from "@/components/brand/RadarBrand";
import { ArrowLeft, Building2, Server, Shield, Cookie, Scale, Gavel, Mail } from "lucide-react";

export default function LegalPage() {
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
            <Scale className="h-4 w-4" />
            Informations légales
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">
            Mentions Légales
          </h1>
          <p className="mt-4 text-gray-500 text-sm">
            Informations de l’instance Radar
          </p>
        </div>

        {/* Content */}
        <div className="space-y-8">
          {/* Éditeur */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-purple-50">
                <Building2 className="h-5 w-5 text-purple-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Éditeur du site</h2>
            </div>
            <p className="text-gray-600 mb-4">
              Le site <strong className="text-gray-900">https://radarapp.fr</strong> est édité par :
            </p>
            {!legal.commercialReleaseEnabled && <p role="status" className="mb-4 rounded-lg bg-amber-50 p-3 text-amber-900">Version de validation : les informations de l’éditeur doivent être renseignées avant toute ouverture commerciale.</p>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                {label:"Raison sociale",value:[legal.companyName,legal.legalForm].filter(Boolean).join(" — ")},
                {label:"Siège social",value:legal.address},
                {label:"SIRET",value:legal.siret},
                {label:"RCS",value:legal.rcs},
                {label:"Capital social",value:legal.capital},
                {label:"Directeur de publication",value:legal.publicationDirector},
                {label:"Email",value:legal.contactEmail},
              ].map((item) => (
                <div key={item.label} className="flex flex-col rounded-lg bg-gray-50 p-3">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{item.label}</span>
                  <span className="text-sm text-gray-900 mt-1">{item.value || "Non renseigné"}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Hébergeur */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-blue-50">
                <Server className="h-5 w-5 text-blue-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Hébergeur</h2>
            </div>
            <div className="rounded-lg bg-gray-50 p-4">
              <p className="font-semibold text-gray-900">{legal.hostingName || "Hébergeur à confirmer"}</p>
              <p className="text-sm text-gray-600 mt-1">{legal.hostingAddress || "Adresse non renseignée"}</p>
              <p className="text-sm text-gray-600">{legal.hostingContact || "Contact non renseigné"}</p>

            </div>
          </section>

          {/* Propriété intellectuelle */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-orange-50">
                <Shield className="h-5 w-5 text-orange-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Propriété intellectuelle</h2>
            </div>
            <div className="space-y-3 text-gray-600 text-sm leading-relaxed">
              <p>
                L&apos;ensemble du contenu du site (textes, images, graphismes, logo, icônes, logiciels,
                base de données) est la propriété exclusive de l&apos;éditeur ou de ses partenaires et est
                protégé par les lois françaises et internationales relatives à la propriété intellectuelle.
              </p>
              <p>
                Toute reproduction, représentation, modification, publication ou adaptation de tout ou
                partie des éléments du site, quel que soit le moyen ou le procédé utilisé, est interdite
                sans autorisation écrite préalable.
              </p>
            </div>
          </section>

          {/* Protection des données */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-green-50">
                <Gavel className="h-5 w-5 text-green-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Protection des données personnelles</h2>
            </div>
            <div className="space-y-3 text-gray-600 text-sm leading-relaxed">
              <p>
                Conformément au Règlement Général sur la Protection des Données (RGPD) et à la loi
                Informatique et Libertés du 6 janvier 1978 modifiée, vous disposez d&apos;un droit d&apos;accès,
                de rectification, de suppression et de portabilité de vos données personnelles.
              </p>
              <p>
                Pour plus d&apos;informations, consultez notre{" "}
                <Link href="/privacy" className="text-purple-600 hover:text-purple-700 font-medium">
                  Politique de Confidentialité
                </Link>.
              </p>
              <p>
                Pour exercer vos droits : <strong className="text-gray-900">{legal.privacyContact || legal.contactEmail || "Contact à renseigner"}</strong>
              </p>
            </div>
          </section>

          {/* Cookies */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-yellow-50">
                <Cookie className="h-5 w-5 text-yellow-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Cookies</h2>
            </div>
            <div className="space-y-3 text-gray-600 text-sm leading-relaxed">
              <p>
                Le site utilise des <strong className="text-gray-900">cookies essentiels</strong> au fonctionnement
                du service (authentification, préférences) ainsi que des <strong className="text-gray-900">cookies
                analytiques</strong> (Google Analytics) soumis à votre consentement via le bandeau cookies.
              </p>
              <p>
                Pour en savoir plus, consultez notre{" "}
                <Link href="/privacy" className="text-purple-600 hover:text-purple-700 font-medium">
                  Politique de Confidentialité
                </Link>.
              </p>
            </div>
          </section>

          {/* Responsabilité */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-red-50">
                <Scale className="h-5 w-5 text-red-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Responsabilité</h2>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed">
              L&apos;éditeur s&apos;efforce de fournir des informations aussi précises que possible.
              Toutefois, il ne pourra être tenu responsable des omissions, des inexactitudes
              et des carences dans la mise à jour, qu&apos;elles soient de son fait ou du fait
              des tiers partenaires qui lui fournissent ces informations.
            </p>
          </section>

          {/* Droit applicable */}
          <section className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-indigo-50">
                <Gavel className="h-5 w-5 text-indigo-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Droit applicable</h2>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed">
              Les présentes mentions légales sont régies par le droit français. En cas de litige,
              les tribunaux français seront seuls compétents.
            </p>
          </section>

          {/* Footer links */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-8 text-sm">
            <Link href="/privacy" className="text-purple-600 hover:text-purple-700 font-medium">
              Politique de Confidentialité
            </Link>
            <span className="text-gray-300">•</span>
            <Link href="/terms" className="text-purple-600 hover:text-purple-700 font-medium">
              Conditions Générales d&apos;Utilisation
            </Link>
            <span className="text-gray-300">•</span>
            <a href={legal.contactEmail ? `mailto:${legal.contactEmail}` : undefined} className="inline-flex items-center gap-1 text-purple-600 hover:text-purple-700 font-medium">
              <Mail className="h-3.5 w-3.5" />
              {legal.contactEmail || "Contact à renseigner"}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
