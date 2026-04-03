import { test, expect } from "../../support/merged-fixtures";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

test.describe("[P0] Phone Number Validation — AC3", () => {
  test("[2.1-E2E-020][P0] Given invalid phone number format, When trigger is called, Then 422 validation error is returned", async ({
    page,
  }) => {
    const response = await page.request.post(`${API_BASE}/calls/trigger`, {
      data: {
        phoneNumber: "not-a-number",
      },
    });

    expect(response.status()).toBe(422);
  });

  test("[2.1-E2E-021][P0] Given empty phone number, When trigger is called, Then 422 validation error is returned", async ({
    page,
  }) => {
    const response = await page.request.post(`${API_BASE}/calls/trigger`, {
      data: {
        phoneNumber: "",
      },
    });

    expect(response.status()).toBe(422);
  });

  test("[2.1-E2E-022][P1] Given E.164 formatted number, When trigger is called without auth, Then 401 or 403 is returned", async ({
    page,
  }) => {
    const response = await page.request.post(`${API_BASE}/calls/trigger`, {
      data: {
        phoneNumber: "+15551234567",
      },
    });

    expect([401, 403]).toContain(response.status());
  });
});
