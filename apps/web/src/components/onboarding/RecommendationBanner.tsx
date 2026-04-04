"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface RecommendationBannerProps {
  presetName: string;
  improvementPct: number;
  reasoning: string;
  onApply: () => void;
  onDismiss: () => void;
}

export function RecommendationBanner({
  presetName,
  improvementPct,
  reasoning,
  onApply,
  onDismiss,
}: RecommendationBannerProps) {
  return (
    <div className="relative rounded-lg border border-blue-500/50 bg-blue-500/10 p-4">
      <button
        type="button"
        onClick={onDismiss}
        className="absolute right-2 top-2 text-blue-600 hover:text-blue-800"
        aria-label="Dismiss recommendation"
      >
        ✕
      </button>

      <div className="space-y-2 pr-6">
        <div className="flex items-start gap-2">
          <span className="text-2xl">💡</span>
          <div className="flex-1">
            <h3 className="font-semibold text-blue-900 dark:text-blue-100">
              Performance-Based Recommendation
            </h3>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              Based on your call performance data
            </p>
          </div>
        </div>

        <div className="rounded-md bg-blue-500/20 p-3">
          <p className="text-sm text-blue-900 dark:text-blue-100">
            <span className="font-semibold">"{presetName}"</span> may achieve{" "}
            <span className="font-bold text-blue-700 dark:text-blue-300">
              {improvementPct}% better pickup rates
            </span>{" "}
            compared to your current preset.
          </p>
          <p className="mt-1 text-xs text-blue-700 dark:text-blue-300">
            Reasoning: {reasoning}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onApply}
            className={cn(
              "rounded-md px-4 py-2 text-sm font-medium transition-colors",
              "bg-blue-600 text-white hover:bg-blue-700"
            )}
          >
            Apply Recommendation
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className={cn(
              "rounded-md px-4 py-2 text-sm font-medium transition-colors",
              "bg-transparent text-blue-700 hover:bg-blue-500/20",
              "dark:text-blue-300 dark:hover:bg-blue-500/30"
            )}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
