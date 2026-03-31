import { test, expect } from "../../support/merged-fixtures";

test.describe("[P0] Usage Limit Enforcement — AC2", () => {
  test("[2.1-E2E-010][P0] Given usage limit exceeded, When triggering call, Then USAGE_LIMIT_EXCEEDED error is displayed", async ({
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
    await expect(callButton).toBeVisible();
    await callButton.click();

    const alert = page.getByRole("alert");
    await expect(alert).toContainText(/limit/i);
  });

  test("[2.1-E2E-011][P1] Given usage at warning threshold, When viewing dashboard, Then usage warning is displayed", async ({
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
    const status = page.getByRole("status");
    await expect(status).toContainText("80%");
  });
});
