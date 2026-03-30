"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress";
import { StepBusinessGoal } from "@/components/onboarding/StepBusinessGoal";
import { StepScriptContext } from "@/components/onboarding/StepScriptContext";
import { StepVoiceSelection } from "@/components/onboarding/StepVoiceSelection";
import { StepIntegrationChoice } from "@/components/onboarding/StepIntegrationChoice";
import { StepSafetyLevel } from "@/components/onboarding/StepSafetyLevel";
import { completeOnboarding } from "@/actions/onboarding";
import { CockpitContainer } from "@/components/obsidian/cockpit-container";
import type { OnboardingPayload } from "@call/types";

const TOTAL_STEPS = 5;

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = React.useState(1);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [showBootAnimation, setShowBootAnimation] = React.useState(false);

  const [wizardData, setWizardData] = React.useState<OnboardingPayload>({
    businessGoal: "",
    scriptContext: "",
    voiceId: "",
    integrationType: "skip",
    safetyLevel: "strict",
  });

  const [reducedMotion, setReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  const isStepValid = React.useMemo(() => {
    switch (currentStep) {
      case 1:
        return wizardData.businessGoal !== "";
      case 2:
        return wizardData.scriptContext.trim().length >= 20;
      case 3:
        return wizardData.voiceId !== "";
      case 4:
        return wizardData.integrationType !== "";
      case 5:
        return wizardData.safetyLevel !== "";
      default:
        return false;
    }
  }, [currentStep, wizardData]);

  const updateField = <K extends keyof OnboardingPayload>(
    field: K,
    value: OnboardingPayload[K],
  ) => {
    setWizardData((prev) => ({ ...prev, [field]: value }));
  };

  const handleNext = () => {
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((s) => s - 1);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    const { agent, error } = await completeOnboarding(wizardData);
    if (error) {
      setSubmitError(error);
      setIsSubmitting(false);
      return;
    }
    if (agent) {
      setShowBootAnimation(true);
    }
  };

  const handleBootComplete = () => {
    router.push("/dashboard");
  };

  if (showBootAnimation) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-8">
        <div className="w-full max-w-2xl">
          <CockpitContainer
            active={true}
            onBootComplete={handleBootComplete}
            reducedMotion={reducedMotion}
          >
            <div className="p-8 text-center">
              <h1 className="text-2xl font-bold text-foreground">
                System Online
              </h1>
              <p className="mt-2 text-muted-foreground">
                Your AI agent is ready. Entering the cockpit...
              </p>
            </div>
          </CockpitContainer>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-xl space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-foreground">
            Launch Your Agent
          </h1>
          <p className="mt-2 text-muted-foreground">
            Answer 5 quick questions and start dialing in under 10 minutes.
          </p>
        </div>

        <OnboardingProgress
          currentStep={currentStep}
          totalSteps={TOTAL_STEPS}
          reducedMotion={reducedMotion}
        />

        <div className="min-h-[300px]">
          {currentStep === 1 && (
            <StepBusinessGoal
              value={wizardData.businessGoal}
              onChange={(v) => updateField("businessGoal", v)}
            />
          )}
          {currentStep === 2 && (
            <StepScriptContext
              value={wizardData.scriptContext}
              onChange={(v) => updateField("scriptContext", v)}
            />
          )}
          {currentStep === 3 && (
            <StepVoiceSelection
              value={wizardData.voiceId}
              onChange={(v) => updateField("voiceId", v)}
            />
          )}
          {currentStep === 4 && (
            <StepIntegrationChoice
              value={wizardData.integrationType}
              onChange={(v) => updateField("integrationType", v)}
            />
          )}
          {currentStep === 5 && (
            <StepSafetyLevel
              value={wizardData.safetyLevel}
              onChange={(v) => updateField("safetyLevel", v)}
            />
          )}
        </div>

        {submitError && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {submitError}
            <button
              type="button"
              onClick={handleSubmit}
              className="ml-2 underline hover:no-underline"
            >
              Try Again
            </button>
          </div>
        )}

        <div className="flex justify-between">
          <Button
            variant="secondary"
            onClick={handleBack}
            disabled={currentStep === 1}
          >
            Back
          </Button>
          {currentStep < TOTAL_STEPS ? (
            <Button onClick={handleNext} disabled={!isStepValid}>
              Next
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={!isStepValid || isSubmitting}
            >
              {isSubmitting ? "Launching..." : "Launch Agent"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
