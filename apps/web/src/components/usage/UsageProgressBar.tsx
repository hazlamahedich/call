import * as React from "react";
import { cn } from "@/lib/utils";

export interface UsageProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  percentage: number;
  reducedMotion?: boolean;
}

const BAR_COLORS = {
  ok: "bg-neon-emerald",
  warning: "bg-neon-blue",
  critical: "bg-destructive",
  exceeded: "bg-destructive",
} as const;

function getThreshold(
  percentage: number,
): "ok" | "warning" | "critical" | "exceeded" {
  if (percentage >= 100) return "exceeded";
  if (percentage >= 95) return "critical";
  if (percentage >= 80) return "warning";
  return "ok";
}

const UsageProgressBar = React.forwardRef<
  HTMLDivElement,
  UsageProgressBarProps
>(({ className, percentage, reducedMotion = false, ...props }, ref) => {
  const safePercentage = Number.isFinite(percentage) ? percentage : 0;
  const clampedPercentage = Math.min(100, Math.max(0, safePercentage));
  const threshold = getThreshold(clampedPercentage);
  const barColor = BAR_COLORS[threshold];

  return (
    <div
      ref={ref}
      role="progressbar"
      aria-valuenow={Math.round(clampedPercentage)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Usage: ${Math.round(clampedPercentage)}% of monthly limit`}
      className={cn(
        "relative h-3 w-full overflow-hidden rounded-full bg-muted",
        className,
      )}
      {...props}
    >
      <div
        className={cn(
          "h-full rounded-full",
          barColor,
          !reducedMotion && "transition-all duration-500 ease-in-out",
        )}
        style={{ width: `${clampedPercentage}%` }}
      />
    </div>
  );
});
UsageProgressBar.displayName = "UsageProgressBar";

export { UsageProgressBar, getThreshold };
