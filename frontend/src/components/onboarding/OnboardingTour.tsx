"use client";

import { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { X, ChevronLeft, ChevronRight, Sparkles, Rocket, Target, Zap, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useOnboarding } from "./OnboardingContext";
import { cn } from "@/lib/utils";

interface SpotlightPosition {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface TooltipPosition {
  top: number;
  left: number;
  arrowPosition: "top" | "bottom" | "left" | "right";
}

export function OnboardingTour() {
  const { isActive, currentStep, steps, nextStep, prevStep, skipOnboarding } = useOnboarding();
  const [spotlightPos, setSpotlightPos] = useState<SpotlightPosition | null>(null);
  const [tooltipPos, setTooltipPos] = useState<TooltipPosition | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [mounted, setMounted] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Calculate positions when step changes
  useEffect(() => {
    if (!isActive || steps.length === 0) {
      setSpotlightPos(null);
      setTooltipPos(null);
      return;
    }

    const currentStepData = steps[currentStep];
    if (!currentStepData) return;

    const updatePositions = () => {
      const element = document.querySelector(currentStepData.target);
      if (!element) {
        // If element not found, try again after a short delay
        setTimeout(updatePositions, 100);
        return;
      }

      const rect = element.getBoundingClientRect();
      const padding = 8;

      // Calculate spotlight position
      const spotlight: SpotlightPosition = {
        top: rect.top + window.scrollY - padding,
        left: rect.left + window.scrollX - padding,
        width: rect.width + padding * 2,
        height: rect.height + padding * 2,
      };
      setSpotlightPos(spotlight);

      // Calculate tooltip position based on preferred position
      const position = currentStepData.position || "bottom";
      const tooltipWidth = 380;
      const tooltipHeight = 220; // Approximate height including padding
      const gap = 16;

      let tooltip: TooltipPosition;
      let finalPosition = position;
      
      // Check available space and adjust position if needed
      const spaceTop = rect.top;
      const spaceBottom = window.innerHeight - rect.bottom;
      const spaceLeft = rect.left;
      const spaceRight = window.innerWidth - rect.right;
      
      // Auto-adjust position if not enough space
      if (position === "top" && spaceTop < tooltipHeight + gap) {
        finalPosition = "bottom";
      } else if (position === "bottom" && spaceBottom < tooltipHeight + gap) {
        finalPosition = "top";
      } else if (position === "left" && spaceLeft < tooltipWidth + gap) {
        finalPosition = "right";
      } else if (position === "right" && spaceRight < tooltipWidth + gap) {
        finalPosition = "left";
      }

      switch (finalPosition) {
        case "top":
          tooltip = {
            top: rect.top + window.scrollY - tooltipHeight - gap,
            left: rect.left + window.scrollX + rect.width / 2 - tooltipWidth / 2,
            arrowPosition: "bottom",
          };
          break;
        case "left":
          tooltip = {
            top: rect.top + window.scrollY + rect.height / 2 - tooltipHeight / 2,
            left: rect.left + window.scrollX - tooltipWidth - gap,
            arrowPosition: "right",
          };
          break;
        case "right":
          tooltip = {
            top: rect.top + window.scrollY + rect.height / 2 - tooltipHeight / 2,
            left: rect.right + window.scrollX + gap,
            arrowPosition: "left",
          };
          break;
        default: // bottom
          tooltip = {
            top: rect.bottom + window.scrollY + gap,
            left: rect.left + window.scrollX + rect.width / 2 - tooltipWidth / 2,
            arrowPosition: "top",
          };
      }

      // Keep tooltip within viewport - ensure minimum 20px from edges
      tooltip.left = Math.max(20, Math.min(tooltip.left, window.innerWidth - tooltipWidth - 20));
      tooltip.top = Math.max(80, Math.min(tooltip.top, window.innerHeight + window.scrollY - tooltipHeight - 20));

      setTooltipPos(tooltip);

      // Scroll element into view if needed
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    };

    setIsAnimating(true);
    const timer = setTimeout(() => {
      updatePositions();
      setIsAnimating(false);
    }, 150);

    // Update on resize
    window.addEventListener("resize", updatePositions);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", updatePositions);
    };
  }, [isActive, currentStep, steps]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") skipOnboarding();
      if (e.key === "ArrowRight" || e.key === "Enter") nextStep();
      if (e.key === "ArrowLeft") prevStep();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isActive, nextStep, prevStep, skipOnboarding]);

  if (!mounted || !isActive || !spotlightPos || !tooltipPos) return null;

  const currentStepData = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;
  const isFirstStep = currentStep === 0;
  const progress = ((currentStep + 1) / steps.length) * 100;

  const getStepIcon = () => {
    switch (currentStep) {
      case 0:
        return <Rocket className="h-6 w-6" />;
      case 1:
        return <Target className="h-6 w-6" />;
      case 2:
        return <Sparkles className="h-6 w-6" />;
      case 3:
        return <Zap className="h-6 w-6" />;
      default:
        return <CheckCircle2 className="h-6 w-6" />;
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[9999] pointer-events-none">
      {/* Backdrop with spotlight cutout */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-auto"
        style={{ transition: "opacity 0.3s ease" }}
      >
        <defs>
          <mask id="spotlight-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            <rect
              x={spotlightPos.left}
              y={spotlightPos.top}
              width={spotlightPos.width}
              height={spotlightPos.height}
              rx="12"
              fill="black"
              className="transition-all duration-300 ease-out"
            />
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(0, 0, 0, 0.75)"
          mask="url(#spotlight-mask)"
        />
      </svg>

      {/* Subtle spotlight glow - no border */}
      <div
        className="absolute rounded-xl transition-all duration-300 ease-out pointer-events-none shadow-[0_0_30px_rgba(255,255,255,0.15)]"
        style={{
          top: spotlightPos.top,
          left: spotlightPos.left,
          width: spotlightPos.width,
          height: spotlightPos.height,
        }}
      />

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className={cn(
          "absolute w-[380px] pointer-events-auto",
          "transition-all duration-300 ease-out",
          isAnimating ? "opacity-0 scale-95" : "opacity-100 scale-100"
        )}
        style={{
          top: tooltipPos.top,
          left: tooltipPos.left,
        }}
      >
        {/* Arrow */}
        <div
          className={cn(
            "absolute w-4 h-4 bg-card rotate-45 border-primary/20",
            tooltipPos.arrowPosition === "top" && "top-[-8px] left-1/2 -translate-x-1/2 border-t border-l",
            tooltipPos.arrowPosition === "bottom" && "bottom-[-8px] left-1/2 -translate-x-1/2 border-b border-r",
            tooltipPos.arrowPosition === "left" && "left-[-8px] top-1/2 -translate-y-1/2 border-l border-b",
            tooltipPos.arrowPosition === "right" && "right-[-8px] top-1/2 -translate-y-1/2 border-r border-t"
          )}
        />

        {/* Card */}
        <div className="relative bg-card rounded-xl border border-primary/20 shadow-2xl overflow-hidden">
          {/* Animated gradient header */}
          <div className="relative h-2 bg-gradient-to-r from-primary via-purple-500 to-pink-500 bg-[length:200%_100%] animate-gradient" />

          {/* Close button */}
          <button
            onClick={skipOnboarding}
            className="absolute top-4 right-4 p-1.5 rounded-full hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>

          <div className="p-6">
            {/* Step indicator with icon */}
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 text-primary animate-bounce-subtle">
                {getStepIcon()}
              </div>
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Étape {currentStep + 1} sur {steps.length}
                </span>
                <h3 className="text-lg font-semibold text-foreground">
                  {currentStepData.title}
                </h3>
              </div>
            </div>

            {/* Description */}
            <p className="text-muted-foreground text-sm leading-relaxed mb-6">
              {currentStepData.description}
            </p>

            {/* Progress bar */}
            <div className="mb-6">
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-purple-500 transition-all duration-500 ease-out rounded-full"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Action button if defined */}
            {currentStepData.action && (
              <Button
                variant="outline"
                size="sm"
                className="w-full mb-4 border-primary/30 hover:bg-primary/10"
                onClick={() => {
                  currentStepData.action?.onClick();
                  nextStep();
                }}
              >
                {currentStepData.action.label}
              </Button>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="sm"
                onClick={prevStep}
                disabled={isFirstStep}
                className={cn(isFirstStep && "invisible")}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Précédent
              </Button>

              <div className="flex gap-1.5">
                {steps.map((_, index) => (
                  <div
                    key={index}
                    className={cn(
                      "w-2 h-2 rounded-full transition-all duration-300",
                      index === currentStep
                        ? "bg-primary w-6"
                        : index < currentStep
                        ? "bg-primary/50"
                        : "bg-muted"
                    )}
                  />
                ))}
              </div>

              <Button
                size="sm"
                onClick={nextStep}
                className="bg-primary hover:bg-primary/90"
              >
                {isLastStep ? (
                  <>
                    Terminer
                    <CheckCircle2 className="h-4 w-4 ml-1" />
                  </>
                ) : (
                  <>
                    Suivant
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Floating particles animation */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full bg-primary/30 animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${i * 0.5}s`,
              animationDuration: `${3 + Math.random() * 2}s`,
            }}
          />
        ))}
      </div>
    </div>,
    document.body
  );
}
