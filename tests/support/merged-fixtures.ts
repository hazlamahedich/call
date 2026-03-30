import { test as base, type Page } from "@playwright/test";

const E2E_CLERK_EMAIL = process.env.E2E_CLERK_EMAIL ?? "";
const E2E_CLERK_PASSWORD = process.env.E2E_CLERK_PASSWORD ?? "";

function hasClerkFixtures(): boolean {
  return E2E_CLERK_EMAIL.length > 0 && E2E_CLERK_PASSWORD.length > 0;
}

async function clerkSignIn(
  page: Page,
  waitForUrl = "**/dashboard**",
): Promise<void> {
  await page.goto("/sign-in");
  await page.locator('input[name="email"]').fill(E2E_CLERK_EMAIL);
  await page.locator('input[name="password"]').fill(E2E_CLERK_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(waitForUrl, { timeout: 15000 });
}

type AuthFixtures = {
  authenticatedPage: Page;
  onboardingPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    test.skip(
      !hasClerkFixtures(),
      "Requires E2E_CLERK_EMAIL and E2E_CLERK_PASSWORD env vars",
    );
    await clerkSignIn(page);
    await use(page);
  },
  onboardingPage: async ({ page }, use) => {
    test.skip(
      !hasClerkFixtures(),
      "Requires E2E_CLERK_EMAIL and E2E_CLERK_PASSWORD env vars",
    );
    await clerkSignIn(page, "**/onboarding**");
    await use(page);
  },
});

export { expect } from "@playwright/test";
export { clerkSignIn, hasClerkFixtures };
