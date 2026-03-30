"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  BUSINESS_GOALS,
  type OnboardingOption,
} from "@/lib/onboarding-constants";

interface StepBusinessGoalProps {
  value: string;
  onChange: (value: string) => void;
}

export function StepBusinessGoal({ value, onChange }: StepBusinessGoalProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">
          What is your primary business goal?
        </h2>
        <p className="text-sm text-muted-foreground">
          Choose the goal that best matches your use case.
        </p>
      </div>
      <div
        className="grid gap-3"
        role="radiogroup"
        aria-label="Business goal options"
      >
        {BUSINESS_GOALS.map((goal: OnboardingOption) => (
          <button
            key={goal.id}
            type="button"
            role="radio"
            aria-checked={value === goal.id}
            onClick={() => onChange(goal.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onChange(goal.id);
              }
            }}
            className={cn(
              "w-full rounded-lg border p-4 text-left transition-colors",
              "hover:border-emerald-500/50 hover:bg-muted/50",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              value === goal.id
                ? "border-emerald-500 bg-emerald-500/10"
                : "border-border bg-card",
            )}
          >
            <div className="font-medium text-foreground">{goal.name}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              {goal.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
