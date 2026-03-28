"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface VibeBorderProps extends React.HTMLAttributes<HTMLDivElement> {
  sentiment: "neutral" | "positive" | "hostile";
  reducedMotion?: boolean;
}

const sentimentClasses = {
  neutral: "border-2 border-zinc-700",
  positive: "border-2 border-neon-emerald animate-pulse-emerald",
  hostile: "border-2 border-neon-crimson animate-jitter-crimson",
};

const staticClasses = {
  neutral: "border-2 border-zinc-700",
  positive: "border-2 border-neon-emerald",
  hostile: "border-2 border-neon-crimson",
};

export function VibeBorder({
  sentiment,
  reducedMotion = false,
  className,
  children,
  ...props
}: VibeBorderProps) {
  const borderClass = reducedMotion
    ? staticClasses[sentiment]
    : sentimentClasses[sentiment];

  return (
    <div
      className={cn(borderClass, "rounded-lg transition-colors", className)}
      aria-live="polite"
      aria-label={`Sentiment: ${sentiment}`}
      {...props}
    >
      {children}
    </div>
  );
}
