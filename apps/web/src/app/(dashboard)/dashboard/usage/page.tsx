import { getUsageSummary } from "@/actions/usage";
import { UsageSummary } from "@/components/usage/UsageSummary";

export default async function UsagePage() {
  const { data: summary, error } = await getUsageSummary();

  if (error || !summary) {
    return (
      <div className="p-lg">
        <h1 className="text-lg font-semibold text-foreground mb-md">Usage</h1>
        <p className="text-sm text-muted-foreground">
          {error || "Unable to load usage data"}
        </p>
      </div>
    );
  }

  return (
    <div className="p-lg space-y-lg">
      <h1 className="text-lg font-semibold text-foreground">Usage</h1>
      <UsageSummary summary={summary} />
    </div>
  );
}
