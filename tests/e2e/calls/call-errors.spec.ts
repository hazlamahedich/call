import { test, expect } from "../../support/merged-fixtures";
import {
  buildWebhookPayload,
  webhookHeaders,
} from "../../support/webhook-helpers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

test.describe("[P1] Webhook Edge Cases — AC6", () => {
  test("[2.1-E2E-070][P1] Given webhook with missing call ID, When posted, Then returns 200 (idempotent ignore)", async ({
    page,
  }) => {
    const body = JSON.stringify({
      message: {
        type: "call-start",
        call: {},
        metadata: { org_id: "org_wh_test" },
      },
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
  });

  test("[2.1-E2E-071][P1] Given webhook with missing org_id in metadata, When posted, Then returns 200 (idempotent ignore)", async ({
    page,
  }) => {
    const body = JSON.stringify({
      message: {
        type: "call-start",
        call: { id: "call_noorg_001" },
        metadata: {},
      },
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
  });

  test("[2.1-E2E-072][P1] Given webhook with unknown event type, When posted, Then returns 200 (unhandled but acknowledged)", async ({
    page,
  }) => {
    const body = buildWebhookPayload("speech-end", {
      vapiCallId: "call_unknown_001",
      orgId: "org_wh_test",
    });
    const headers = webhookHeaders(body);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response.status()).toBe(200);
  });

  test("[2.1-E2E-073][P1] Given webhook with malformed JSON body, When posted, Then returns 200 (graceful degradation)", async ({
    page,
  }) => {
    const malformedBody = "not valid json{{{";
    const sigHeaders = webhookHeaders(malformedBody);

    const response = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      {
        data: malformedBody,
        headers: {
          "Content-Type": "application/json",
          "vapi-signature": sigHeaders["vapi-signature"],
        },
      },
    );

    expect(response.status()).toBe(200);
  });

  test("[2.1-E2E-074][P2] Given call-start webhook sent twice (idempotent), When posted with same vapi_call_id, Then both return 200", async ({
    page,
  }) => {
    const body = buildWebhookPayload("call-start", {
      vapiCallId: "call_idempotent_001",
      orgId: "org_wh_test",
    });
    const headers = webhookHeaders(body);

    const response1 = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );
    const response2 = await page.request.post(
      `${API_BASE}/webhooks/vapi/call-events`,
      { data: body, headers },
    );

    expect(response1.status()).toBe(200);
    expect(response2.status()).toBe(200);
  });
});

test.describe("[P1] API Error Scenarios — AC6", () => {
  test("[2.1-E2E-080][P1] Given trigger endpoint returns 500 VAPI_NOT_CONFIGURED, When call is attempted, Then error is surfaced", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/calls/trigger", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "VAPI_NOT_CONFIGURED",
            message: "No assistant_id provided",
          },
        }),
      }),
    );

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    await expect(callButton).toBeVisible();
    await callButton.click();

    const alert = page.getByRole("alert");
    await expect(alert).toBeVisible();
  });

  test("[2.1-E2E-081][P1] Given trigger endpoint returns 500 generic error, When call is attempted, Then error is handled gracefully", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/calls/trigger", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "VAPI_CALL_TRIGGER_FAILED",
            message: "Failed to trigger outbound call",
          },
        }),
      }),
    );

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    await expect(callButton).toBeVisible();
    await callButton.click();

    const alert = page.getByRole("alert");
    await expect(alert).toBeVisible();
  });

  test("[2.1-E2E-082][P1] Given trigger endpoint returns 403 AUTH_FORBIDDEN, When call is attempted, Then auth error is displayed", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/calls/trigger", (route) =>
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "AUTH_FORBIDDEN",
            message: "Organization context required",
          },
        }),
      }),
    );

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    await expect(callButton).toBeVisible();
    await callButton.click();

    const alert = page.getByRole("alert");
    await expect(alert).toBeVisible();
  });
});
