"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

const MIN_LENGTH = 20;

interface StepScriptContextProps {
  value: string;
  onChange: (value: string) => void;
}

export function StepScriptContext({ value, onChange }: StepScriptContextProps) {
  const isValid = value.trim().length >= MIN_LENGTH;
  const charCount = value.trim().length;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">
          Describe your primary script context
        </h2>
        <p className="text-sm text-muted-foreground">
          Describe your product, service, or offer in a few sentences.
        </p>
      </div>
      <div className="space-y-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="We sell premium widgets to small businesses in the healthcare sector..."
          rows={5}
          className={cn(
            "w-full rounded-lg border border-border bg-card p-4 text-foreground",
            "placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          )}
          aria-label="Script context"
          aria-describedby="char-count"
        />
        <div
          id="char-count"
          className={cn(
            "text-xs",
            isValid ? "text-emerald-500" : "text-muted-foreground",
          )}
        >
          {charCount} / {MIN_LENGTH} minimum characters
        </div>
      </div>
    </div>
  );
}

export { MIN_LENGTH };
