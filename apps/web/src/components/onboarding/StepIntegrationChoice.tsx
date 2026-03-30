"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  INTEGRATION_OPTIONS,
  type OnboardingOption,
} from "@/lib/onboarding-constants";

interface StepIntegrationChoiceProps {
  value: string;
  onChange: (value: string) => void;
}

export function StepIntegrationChoice({
  value,
  onChange,
}: StepIntegrationChoiceProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">
          Connect your CRM
        </h2>
        <p className="text-sm text-muted-foreground">
          Choose an integration or skip for now.
        </p>
      </div>
      <div
        className="grid gap-3"
        role="radiogroup"
        aria-label="Integration options"
      >
        {INTEGRATION_OPTIONS.map((option: OnboardingOption) => (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={value === option.id}
            onClick={() => onChange(option.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onChange(option.id);
              }
            }}
            className={cn(
              "w-full rounded-lg border p-4 text-left transition-colors",
              "hover:border-emerald-500/50 hover:bg-muted/50",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              value === option.id
                ? "border-emerald-500 bg-emerald-500/10"
                : "border-border bg-card",
            )}
          >
            <div className="font-medium text-foreground">{option.name}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              {option.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
