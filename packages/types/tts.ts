import type { TenantScoped } from "./tenant";

export interface TTSRequest extends TenantScoped {
  id: number;
  callId: number;
  vapiCallId: string;
  provider: "elevenlabs" | "cartesia";
  voiceId: string;
  textLength: number;
  latencyMs: number | null;
  status: "success" | "timeout" | "error" | "all_failed";
  errorMessage: string | null;
  receivedAt: string;
  vapiEventTimestamp: number | null;
}

export interface TTSProviderSwitch extends TenantScoped {
  id: number;
  callId: number;
  vapiCallId: string;
  fromProvider: string;
  toProvider: string;
  reason: string;
  consecutiveSlowCount: number;
  lastLatencyMs: number | null;
  switchedAt: string;
}
