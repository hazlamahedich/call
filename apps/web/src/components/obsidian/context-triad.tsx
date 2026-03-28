import * as React from "react";
import { cn } from "@/lib/utils";

export interface ContextTriadProps extends React.HTMLAttributes<HTMLDivElement> {
  why: string;
  mood: string;
  target: string;
}

export function ContextTriad({
  why,
  mood,
  target,
  className,
  ...props
}: ContextTriadProps) {
  const bullets = [
    { label: "WHY", value: why },
    { label: "MOOD", value: mood },
    { label: "TARGET", value: target },
  ];

  return (
    <div className={cn("space-y-xs", className)} {...props}>
      {bullets.map((bullet) => (
        <div key={bullet.label} className="flex items-baseline gap-sm">
          <span className="text-muted-foreground uppercase tracking-[0.05em] font-mono text-xs">
            {bullet.label}:
          </span>
          <span className="text-foreground font-mono text-sm">
            {bullet.value}
          </span>
        </div>
      ))}
    </div>
  );
}
