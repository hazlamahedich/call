import { getUsageSummary } from "@/actions/usage";
import { UsageThresholdAlert } from "@/components/usage/UsageThresholdAlert";

export default async function DashboardPage() {
  const { data: summary } = await getUsageSummary();

  return (
    <div className="p-lg space-y-lg">
      {summary && summary.threshold !== "ok" && (
        <UsageThresholdAlert threshold={summary.threshold} />
      )}
      <h1 className="text-lg font-semibold text-foreground">Dashboard</h1>
    </div>
  );
}
