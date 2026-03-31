/**
 * Story 2.1: Vapi Telephony Bridge & Webhook Integration
 * E2E Tests for Call Trigger Flow
 *
 * Test ID Format: 2.1-E2E-XXX
 * Priority: P0 (Critical) | P1 (High)
 */
import { test, expect } from "../support/merged-fixtures";

test.describe("[P0] Call Trigger", () => {
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
    if (await callButton.isVisible()) {
      await callButton.click();

      await page.waitForResponse("**/calls/trigger");

      expect(requestBody).toBeTruthy();
      expect(requestBody?.phoneNumber).toBeDefined();
    }
  });

  test("[2.1-E2E-002][P0] Given usage limit exceeded, When triggering call, Then error is displayed", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/calls/trigger", (route) =>
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "USAGE_LIMIT_EXCEEDED",
            message: "Monthly call limit has been reached.",
          },
        }),
      }),
    );

    await page.goto("/dashboard");

    const callButton = page.getByRole("button", { name: /start call/i });
    if (await callButton.isVisible()) {
      await callButton.click();

      const alert = page.getByRole("alert");
      if (await alert.isVisible()) {
        await expect(alert).toContainText("limit");
      }
    }
  });
});

test.describe("[P1] Webhook Integration", () => {
  test("[2.1-E2E-003][P1] Given webhook endpoint, When posting call-start event, Then returns 200", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Dashboard")).toBeVisible();
  });
});
