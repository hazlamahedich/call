import type { UsageSummary as UsageSummaryType } from "@call/types";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { UsageProgressBar } from "./UsageProgressBar";
import { UsageThresholdAlert } from "./UsageThresholdAlert";
import { PLAN_LABELS } from "@/lib/usage-constants";

export interface UsageSummaryProps {
  summary: UsageSummaryType;
  reducedMotion?: boolean;
}

export function UsageSummary({ summary, reducedMotion }: UsageSummaryProps) {
  const planLabel = PLAN_LABELS[summary.plan] || summary.plan;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage Overview</CardTitle>
        <CardDescription>
          {planLabel} plan — current billing period
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-md">
        <UsageThresholdAlert threshold={summary.threshold} />

        <div className="flex items-baseline justify-between">
          <span className="font-mono text-2xl tabular-nums text-foreground">
            {summary.used.toLocaleString()}
          </span>
          <span className="text-sm text-muted-foreground">
            of{" "}
            <span className="font-mono tabular-nums">
              {summary.cap.toLocaleString()}
            </span>{" "}
            calls
          </span>
        </div>

        <UsageProgressBar
          percentage={summary.percentage}
          reducedMotion={reducedMotion}
        />

        <p className="text-xs text-muted-foreground text-right font-mono tabular-nums">
          {summary.percentage.toFixed(1)}% consumed
        </p>
      </CardContent>
    </Card>
  );
}
