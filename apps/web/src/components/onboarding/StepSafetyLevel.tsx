"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  SAFETY_LEVELS,
  type OnboardingOption,
} from "@/lib/onboarding-constants";

interface StepSafetyLevelProps {
  value: string;
  onChange: (value: string) => void;
}

export function StepSafetyLevel({ value, onChange }: StepSafetyLevelProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">
          Set your safety level
        </h2>
        <p className="text-sm text-muted-foreground">
          Control how strictly compliance rules are enforced.
        </p>
      </div>
      <div
        className="grid gap-3"
        role="radiogroup"
        aria-label="Safety level options"
      >
        {SAFETY_LEVELS.map((level: OnboardingOption) => (
          <button
            key={level.id}
            type="button"
            role="radio"
            aria-checked={value === level.id}
            onClick={() => onChange(level.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onChange(level.id);
              }
            }}
            className={cn(
              "w-full rounded-lg border p-4 text-left transition-colors",
              "hover:border-emerald-500/50 hover:bg-muted/50",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              value === level.id
                ? "border-emerald-500 bg-emerald-500/10"
                : "border-border bg-card",
            )}
          >
            <div className="font-medium text-foreground">{level.name}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              {level.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
