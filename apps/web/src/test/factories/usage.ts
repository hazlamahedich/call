import type { UsageSummary, UsageThreshold } from "@call/types";

export function createUsageSummary(
  overrides: Partial<UsageSummary> = {},
): UsageSummary {
  return {
    used: 500,
    cap: 1000,
    percentage: 50.0,
    plan: "free",
    threshold: "ok",
    ...overrides,
  };
}

export function createUsageSummaryAtThreshold(
  threshold: UsageThreshold,
): UsageSummary {
  const configs: Record<UsageThreshold, Partial<UsageSummary>> = {
    ok: {
      used: 500,
      cap: 1000,
      percentage: 50.0,
      plan: "free",
      threshold: "ok",
    },
    warning: {
      used: 850,
      cap: 1000,
      percentage: 85.0,
      plan: "free",
      threshold: "warning",
    },
    critical: {
      used: 970,
      cap: 1000,
      percentage: 97.0,
      plan: "free",
      threshold: "critical",
    },
    exceeded: {
      used: 1000,
      cap: 1000,
      percentage: 100.0,
      plan: "free",
      threshold: "exceeded",
    },
  };
  return createUsageSummary(configs[threshold]);
}
