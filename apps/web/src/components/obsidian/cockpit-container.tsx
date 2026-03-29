"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface CockpitContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  active?: boolean;
  onBootComplete?: () => void;
  reducedMotion?: boolean;
}

export function CockpitContainer({
  active = false,
  onBootComplete,
  reducedMotion = false,
  className,
  children,
  ...props
}: CockpitContainerProps) {
  const [booted, setBooted] = React.useState(false);
  const onBootCompleteRef = React.useRef(onBootComplete);
  onBootCompleteRef.current = onBootComplete;

  React.useEffect(() => {
    if (!active) {
      setBooted(false);
      return;
    }
    if (!booted) {
      const timer = setTimeout(() => {
        setBooted(true);
        onBootCompleteRef.current?.();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [active, booted]);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg border border-border",
        "bg-card/40 backdrop-blur-md shadow-[0_0_30px_rgba(0,0,0,0.3)]",
        !reducedMotion && active && !booted && "animate-boot-glow",
        className,
      )}
      {...props}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-5"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "25% 25%",
        }}
      />
      {children}
    </div>
  );
}
