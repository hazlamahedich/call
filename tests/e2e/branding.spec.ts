/**
 * Story 1-5: White-labeled Admin Portal & Custom Branding
 * E2E Tests for Branding Settings Page
 *
 * Test ID Format: 1.5-E2E-BRANDING-XXX
 * Priority: P0 (Critical) | P1 (High)
 *
 * NOTE: These tests require Clerk test fixtures to be configured.
 * Set environment variables E2E_CLERK_EMAIL and E2E_CLERK_PASSWORD
 * with admin credentials before running.
 */
import { test, expect } from "@playwright/test";

const E2E_CLERK_EMAIL = process.env.E2E_CLERK_EMAIL || "admin@test.example";
const E2E_CLERK_PASSWORD = process.env.E2E_CLERK_PASSWORD || "TestPassword123!";

test.describe("[P0] Branding Settings Page", () => {
  test("[1.5-E2E-001][P1] Given authenticated admin, When navigating to branding settings, Then branding page loads", async ({
    page,
  }) => {
    test.skip(!!process.env.CI, "Requires Clerk test fixtures");
    await page.goto("/sign-in");
    await page.locator('input[name="email"]').fill(E2E_CLERK_EMAIL);
    await page.locator('input[name="password"]').fill(E2E_CLERK_PASSWORD);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/dashboard**", { timeout: 15000 });

    await page.goto("/dashboard/settings/branding");

    const header = page.locator("header");
    await expect(header).toBeVisible();
  });

  test("[1.5-E2E-002][P1] Given branding settings page, When page renders, Then shows brand configuration form", async ({
    page,
  }) => {
    test.skip(!!process.env.CI, "Requires Clerk test fixtures");
    await page.goto("/sign-in");
    await page.locator('input[name="email"]').fill(E2E_CLERK_EMAIL);
    await page.locator('input[name="password"]').fill(E2E_CLERK_PASSWORD);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/dashboard**", { timeout: 1500 });

    await page.goto("/dashboard/settings/branding");

    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
  });
});
