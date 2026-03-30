import type { UsageThreshold } from "@call/types";
import { StatusMessage } from "@/components/ui/status-message";
import { THRESHOLD_LABELS } from "@/lib/usage-constants";

export interface UsageThresholdAlertProps {
  threshold: UsageThreshold;
}

export function UsageThresholdAlert({ threshold }: UsageThresholdAlertProps) {
  if (threshold === "ok") return null;

  const variant = threshold === "warning" ? "warning" : "error";

  return (
    <StatusMessage variant={variant}>
      {THRESHOLD_LABELS[threshold]}
    </StatusMessage>
  );
}
