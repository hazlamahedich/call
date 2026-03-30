/**
 * Story 1-6: 10-Minute Launch Onboarding Wizard
 * E2E Tests for Onboarding Wizard Flow
 *
 * Test ID Format: 1.6-E2E-XXX
 * Priority: P0 (Critical) | P1 (High)
 *
 * NOTE: These tests require Clerk test fixtures to be configured.
 * Set environment variables E2E_CLERK_EMAIL and E2E_CLERK_PASSWORD
 * with credentials for a NEW (non-onboarded) account before running.
 */
import { test, expect } from "../support/merged-fixtures";

test.describe("[P0] Onboarding Wizard Flow", () => {
  test("[1.6-E2E-001][P0] Given fresh user, When navigating to /onboarding, Then onboarding page loads with wizard", async ({
    page,
  }) => {
    test.skip(
      !process.env.E2E_CLERK_EMAIL,
      "Requires E2E_CLERK_EMAIL and E2E_CLERK_PASSWORD env vars",
    );

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    await expect(page.getByText("Launch Your Agent")).toBeVisible();
    await expect(page.getByText("Answer 5 quick questions")).toBeVisible();
  });

  test("[1.6-E2E-002][P0] Given onboarding page, When rendered, Then progress indicator shows Step 1 of 5", async ({
    page,
  }) => {
    test.skip(!process.env.E2E_CLERK_EMAIL, "Requires Clerk test fixtures");

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    await expect(page.getByText("Step 1 of 5")).toBeVisible();
  });

  test("[1.6-E2E-003][P0] Given step 1 business goal, When no selection made, Then Next button is disabled", async ({
    page,
  }) => {
    test.skip(!process.env.E2E_CLERK_EMAIL, "Requires Clerk test fixtures");

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    const nextButton = page.getByRole("button", { name: "Next" });
    await expect(nextButton).toBeDisabled();
  });

  test("[1.6-E2E-004][P1] Given step 1, When selecting a business goal and clicking Next, Then step 2 is shown", async ({
    page,
  }) => {
    test.skip(!process.env.E2E_CLERK_EMAIL, "Requires Clerk test fixtures");

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    await page.getByText("Lead Generation").click();
    const nextButton = page.getByRole("button", { name: "Next" });
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    await expect(page.getByText("Step 2 of 5")).toBeVisible();
  });

  test("[1.6-E2E-005][P1] Given step 2 script context, When entering text below minimum, Then Next is disabled", async ({
    page,
  }) => {
    test.skip(!process.env.E2E_CLERK_EMAIL, "Requires Clerk test fixtures");

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    await page.getByText("Lead Generation").click();
    await page.getByRole("button", { name: "Next" }).click();

    const textarea = page.getByRole("textbox", { name: "Script context" });
    await textarea.fill("Too short");
    const nextButton = page.getByRole("button", { name: "Next" });
    await expect(nextButton).toBeDisabled();
  });

  test("[1.6-E2E-006][P1] Given step 2, When entering valid script context and clicking Next, Then step 3 is shown", async ({
    page,
  }) => {
    test.skip(!process.env.E2E_CLERK_EMAIL, "Requires Clerk test fixtures");

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    await page.getByText("Lead Generation").click();
    await page.getByRole("button", { name: "Next" }).click();

    const textarea = page.getByRole("textbox", { name: "Script context" });
    await textarea.fill(
      "We sell premium widgets to small businesses nationwide",
    );
    const nextButton = page.getByRole("button", { name: "Next" });
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    await expect(page.getByText("Step 3 of 5")).toBeVisible();
  });

  test("[1.6-E2E-007][P1] Given onboarding wizard, When clicking Back, Then previous step is shown", async ({
    page,
  }) => {
    test.skip(!process.env.E2E_CLERK_EMAIL, "Requires Clerk test fixtures");

    await page.goto("/sign-in");
    await page
      .locator('input[name="email"]')
      .fill(process.env.E2E_CLERK_EMAIL || "");
    await page
      .locator('input[name="password"]')
      .fill(process.env.E2E_CLERK_PASSWORD || "");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/onboarding**", { timeout: 15000 });

    await page.getByText("Lead Generation").click();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Step 2 of 5")).toBeVisible();

    const backButton = page.getByRole("button", { name: "Back" });
    await expect(backButton).toBeEnabled();
    await backButton.click();

    await expect(page.getByText("Step 1 of 5")).toBeVisible();
  });
});

test.describe("[P1] Onboarding Redirect Guard", () => {
  test("[1.6-E2E-010][P1] Given unauthenticated user, When navigating to /onboarding, Then redirected to sign-in", async ({
    page,
  }) => {
    await page.goto("/onboarding");
    await page.waitForURL(/\/sign-in/, { timeout: 10000 });
    expect(page.url()).toContain("/sign-in");
  });
});
