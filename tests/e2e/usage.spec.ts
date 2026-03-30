/**
 * Story 1.7: Resource Guardrails - Usage Monitoring & Hard Caps
 * E2E Tests for Usage Dashboard & Alerts
 *
 * Test ID Format: 1.7-E2E-XXX
 * Priority: P0 (Critical) | P1 (High)
 *
 * NOTE: These tests require Clerk test fixtures to be configured.
 * Set environment variables E2E_CLERK_EMAIL and E2E_CLERK_PASSWORD
 * with credentials for an authenticated account before running.
 */
import { test, expect } from "../support/merged-fixtures";

test.describe("[P0] Usage Dashboard", () => {
  test("[1.7-E2E-001][P0] Given authenticated user on dashboard, When usage is under 80%, Then no alert is shown", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 500,
          cap: 1000,
          percentage: 50.0,
          plan: "free",
          threshold: "ok",
        }),
      }),
    );

    await page.goto("/dashboard");
    await expect(page.getByText("Dashboard")).toBeVisible();
    await expect(page.getByRole("status")).not.toBeVisible();
  });

  test("[1.7-E2E-002][P0] Given authenticated user on dashboard, When usage hits 80%, Then warning alert is shown", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 850,
          cap: 1000,
          percentage: 85.0,
          plan: "free",
          threshold: "warning",
        }),
      }),
    );

    await page.goto("/dashboard");
    const alert = page.getByRole("status");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("80%");
  });

  test("[1.7-E2E-003][P0] Given authenticated user on dashboard, When usage hits 95%, Then critical alert is shown", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 970,
          cap: 1000,
          percentage: 97.0,
          plan: "free",
          threshold: "critical",
        }),
      }),
    );

    await page.goto("/dashboard");
    const alert = page.getByRole("status");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("95%");
  });

  test("[1.7-E2E-004][P0] Given authenticated user on dashboard, When usage is 100%, Then exceeded alert is shown", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 1000,
          cap: 1000,
          percentage: 100.0,
          plan: "free",
          threshold: "exceeded",
        }),
      }),
    );

    await page.goto("/dashboard");
    const alert = page.getByRole("status");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("limit reached");
  });
});

test.describe("[P1] Usage Detail Page", () => {
  test("[1.7-E2E-005][P1] Given authenticated user, When visiting /dashboard/usage, Then usage summary card is shown", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 500,
          cap: 1000,
          percentage: 50.0,
          plan: "free",
          threshold: "ok",
        }),
      }),
    );

    await page.goto("/dashboard/usage");
    await expect(page.getByText("Usage Overview")).toBeVisible();
    await expect(page.getByText("500")).toBeVisible();
    await expect(page.getByText(/1,000/)).toBeVisible();
  });

  test("[1.7-E2E-006][P1] Given pro plan user, When visiting usage page, Then Scale plan label is shown", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 5000,
          cap: 25000,
          percentage: 20.0,
          plan: "pro",
          threshold: "ok",
        }),
      }),
    );

    await page.goto("/dashboard/usage");
    await expect(page.getByText(/Scale plan/)).toBeVisible();
  });

  test("[1.7-E2E-007][P1] Given high usage, When visiting usage page, Then progress bar has correct aria value", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          used: 850,
          cap: 1000,
          percentage: 85.0,
          plan: "free",
          threshold: "warning",
        }),
      }),
    );

    await page.goto("/dashboard/usage");
    const progressbar = page.getByRole("progressbar");
    await expect(progressbar).toBeVisible();
    await expect(progressbar).toHaveAttribute("aria-valuenow", "85");
  });

  test("[1.7-E2E-008][P1] Given API error, When visiting usage page, Then error message is displayed", async ({
    authenticatedPage: page,
  }) => {
    await page.route("**/usage/summary", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "USAGE_INTERNAL_ERROR",
            message: "Failed to retrieve usage summary",
          },
        }),
      }),
    );

    await page.goto("/dashboard/usage");
    await expect(page.getByText("Usage")).toBeVisible();
  });
});
