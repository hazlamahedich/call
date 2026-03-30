import type { UsageThreshold } from "@call/types";
import type { PlanType } from "@call/types";

export const THRESHOLD_LABELS: Record<UsageThreshold, string> = {
  ok: "Usage is within normal limits",
  warning: "You've used 80% of your monthly call limit",
  critical: "You've used 95% of your monthly call limit — approaching hard cap",
  exceeded: "Monthly call limit reached — new calls are blocked",
};

export const PLAN_LABELS: Record<PlanType, string> = {
  free: "Seed",
  pro: "Scale",
  enterprise: "Apex",
};
