import { test, expect } from "../../support/merged-fixtures";
import {
  buildWebhookPayload,
  webhookHeaders,
} from "../../support/webhook-helpers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

test.describe("[P0] Webhook: call-start Event — AC4", () => {
  test("[2.1-E2E-030][P0] Given valid call-start webhook, When posted with correct signature, Then returns 200 received", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-start", {
      vapiCallId: "call_start_001",
      orgId: "org_wh_test",
      phoneNumber: "+15551112222",
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.received).toBe(true);
  });

  test("[2.1-E2E-031][P1] Given call-start with lead and agent metadata, When processed, Then returns received", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-start", {
      vapiCallId: "call_start_002",
      orgId: "org_wh_meta",
      phoneNumber: "+15553334444",
      leadId: 42,
      agentId: 7,
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
  });
});

test.describe("[P0] Webhook: call-end Event — AC4", () => {
  test("[2.1-E2E-040][P0] Given valid call-end webhook with duration and recording, When posted, Then returns 200 received", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-end", {
      vapiCallId: "call_end_001",
      orgId: "org_wh_test",
      duration: 120,
      recordingUrl: "https://recordings.vapi.ai/call_end_001.mp3",
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.received).toBe(true);
  });

  test("[2.1-E2E-041][P1] Given call-end without optional fields, When posted, Then still returns 200", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-end", {
      vapiCallId: "call_end_002",
      orgId: "org_wh_test",
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
  });
});

test.describe("[P0] Webhook: call-failed Event — AC4", () => {
  test("[2.1-E2E-050][P0] Given valid call-failed webhook with error, When posted, Then returns 200 received", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-failed", {
      vapiCallId: "call_fail_001",
      orgId: "org_wh_test",
      errorMessage: "No answer from destination",
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.received).toBe(true);
  });

  test("[2.1-E2E-051][P1] Given call-failed without error message, When posted, Then returns 200", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-failed", {
      vapiCallId: "call_fail_002",
      orgId: "org_wh_test",
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
  });
});
