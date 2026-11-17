"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";

export function FinalCTA() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) setIsLoggedIn(true);
  }, []);

  return (
    <section className="py-24 bg-gradient-to-b from-gray-50 to-white relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-100 rounded-full blur-[120px] opacity-60" />
      </div>

      <div className="container mx-auto px-6 relative z-10">
        <div className="max-w-3xl mx-auto text-center">
          {/* Headline */}
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
            Prêt à centraliser votre agence ?
          </h2>

          {/* Subheadline */}
          <p className="text-lg text-gray-600 mb-10 max-w-xl mx-auto">
            Pipeline, projets, facturation, découverte artistes, analytics — tout au même endroit.
            <br />
            Accès sur création d&apos;espace ou invitation.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href={isLoggedIn ? "/today" : "/login"}>
              <Button
                size="lg"
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white text-lg px-10 py-6 rounded-xl btn-press"
              >
                {isLoggedIn ? "Accéder au dashboard" : "Créer un espace"}
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/pricing">
              <Button
                size="lg"
                variant="outline"
                className="border-gray-300 text-gray-900 hover:bg-gray-100 text-lg px-10 py-6 rounded-xl btn-press"
              >
                <Eye className="mr-2 h-5 w-5" />
                Choisir un abonnement
              </Button>
            </Link>
          </div>

          {/* Trust note */}
          <p className="mt-8 text-sm text-gray-500">
            Organisation • Discovery et analyses indicatives • Intégrations selon configuration
          </p>
        </div>
      </div>
    </section>
  );
}
