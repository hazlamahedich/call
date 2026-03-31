import crypto from "crypto";

const VAPI_WEBHOOK_SECRET =
  process.env.VAPI_WEBHOOK_SECRET ?? "test-webhook-secret";

export function computeVapiSignature(body: string): string {
  return crypto
    .createHmac("sha256", VAPI_WEBHOOK_SECRET)
    .update(body)
    .digest("hex");
}

export function buildWebhookPayload(
  eventType: string,
  overrides: {
    vapiCallId?: string;
    orgId?: string;
    phoneNumber?: string;
    duration?: number;
    recordingUrl?: string;
    errorMessage?: string;
    leadId?: number;
    agentId?: number;
  } = {},
): string {
  const {
    vapiCallId = "call_test_123",
    orgId = "org_test_001",
    phoneNumber = "+1234567890",
    duration,
    recordingUrl,
    errorMessage,
    leadId,
    agentId,
  } = overrides;

  const callData: Record<string, unknown> = {
    id: vapiCallId,
  };

  if (phoneNumber) callData.phoneNumber = phoneNumber;
  if (duration !== undefined) callData.duration = duration;
  if (recordingUrl) callData.recordingUrl = recordingUrl;
  if (errorMessage) {
    callData.error = { message: errorMessage };
  }

  const metadata: Record<string, unknown> = { org_id: orgId };
  if (leadId !== undefined) metadata.lead_id = String(leadId);
  if (agentId !== undefined) metadata.agent_id = String(agentId);

  const payload = {
    message: {
      type: eventType,
      call: callData,
      metadata,
    },
  };

  return JSON.stringify(payload);
}

export function webhookHeaders(body: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "vapi-signature": computeVapiSignature(body),
  };
}
