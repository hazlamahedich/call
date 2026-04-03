import { defineConfig, devices } from "@playwright/test";
import path from "path";

/**
 * See https://playwright.dev/docs/test-configuration.
 *
 * ✅ P2 FIX: Added globalSetup for shared auth and default storageState
 * - Tests start already authenticated (10-20x faster)
 * - Admin user created once and reused
 * - Session state persisted across test runs
 */
export default defineConfig({
  testDir: "./e2e",
  /* ✅ P2 FIX: Global setup for shared auth state */
  globalSetup: path.join(__dirname, "global-setup.ts"),
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: "html",
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000",

    /* ✅ P2 FIX: Use shared auth state by default */
    storageState: path.join(__dirname, ".auth", "admin.json"),

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "on-first-retry",
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
});
