"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState } from "react";
import Link from "next/link";
import {
  Radar,
  Send,
  Mail,
  MapPin,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ForceLightMode } from "@/components/landing/ForceLightMode";
import { LandingWrapper } from "@/components/landing/LandingWrapper";
import { LandingHeader } from "@/components/landing/LandingHeader";
import { LandingFooter } from "@/components/landing/LandingFooter";

const PLAN_OPTIONS = [
  { value: "", label: "Sélectionnez un pack (optionnel)" },
  { value: "core", label: "Radar Core" },
  { value: "business", label: "Radar Business" },
  { value: "talents", label: "Radar Talents" },
  { value: "intelligence", label: "Radar Intelligence" },
  { value: "custom", label: "Offre sur mesure" },
];

export default function ContactPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    phone: "",
    plan: "",
    message: "",
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
      const res = await workspaceFetch(`${apiUrl}/api/v1/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        throw new Error("Erreur serveur");
      }

      setStatus("success");
    } catch {
      setStatus("error");
      setErrorMsg("Une erreur est survenue. Vous pouvez aussi nous écrire à contact@radarapp.fr");
    }
  };

  return (
    <ForceLightMode>
      <LandingWrapper>
        <LandingHeader />

        <main className="min-h-screen bg-gradient-to-b from-white to-gray-50 pt-24 pb-16">
          <div className="container mx-auto px-6 max-w-5xl">
            {/* Back link */}
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors mb-8 text-sm"
            >
              <ArrowLeft className="h-4 w-4" />
              Retour aux abonnements
            </Link>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-12">
              {/* Left side - Info */}
              <div className="lg:col-span-2">
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-10 w-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
                    <Radar className="h-6 w-6 text-white" />
                  </div>
                  <span className="text-2xl font-bold text-gray-900">Radar</span>
                </div>

                <h1 className="text-3xl font-bold text-gray-900 mb-4">
                  Contactez notre équipe
                </h1>
                <p className="text-gray-600 mb-8">
                  Une question sur nos offres ? Besoin d'une démo personnalisée ?
                  Notre équipe vous répond sous 24h.
                </p>

                <div className="space-y-6">
                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
                      <Mail className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Email</p>
                      <a
                        href="mailto:contact@radarapp.fr"
                        className="text-purple-600 hover:text-purple-700 text-sm"
                      >
                        contact@radarapp.fr
                      </a>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
                      <MapPin className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Localisation</p>
                      <p className="text-gray-600 text-sm">Paris, France</p>
                    </div>
                  </div>
                </div>

                {/* Trust */}
                <div className="mt-10 p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <p className="text-sm text-gray-600 flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5" /> Hébergé en France • RGPD conforme • Données chiffrées
                  </p>
                </div>
              </div>

              {/* Right side - Form */}
              <div className="lg:col-span-3">
                {status === "success" ? (
                  <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-10 text-center">
                    <div className="flex justify-center mb-6">
                      <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
                        <CheckCircle2 className="h-8 w-8 text-green-600" />
                      </div>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-3">
                      Message envoyé !
                    </h2>
                    <p className="text-gray-600 mb-6">
                      Merci pour votre message. Notre équipe vous contactera sous 24h.
                    </p>
                    <Link href="/">
                      <Button variant="outline" className="rounded-xl">
                        Retour à l'accueil
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <form
                    onSubmit={handleSubmit}
                    className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8"
                  >
                    <h2 className="text-xl font-semibold text-gray-900 mb-6">
                      Envoyez-nous un message
                    </h2>

                    <div className="space-y-5">
                      {/* Name + Email */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">
                            Nom complet *
                          </label>
                          <input
                            type="text"
                            required
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="Jean Dupont"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">
                            Email professionnel *
                          </label>
                          <input
                            type="email"
                            required
                            value={form.email}
                            onChange={(e) => setForm({ ...form, email: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="jean@agence.com"
                          />
                        </div>
                      </div>

                      {/* Company + Phone */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">
                            Société
                          </label>
                          <input
                            type="text"
                            value={form.company}
                            onChange={(e) => setForm({ ...form, company: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="Mon Agence"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1.5">
                            Téléphone
                          </label>
                          <input
                            type="tel"
                            value={form.phone}
                            onChange={(e) => setForm({ ...form, phone: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="06 12 34 56 78"
                          />
                        </div>
                      </div>

                      {/* Pack */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">
                          Pack qui vous intéresse
                        </label>
                        <select
                          value={form.plan}
                          onChange={(e) => setForm({ ...form, plan: e.target.value })}
                          className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors bg-white"
                        >
                          {PLAN_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Message */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">
                          Message *
                        </label>
                        <textarea
                          required
                          rows={5}
                          value={form.message}
                          onChange={(e) => setForm({ ...form, message: e.target.value })}
                          className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors resize-none"
                          placeholder="Décrivez votre besoin, posez vos questions..."
                        />
                      </div>

                      {/* Error */}
                      {status === "error" && (
                        <p className="text-red-600 text-sm">{errorMsg}</p>
                      )}

                      {/* Submit */}
                      <Button
                        type="submit"
                        disabled={status === "loading"}
                        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white py-3 rounded-xl shadow-lg shadow-purple-500/25"
                      >
                        {status === "loading" ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Envoi en cours...
                          </>
                        ) : (
                          <>
                            <Send className="mr-2 h-4 w-4" />
                            Envoyer le message
                          </>
                        )}
                      </Button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </main>

        <LandingFooter />
      </LandingWrapper>
    </ForceLightMode>
  );
}
