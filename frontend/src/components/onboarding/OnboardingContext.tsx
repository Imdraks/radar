"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { ConfettiCelebration } from "./ConfettiCelebration";

export interface OnboardingStep {
  id: string;
  target: string; // CSS selector
  title: string;
  description: string;
  position?: "top" | "bottom" | "left" | "right";
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface OnboardingContextType {
  helpOpen: boolean;
  openHelp: () => void;
  closeHelp: () => void;
  guideOpen: boolean;
  openGuide: () => void;
  closeGuide: () => void;
  isActive: boolean;
  currentStep: number;
  steps: OnboardingStep[];
  hasCompletedOnboarding: boolean;
  showCelebration: boolean;
  startOnboarding: () => void;
  endOnboarding: () => void;
  nextStep: () => void;
  prevStep: () => void;
  skipOnboarding: () => void;
  resetOnboarding: () => void;
  setSteps: (steps: OnboardingStep[]) => void;
}

const OnboardingContext = createContext<OnboardingContextType | null>(null);

const ONBOARDING_STORAGE_KEY = "opportunities-radar-onboarding-completed";
const ONBOARDING_VERSION = "2.0"; // Increment to re-show onboarding after updates

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [guideOpen, setGuideOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const openHelp = useCallback(() => {
    setGuideOpen(false); setIsActive(false); setHelpOpen(true);
    try { localStorage.setItem("opportunities-radar-welcome-shown-v2", "true"); } catch { /* Manual help works without storage. */ }
  }, []);
  const closeHelp = useCallback(() => setHelpOpen(false), []);
  const [isActive, setIsActive] = useState(false);
  const openGuide = useCallback(() => { setIsActive(false); setHelpOpen(false); setGuideOpen(true); }, []);
  const closeGuide = useCallback(() => {
    setGuideOpen(false);
    try { localStorage.setItem("opportunities-radar-welcome-shown-v2", "true"); } catch { /* Guide remains usable without storage. */ }
  }, []);
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<OnboardingStep[]>([]);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(true);
  const [showCelebration, setShowCelebration] = useState(false);

  // Check if user has completed onboarding
  useEffect(() => {
    let stored: string | null;
    try { stored = localStorage.getItem(ONBOARDING_STORAGE_KEY); } catch { return; }
    if (stored) {
      try {
        const data = JSON.parse(stored);
        setHasCompletedOnboarding(data.version === ONBOARDING_VERSION && data.completed);
      } catch {
        setHasCompletedOnboarding(false);
      }
    } else {
      setHasCompletedOnboarding(false);
    }
  }, []);

  // Onboarding is now triggered manually via WelcomeModal button
  // No auto-start to avoid modal overlap

  const startOnboarding = useCallback(() => {
    setGuideOpen(false);
    setHelpOpen(false);
    setCurrentStep(0);
    setIsActive(true);
  }, []);

  const endOnboarding = useCallback(() => {
    setIsActive(false);
    setHasCompletedOnboarding(true);
    setShowCelebration(true); // Trigger confetti celebration
    try {
      localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify({ completed: true, version: ONBOARDING_VERSION }));
    } catch { /* Completion still applies for this session. */ }
  }, []);

  const nextStep = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      endOnboarding();
    }
  }, [currentStep, steps.length, endOnboarding]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  const skipOnboarding = useCallback(() => {
    setIsActive(false);
    setHasCompletedOnboarding(true);
    try {
      localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify({ completed: true, version: ONBOARDING_VERSION }));
    } catch { /* Completion still applies for this session. */ }
  }, []);

  const resetOnboarding = useCallback(() => {
    try { localStorage.removeItem(ONBOARDING_STORAGE_KEY); } catch { /* Reset remains available in memory. */ }
    setHasCompletedOnboarding(false);
    setCurrentStep(0);
  }, []);

  return (
    <OnboardingContext.Provider
      value={{
        helpOpen, openHelp, closeHelp,
        guideOpen, openGuide, closeGuide,
        isActive,
        currentStep,
        steps,
        hasCompletedOnboarding,
        showCelebration,
        startOnboarding,
        endOnboarding,
        nextStep,
        prevStep,
        skipOnboarding,
        resetOnboarding,
        setSteps,
      }}
    >
      {children}
      <ConfettiCelebration 
        isActive={showCelebration} 
        onComplete={() => setShowCelebration(false)} 
      />
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error("useOnboarding must be used within an OnboardingProvider");
  }
  return context;
}
