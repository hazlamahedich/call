import type { PlanType } from "./auth";

export interface UsageSummary {
  used: number;
  cap: number;
  percentage: number;
  plan: PlanType;
  threshold: UsageThreshold;
}

export type UsageThreshold = "ok" | "warning" | "critical" | "exceeded";
