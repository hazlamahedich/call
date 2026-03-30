"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  VOICE_OPTIONS,
  type OnboardingOption,
} from "@/lib/onboarding-constants";

interface StepVoiceSelectionProps {
  value: string;
  onChange: (value: string) => void;
}

export function StepVoiceSelection({
  value,
  onChange,
}: StepVoiceSelectionProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">
          Choose a voice for your agent
        </h2>
        <p className="text-sm text-muted-foreground">
          Select the voice personality that fits your brand.
        </p>
      </div>
      <div
        className="grid grid-cols-2 gap-3"
        role="radiogroup"
        aria-label="Voice options"
      >
        {VOICE_OPTIONS.map((voice: OnboardingOption) => (
          <button
            key={voice.id}
            type="button"
            role="radio"
            aria-checked={value === voice.id}
            onClick={() => onChange(voice.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onChange(voice.id);
              }
            }}
            className={cn(
              "rounded-lg border p-4 text-left transition-colors",
              "hover:border-emerald-500/50 hover:bg-muted/50",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              value === voice.id
                ? "border-emerald-500 bg-emerald-500/10"
                : "border-border bg-card",
            )}
          >
            <div className="font-medium text-foreground">{voice.name}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              {voice.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
