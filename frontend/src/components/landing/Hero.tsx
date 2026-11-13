"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { ArrowRight, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Hero() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) setIsLoggedIn(true);
  }, []);

  return (
    <section className="relative min-h-screen flex items-center pt-24 pb-16 overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-gray-50" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-100 rounded-full blur-3xl opacity-60" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-pink-100 rounded-full blur-3xl opacity-60" />

      <div className="container mx-auto px-6 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Content */}
          <div className="text-center lg:text-left">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-50 rounded-full text-sm text-purple-600 mb-6">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
              </span>
              Pensé pour les agences de production
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-tight text-gray-900 dark:!text-gray-900" style={{ color: '#111827' }}>
              <span style={{ color: '#111827' }}>Le</span>{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600" style={{ color: 'transparent', WebkitBackgroundClip: 'text', backgroundClip: 'text' }}>
                cockpit
              </span>{" "}
              <span style={{ color: '#111827' }}>pour piloter votre agence</span>
            </h1>

            {/* Subheadline - Pain → Solution */}
            <p className="text-lg sm:text-xl text-gray-600 mb-4 max-w-xl mx-auto lg:mx-0">
              Pipeline, projets, facturation, découverte artistes et analytics — tout au même endroit.
            </p>
            <p className="text-lg sm:text-xl text-gray-900 font-medium mb-4 max-w-xl mx-auto lg:mx-0">
              Fin des infos éparpillées entre Drive, Notion et Excel.
            </p>
            {/* Filtre naturel */}
            <p className="text-sm text-gray-500 mb-8 max-w-xl mx-auto lg:mx-0">
              Plateforme privée conçue pour les agences de production musicale.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link href={isLoggedIn ? "/today" : "/login"}>
                <Button
                  size="lg"
                  className="w-full sm:w-auto bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white text-lg px-8 py-6 rounded-xl btn-press"
                >
                  {isLoggedIn ? "Accéder au dashboard" : "Créer un espace"}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/pricing">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto border-gray-300 text-gray-900 hover:bg-gray-100 text-lg px-8 py-6 rounded-xl btn-press"
                >
                  <Eye className="mr-2 h-5 w-5" />
                  Voir les abonnements
                </Button>
              </Link>
            </div>

            {/* Trust badges - Micro-ligne de confiance */}
            <div className="flex flex-wrap items-center gap-4 mt-10 justify-center lg:justify-start text-sm text-gray-500">
              <span>Découverte & Scoring artistes</span>
              <span className="text-gray-300">•</span>
              <span>Devis et factures centralisés</span>
              <span className="text-gray-300">•</span>
              <span>Google Workspace + Banques</span>
              <span className="text-gray-300">•</span>
              <span>Veille concurrentielle</span>
            </div>
          </div>

          {/* Right: Product Screenshot */}
          <div className="relative">
            <div className="relative bg-white rounded-2xl border border-gray-200 shadow-2xl overflow-hidden card-hover">
              {/* Browser Chrome */}
              <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-200">
                <div className="flex gap-1.5">
                  <div className="h-3 w-3 rounded-full bg-red-500/80" />
                  <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
                  <div className="h-3 w-3 rounded-full bg-green-500/80" />
                </div>
                <div className="flex-1 flex justify-center">
                  <div className="px-4 py-1 bg-gray-200 rounded-lg text-xs text-gray-600">
                    radarapp.fr/today
                  </div>
                </div>
              </div>

              {/* Mockup Dashboard - Données fictives */}
              <div className="bg-gray-50 p-4">
                {/* Header Dashboard */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-xs font-bold">R</span>
                    </div>
                    <span className="font-semibold text-gray-900 text-sm">Cockpit</span>
                  </div>
                  <button className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded-lg">
                    + Nouveau projet
                  </button>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-4 gap-2 mb-4">
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="text-[10px] text-gray-500">Projets actifs</div>
                    <div className="text-lg font-bold text-gray-900">7</div>
                  </div>
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="text-[10px] text-gray-500">Validations</div>
                    <div className="text-lg font-bold text-orange-500">3</div>
                  </div>
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="text-[10px] text-gray-500">Factures</div>
                    <div className="text-lg font-bold text-purple-500">12</div>
                  </div>
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="text-[10px] text-gray-500">CA du mois</div>
                    <div className="text-lg font-bold text-gray-900">24k€</div>
                  </div>
                </div>

                {/* Columns */}
                <div className="grid grid-cols-3 gap-2">
                  {/* À faire */}
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-700">À faire</span>
                      <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">4</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="bg-purple-50 border-l-2 border-purple-500 p-1.5 rounded text-[10px]">
                        <div className="font-medium text-gray-800">Maquettes V2</div>
                        <div className="text-gray-500">Studio Neon</div>
                      </div>
                      <div className="bg-gray-50 border-l-2 border-gray-300 p-1.5 rounded text-[10px]">
                        <div className="font-medium text-gray-800">Brief client</div>
                        <div className="text-gray-500">Agence Pulse</div>
                      </div>
                    </div>
                  </div>

                  {/* En cours */}
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-700">En cours</span>
                      <span className="text-[10px] bg-blue-100 px-1.5 py-0.5 rounded text-blue-600">3</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="bg-blue-50 border-l-2 border-blue-500 p-1.5 rounded text-[10px]">
                        <div className="font-medium text-gray-800">Développement</div>
                        <div className="text-gray-500">MediaLab Paris</div>
                      </div>
                      <div className="bg-blue-50 border-l-2 border-blue-500 p-1.5 rounded text-[10px]">
                        <div className="font-medium text-gray-800">Motion design</div>
                        <div className="text-gray-500">Creative House</div>
                      </div>
                    </div>
                  </div>

                  {/* Pipeline */}
                  <div className="bg-white rounded-lg p-2 border border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-700">Pipeline</span>
                      <span className="text-[10px] bg-green-100 px-1.5 py-0.5 rounded text-green-600">66k€</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="bg-green-50 border-l-2 border-green-500 p-1.5 rounded text-[10px]">
                        <div className="font-medium text-gray-800">Refonte e-commerce</div>
                        <div className="text-green-600 font-medium">15 000€</div>
                      </div>
                      <div className="bg-yellow-50 border-l-2 border-yellow-500 p-1.5 rounded text-[10px]">
                        <div className="font-medium text-gray-800">App mobile MVP</div>
                        <div className="text-yellow-600 font-medium">25 000€</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating Elements */}
            <div className="absolute bottom-4 left-4 bg-white rounded-xl shadow-xl p-4 flex items-center gap-3 animate-fade-in z-10">
              <div className="h-10 w-10 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-900">Deal converti</div>
                <div className="text-xs text-gray-500">Projet créé automatiquement</div>
              </div>
            </div>

            <div className="absolute top-4 right-4 bg-white rounded-xl shadow-xl p-4 animate-fade-in z-10">
              <div className="flex items-center gap-2 text-sm">
                <div className="h-8 w-8 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 font-bold text-xs">GD</span>
                </div>
                <div className="text-gray-900 font-medium">Synchro Drive</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
