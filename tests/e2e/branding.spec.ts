/**
 * Story 1-5: White-labeled Admin Portal & Custom Branding
 * E2E Tests for Branding Settings Page
 *
 * Test ID Format: [1.5-E2E-BRANDING-XXX]
 * Priority: P0 (Critical) | P1 (High)
 *
 * ✅ UPDATED: Now uses proper Clerk test fixtures from tests/fixtures/clerk-fixtures.ts
 */
import { clerkTest, expect } from "../../fixtures/clerk-fixtures";

clerkTest.describe("[P0] Branding Settings Page", () => {
  clerkTest("[1.5-E2E-001][P1] Given authenticated admin, When navigating to branding settings, Then branding page loads", async ({ adminUser, page }) => {
    // Given: Admin user is signed in (from fixture)
    // When: Admin navigates to branding settings
    await page.goto("/dashboard/settings/branding");
    
    // Then: Branding page should load
    const header = page.locator("header");
    await expect(header).toBeVisible();
    
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
  });

  clerkTest("[1.5-E2E-002][P1] Given branding settings page, When page renders, Then shows brand configuration form", async ({ adminUser, page }) => {
    // Given: Admin user is signed in
    await page.goto("/dashboard/settings/branding");
    
    // When: Page loads
    // Then: Should show brand configuration form
    const heading = page.getByRole("heading", { level: 1, name: /branding/i });
    await expect(heading).toBeVisible();
    
    // Should have form fields
    await expect(page.locator('input[name="brandName"]')).toBeVisible();
    await expect(page.locator('input[type="color"]')).toBeVisible();
  });

  clerkTest("[1.5-E2E-003][P1] should allow uploading custom logo", async ({ adminUser, page }) => {
    // Given: Admin user is on branding settings page
    await page.goto("/dashboard/settings/branding");
    
    // When: Admin uploads a logo
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles("tests/fixtures/test-logo.png");
    
    // Then: Logo should be previewed
    const logoPreview = page.locator('[data-testid="logo-preview"]');
    await expect(logoPreview).toBeVisible();
  });

  clerkTest("[1.5-E2E-004][P1] should save branding settings", async ({ adminUser, page }) => {
    // Given: Admin user is on branding settings page
    await page.goto("/dashboard/settings/branding");
    
    // When: Admin updates branding settings
    await page.fill('input[name="brandName"]', "Test Brand");
    await page.locator('input[type="color"]').fill("#ff0000");
    await page.click('button[type="submit"]');
    
    // Then: Settings should be saved
    const successMessage = page.getByText(/branding.*saved|settings.*updated/i);
    await expect(successMessage).toBeVisible();
    
    // Verify settings persist on reload
    await page.reload();
    await expect(page.locator('input[name="brandName"]')).toHaveValue("Test Brand");
  });

  clerkTest("[1.5-E2E-005][P2] should reset to default branding", async ({ adminUser, page }) => {
    // Given: Admin user has custom branding set
    await page.goto("/dashboard/settings/branding");
    
    // When: Admin clicks reset to defaults
    await page.click('button:has-text("Reset to Defaults")');
    
    // Then: Should show confirmation dialog
    const confirmDialog = page.getByText(/are you sure.*reset/i);
    await expect(confirmDialog).toBeVisible();
    
    await page.click('button:has-text("Confirm")');
    
    // Then: Branding should be reset
    const successMessage = page.getByText(/branding.*reset/i);
    await expect(successMessage).toBeVisible();
  });

  clerkTest("[1.5-E2E-006][P2] member user should not access branding settings", async ({ memberUser, page }) => {
    // Given: Member user is signed in
    // When: Member attempts to access branding settings
    await page.goto("/dashboard/settings/branding");
    
    // Then: Should see access denied
    const errorMessage = page.getByText(/access denied|not authorized|403/i);
    await expect(errorMessage).toBeVisible();
  });
});
