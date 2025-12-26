"use client";

import { useEffect } from "react";
import { useOnboarding, OnboardingStep } from "./OnboardingContext";

// Tutoriel d'onboarding du dashboard - étapes simplifiées et claires
const DASHBOARD_STEPS: OnboardingStep[] = [
  {
    id: "welcome",
    target: "[data-onboarding='stats-cards']",
    title: "Bienvenue sur Radar ! 🎯",
    description:
      "Radar vous aide à détecter les meilleures opportunités pour votre activité musicale. Ces cartes affichent vos statistiques clés : opportunités totales, nouvelles, urgentes et score moyen.",
    position: "bottom",
  },
  {
    id: "collect-button",
    target: "[data-onboarding='collect-button']",
    title: "Lancer une collecte",
    description:
      "Cliquez ici pour lancer une recherche d'opportunités. Vous pouvez faire une collecte standard via vos sources configurées, ou utiliser l'IA pour une recherche avancée avec ChatGPT.",
    position: "bottom",
  },
  {
    id: "top-opportunities",
    target: "[data-onboarding='top-opportunities']",
    title: "Meilleures opportunités",
    description:
      "Vos opportunités les mieux notées apparaissent ici. Le score est calculé automatiquement selon la pertinence, le budget, la deadline et d'autres critères.",
    position: "bottom",
  },
  {
    id: "deadlines",
    target: "[data-onboarding='deadlines']",
    title: "Deadlines à venir",
    description:
      "Ne manquez jamais une deadline ! Cette section affiche les opportunités dont la date limite approche. Restez organisé et réactif.",
    position: "bottom",
  },
  {
    id: "sidebar",
    target: "[data-onboarding='sidebar']",
    title: "Navigation",
    description:
      "Le menu de navigation vous donne accès à toutes les fonctionnalités : liste complète des opportunités, gestion des sources de données, et paramètres.",
    position: "right",
  },
  {
    id: "user-menu",
    target: "[data-onboarding='user-menu']",
    title: "Votre profil",
    description:
      "Gérez votre compte, vos préférences et relancez ce tutoriel à tout moment depuis votre menu utilisateur. Vous êtes prêt à commencer ! 🚀",
    position: "top",
  },
];

export function DashboardOnboarding() {
  const { setSteps } = useOnboarding();

  useEffect(() => {
    setSteps(DASHBOARD_STEPS);
  }, [setSteps]);

  return null;
}
