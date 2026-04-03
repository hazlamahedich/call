"use client";

import { useEffect, useState } from "react";
import { getUsageSummary } from "@/actions/usage";
import { UsageThresholdAlert } from "@/components/usage/UsageThresholdAlert";
import type { UsageSummary } from "@call/types";

export default function DashboardPage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  useEffect(() => {
    getUsageSummary()
      .then((result) => result.data && setSummary(result.data))
      .catch(() => {});
  }, []);

  return (
    <div className="p-lg space-y-lg">
      {summary && summary.threshold !== "ok" && (
        <UsageThresholdAlert threshold={summary.threshold} />
      )}
      <h1 className="text-lg font-semibold text-foreground">Dashboard</h1>
    </div>
  );
}
