"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState } from "react";
import Link from "next/link";
import legal from "@/config/legal.json";
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
  { value: "", label: "Sélectionnez une offre (optionnel)" },
  { value: "core", label: "Radar Core" },
  { value: "business", label: "Radar Business" },
  { value: "premium", label: "Radar Premium" },
  { value: "custom", label: "Radar Addons — besoin sur mesure" },
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
        body: JSON.stringify({ ...form, privacy_notice_version: "2026-11-13" }),
      });

      if (!res.ok) {
        throw new Error("Erreur serveur");
      }

      setStatus("success");
    } catch {
      setStatus("error");
      setErrorMsg("Le message n’a pas pu être transmis. Consultez le contact publié dans les mentions légales.");
    }
  };

  return (
    <ForceLightMode>
      <LandingWrapper>
        <LandingHeader />

        <main className="radar-public min-h-screen pt-32 pb-20">
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
                  Nous étudions les demandes des professionnels.
                </p>

                <div className="space-y-6">
                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
                      <Mail className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Email</p>
                      <a
                        href={legal.contactEmail ? `mailto:${legal.contactEmail}` : undefined}
                        className="text-purple-600 hover:text-purple-700 text-sm"
                      >
                        {legal.contactEmail || "Contact à renseigner"}
                      </a>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
                      <MapPin className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Localisation</p>
                      <p className="text-gray-600 text-sm">{legal.address || "Adresse à renseigner"}</p>
                    </div>
                  </div>
                </div>

                {/* Trust */}
                <div className="mt-10 p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <p className="text-sm text-gray-600 flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5" /> Demandes professionnelles • Informations de confidentialité accessibles
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
                      Merci pour votre message. Votre demande a été transmise à notre équipe.
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
                          <label htmlFor="contact-name" className="block text-sm font-medium text-gray-700 mb-1.5">
                            Nom complet *
                          </label>
                          <input
                            type="text"
                            required
                            id="contact-name" value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="Jean Dupont"
                          />
                        </div>
                        <div>
                          <label htmlFor="contact-email" className="block text-sm font-medium text-gray-700 mb-1.5">
                            Email professionnel *
                          </label>
                          <input
                            type="email"
                            required
                            id="contact-email" value={form.email}
                            onChange={(e) => setForm({ ...form, email: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="jean@agence.com"
                          />
                        </div>
                      </div>

                      {/* Company + Phone */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label htmlFor="contact-company" className="block text-sm font-medium text-gray-700 mb-1.5">
                            Société
                          </label>
                          <input
                            type="text"
                            id="contact-company" value={form.company}
                            onChange={(e) => setForm({ ...form, company: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="Mon Agence"
                          />
                        </div>
                        <div>
                          <label htmlFor="contact-phone" className="block text-sm font-medium text-gray-700 mb-1.5">
                            Téléphone
                          </label>
                          <input
                            type="tel"
                            id="contact-phone" value={form.phone}
                            onChange={(e) => setForm({ ...form, phone: e.target.value })}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors"
                            placeholder="06 12 34 56 78"
                          />
                        </div>
                      </div>

                      {/* Pack */}
                      <div>
                        <label htmlFor="contact-plan" className="block text-sm font-medium text-gray-700 mb-1.5">
                          Pack qui vous intéresse
                        </label>
                        <select
                          id="contact-plan" value={form.plan}
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
                        <label htmlFor="contact-message" className="block text-sm font-medium text-gray-700 mb-1.5">
                          Message *
                        </label>
                        <textarea
                          required
                          rows={5}
                          id="contact-message" value={form.message}
                          onChange={(e) => setForm({ ...form, message: e.target.value })}
                          className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-colors resize-none"
                          placeholder="Décrivez votre besoin, posez vos questions..."
                        />
                      </div>

                      <p id="contact-privacy" className="text-xs leading-relaxed text-gray-600">Le nom, l’email et le message servent à répondre à votre demande professionnelle. Société, téléphone et offre sont facultatifs. Aucun abonnement à une newsletter n’en découle. N’envoyez ni identifiant secret ni donnée sensible. <Link href="/privacy#contact">Finalités, base juridique, destinataires, conservation et droits</Link>.</p>
                      {/* Error */}
                      {status === "error" && (
                        <p role="alert" className="text-red-600 text-sm">{errorMsg}</p>
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
