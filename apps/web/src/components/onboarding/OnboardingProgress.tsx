"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

const STEP_LABELS = [
  "Business Goal",
  "Script Context",
  "Voice Selection",
  "Integration",
  "Safety Level",
];

interface OnboardingProgressProps {
  currentStep: number;
  totalSteps?: number;
  reducedMotion?: boolean;
}

export function OnboardingProgress({
  currentStep,
  totalSteps = 5,
  reducedMotion = false,
}: OnboardingProgressProps) {
  return (
    <div
      className="flex flex-col items-center gap-2"
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={1}
      aria-valuemax={totalSteps}
      aria-label={`Onboarding progress: Step ${currentStep} of ${totalSteps}`}
    >
      <div className="flex items-center gap-2">
        {Array.from({ length: totalSteps }, (_, i) => {
          const step = i + 1;
          const isCompleted = step < currentStep;
          const isActive = step === currentStep;
          const isUpcoming = step > currentStep;

          return (
            <React.Fragment key={step}>
              <div
                className={cn(
                  "flex h-3 w-3 items-center justify-center rounded-full",
                  !reducedMotion && "transition-all duration-300",
                  isCompleted && "bg-emerald-500",
                  isActive && "bg-emerald-500 ring-2 ring-emerald-500/30",
                  isUpcoming && "bg-zinc-700",
                )}
                aria-label={`Step ${step}: ${STEP_LABELS[i]}${isCompleted ? " (completed)" : isActive ? " (current)" : ""}`}
              />
              {step < totalSteps && (
                <div
                  className={cn(
                    "h-px w-8",
                    !reducedMotion && "transition-all duration-300",
                    step < currentStep ? "bg-emerald-500" : "bg-zinc-700",
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
      <div className="text-xs text-muted-foreground">
        Step {currentStep} of {totalSteps}: {STEP_LABELS[currentStep - 1]}
      </div>
    </div>
  );
}
