import { test, expect } from "../../support/merged-fixtures";
import {
  buildWebhookPayload,
  webhookHeaders,
} from "../../support/webhook-helpers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

test.describe("[P0] Webhook Signature Verification — AC5", () => {
  test("[2.1-E2E-060][P0] Given webhook without vapi-signature header, When posted, Then returns 401", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-start", {
      vapiCallId: "call_nosig_001",
      orgId: "org_wh_test",
    });

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      {
        data: body,
        headers: { "Content-Type": "application/json" },
      },
    );

    expect(response.status()).toBe(401);
    const json = await response.json();
    expect(json.detail?.code).toBe("VAPI_SIGNATURE_MISSING");
  });

  test("[2.1-E2E-061][P0] Given webhook with invalid signature, When posted, Then returns 401", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-start", {
      vapiCallId: "call_badsig_001",
      orgId: "org_wh_test",
    });

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      {
        data: body,
        headers: {
          "Content-Type": "application/json",
          "vapi-signature": "invalid_signature_value",
        },
      },
    );

    expect(response.status()).toBe(401);
    const json = await response.json();
    expect(json.detail?.code).toBe("VAPI_SIGNATURE_INVALID");
  });
});
