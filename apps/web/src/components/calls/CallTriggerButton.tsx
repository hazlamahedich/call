"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { TriggerCallRequest, TriggerCallResponse } from "@call/types";

interface CallTriggerButtonProps {
  phoneNumber: string;
  leadId?: number;
  agentId?: number;
  campaignId?: number;
  onCallTriggered?: (response: TriggerCallResponse) => void;
  onError?: (error: string) => void;
}

export function CallTriggerButton({
  phoneNumber,
  leadId,
  agentId,
  campaignId,
  onCallTriggered,
  onError,
}: CallTriggerButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrigger = async () => {
    setLoading(true);
    setError(null);

    try {
      const { triggerCall } = await import("@/actions/calls");
      const payload: TriggerCallRequest = {
        phoneNumber,
        leadId,
        agentId,
        campaignId,
      };
      const result = await triggerCall(payload);

      if (result.error) {
        setError(result.error);
        onError?.(result.error);
      } else if (result.data) {
        onCallTriggered?.(result.data);
      }
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Button
        onClick={handleTrigger}
        disabled={loading || !phoneNumber}
        size="md"
        variant="primary"
      >
        {loading ? "Calling..." : "Start Call"}
      </Button>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
