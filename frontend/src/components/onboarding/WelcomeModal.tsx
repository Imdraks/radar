"use client";

import { useState, useEffect } from "react";
import { Rocket, Target, Sparkles, Zap, ArrowRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useOnboarding } from "./OnboardingContext";
import { cn } from "@/lib/utils";

const WELCOME_STORAGE_KEY = "opportunities-radar-welcome-shown-v2";

const features = [
  {
    icon: Target,
    title: "Opportunités intelligentes",
    description: "Détectez automatiquement les appels d'offres et événements pertinents",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
  },
  {
    icon: Sparkles,
    title: "Analyse d'artistes",
    description: "Scoring IA avec données Spotify, réseaux sociaux et historique live",
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
  },
  {
    icon: Zap,
    title: "Enrichissement automatique",
    description: "Labels, management, contacts extraits automatiquement",
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
  },
];

export function WelcomeModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentFeature, setCurrentFeature] = useState(0);
  const { hasCompletedOnboarding, startOnboarding, setSteps } = useOnboarding();

  useEffect(() => {
    // Check if welcome modal has been shown
    const welcomeShown = localStorage.getItem(WELCOME_STORAGE_KEY);
    if (!welcomeShown && !hasCompletedOnboarding) {
      // Delay to let the page load
      const timer = setTimeout(() => setIsOpen(true), 500);
      return () => clearTimeout(timer);
    }
  }, [hasCompletedOnboarding]);

  // Auto-rotate features
  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setCurrentFeature((prev) => (prev + 1) % features.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [isOpen]);

  const handleStartTour = () => {
    localStorage.setItem(WELCOME_STORAGE_KEY, "true");
    setIsOpen(false);
    // Small delay to let modal close animation finish
    setTimeout(() => startOnboarding(), 300);
  };

  const handleSkip = () => {
    localStorage.setItem(WELCOME_STORAGE_KEY, "true");
    setIsOpen(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="sm:max-w-lg overflow-hidden p-0">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-purple-500/5 to-pink-500/5" />
        
        {/* Animated orbs */}
        <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-purple-500/20 rounded-full blur-3xl animate-pulse delay-1000" />

        <div className="relative p-6">
          {/* Close button */}
          <button
            onClick={handleSkip}
            className="absolute top-4 right-4 p-1.5 rounded-full hover:bg-muted transition-colors z-10"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>

          <DialogHeader className="text-center space-y-4">
            {/* Animated logo */}
            <div className="flex justify-center">
              <div className="relative">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shadow-lg animate-bounce-subtle">
                  <Rocket className="h-10 w-10 text-white" />
                </div>
                {/* Sparkle effects */}
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-amber-400 rounded-full animate-ping" />
                <div className="absolute -bottom-1 -left-1 w-3 h-3 bg-pink-400 rounded-full animate-ping delay-500" />
              </div>
            </div>

            <DialogTitle className="text-2xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
              Bienvenue sur Radar 🎯
            </DialogTitle>
            <DialogDescription className="text-base">
              Votre plateforme intelligente pour détecter les meilleures opportunités
              et analyser les artistes en quelques clics.
            </DialogDescription>
          </DialogHeader>

          {/* Feature carousel */}
          <div className="mt-8 mb-6">
            <div className="relative h-[120px] overflow-hidden">
              {features.map((feature, index) => {
                const Icon = feature.icon;
                return (
                  <div
                    key={index}
                    className={cn(
                      "absolute inset-0 flex items-center gap-4 p-4 rounded-xl border bg-card/50 backdrop-blur-sm transition-all duration-500",
                      currentFeature === index
                        ? "opacity-100 translate-x-0"
                        : currentFeature > index
                        ? "opacity-0 -translate-x-full"
                        : "opacity-0 translate-x-full"
                    )}
                  >
                    <div className={cn("p-3 rounded-xl", feature.bgColor)}>
                      <Icon className={cn("h-8 w-8", feature.color)} />
                    </div>
                    <div>
                      <h4 className="font-semibold text-foreground">{feature.title}</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Feature indicators */}
            <div className="flex justify-center gap-2 mt-4">
              {features.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentFeature(index)}
                  className={cn(
                    "w-2 h-2 rounded-full transition-all duration-300",
                    currentFeature === index
                      ? "bg-primary w-6"
                      : "bg-muted hover:bg-muted-foreground/50"
                  )}
                />
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-3">
            <Button
              size="lg"
              className="w-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90 shadow-lg"
              onClick={handleStartTour}
            >
              Démarrer le tutoriel
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              onClick={handleSkip}
            >
              Passer et explorer par moi-même
            </Button>
          </div>

          {/* Keyboard hint */}
          <p className="text-xs text-center text-muted-foreground mt-4">
            Astuce: Utilisez les touches ← → pour naviguer pendant le tutoriel
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
