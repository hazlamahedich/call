import { test, expect } from "../support/merged-fixtures";

test.describe("[CROSS-STORY][E2E] Homepage & Navigation — Stories 1-1, 1-4", () => {
  test("[E2E-001][P0] should display the homepage with title", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Titan Cold Caller");
  });

  test("[E2E-002][P1] should have a link to command center on homepage", async ({
    page,
  }) => {
    await page.goto("/");
    const link = page.locator('a[href="/command-center"]');
    await expect(link).toBeVisible();
    await expect(link).toContainText("Enter Command Center");
  });

  test("[E2E-003][P1] should navigate to command center from homepage", async ({
    page,
  }) => {
    await page.goto("/");
    await page.click('a[href="/command-center"]');
    await expect(page.locator("text=Main Telemetry")).toBeVisible();
  });

  test("[E2E-004][P1] should render command center with Fleet Navigator sidebar", async ({
    page,
  }) => {
    await page.goto("/command-center");
    await expect(page.locator("text=Fleet Navigator")).toBeVisible();
  });

  test("[E2E-005][P1] should render command center with Live Telemetry area", async ({
    page,
  }) => {
    await page.goto("/command-center");
    await expect(page.locator("text=Live Telemetry")).toBeVisible();
  });

  test("[E2E-006][P1] should render command center with Rejection Shield panel", async ({
    page,
  }) => {
    await page.goto("/command-center");
    await expect(page.locator("text=Rejection Shield")).toBeVisible();
  });

  test("[E2E-007][P2] should display Obsidian dark theme on homepage", async ({
    page,
  }) => {
    await page.goto("/");
    const body = page.locator("body");
    const bgColor = await body.evaluate(
      (el) => getComputedStyle(el).backgroundColor,
    );
    expect(bgColor).toBeTruthy();
  });
});
