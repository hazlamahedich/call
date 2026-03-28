"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface GlitchPipProps extends React.HTMLAttributes<HTMLDivElement> {
  active: boolean;
  reducedMotion?: boolean;
}

export function GlitchPip({
  active,
  reducedMotion = false,
  className,
  ...props
}: GlitchPipProps) {
  if (reducedMotion || !active) {
    return (
      <div
        className={cn(
          "size-1 shrink-0 rounded-sm",
          active ? "bg-neon-crimson" : "bg-muted",
          className,
        )}
        aria-hidden="true"
        {...props}
      />
    );
  }

  return (
    <div
      className={cn(
        "size-1 shrink-0 rounded-sm animate-glitch-pip",
        "bg-neon-crimson",
        className,
      )}
      aria-hidden="true"
      {...props}
    />
  );
}
