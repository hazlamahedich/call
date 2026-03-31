import { test, expect } from "../../support/merged-fixtures";
import {
  buildWebhookPayload,
  webhookHeaders,
} from "../../support/webhook-helpers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

test.describe("[P0] Call Trigger — AC1", () => {
  test("[2.1-E2E-001][P0] Given authenticated user, When clicking start call with valid number, Then trigger endpoint is called", async ({
    authenticatedPage: page,
  }) => {
    let requestBody: Record<string, unknown> | null = null;

    await page.route("**/calls/trigger", async (route) => {
      requestBody = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          call: {
            id: 1,
            vapiCallId: "call_e2e_123",
            orgId: "org_test",
            status: "pending",
            phoneNumber: "+1234567890",
            createdAt: new Date().toISOString(),
          },
        }),
      });
    });

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    await expect(callButton).toBeVisible();
    await callButton.click();

    await page.waitForResponse("**/calls/trigger");

    expect(requestBody).toBeTruthy();
    expect(requestBody?.phoneNumber).toBeDefined();
  });

  test("[2.1-E2E-002][P0] Given valid trigger payload, When API responds 201, Then call response contains required fields", async ({
    authenticatedPage: page,
  }) => {
    const mockCall = {
      id: 42,
      vapiCallId: "call_e2e_456",
      orgId: "org_test",
      leadId: 10,
      agentId: 5,
      campaignId: null,
      status: "pending",
      phoneNumber: "+15551234567",
      createdAt: new Date().toISOString(),
    };

    await page.route("**/calls/trigger", async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ call: mockCall }),
      });
    });

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    await expect(callButton).toBeVisible();
    await callButton.click();

    const response = await page.waitForResponse("**/calls/trigger");
    const body = await response.json();

    expect(response.status()).toBe(201);
    expect(body.call).toBeDefined();
    expect(body.call.id).toBe(42);
    expect(body.call.vapiCallId).toBe("call_e2e_456");
    expect(body.call.status).toBe("pending");
    expect(body.call.phoneNumber).toBe("+15551234567");
  });

  test("[2.1-E2E-003][P0] Given trigger with lead and agent context, When payload is sent, Then context is preserved", async ({
    authenticatedPage: page,
  }) => {
    let capturedBody: Record<string, unknown> | null = null;

    await page.route("**/calls/trigger", async (route) => {
      capturedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          call: {
            id: 3,
            vapiCallId: "call_ctx_001",
            orgId: "org_test",
            leadId: 99,
            agentId: 7,
            status: "pending",
            phoneNumber: "+15559876543",
            createdAt: new Date().toISOString(),
          },
        }),
      });
    });

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    await expect(callButton).toBeVisible();
    await callButton.click();
    await page.waitForResponse("**/calls/trigger");

    expect(capturedBody?.leadId).toBe(99);
    expect(capturedBody?.agentId).toBe(7);
  });
});
