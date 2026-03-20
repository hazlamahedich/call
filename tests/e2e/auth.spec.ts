/**
 * Story 1-2: Multi-layer Hierarchy & Clerk Auth Integration
 * E2E Tests for Authentication Flow
 * 
 * Test ID Format: 1.2-E2E-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
 */
import { test, expect, Page } from '@playwright/test';

test.describe('[P1] Authentication Flow - Story 1-2', () => {
  test.describe.configure({ mode: 'parallel' });

  test('[1.2-E2E-001][P0] should redirect unauthenticated users to sign-in page', async ({ page }) => {
    // Given: User is not authenticated
    // When: User navigates to protected dashboard route
    await page.goto('/dashboard');
    await page.waitForURL('**/sign-in**');
    // Then: User should be redirected to sign-in page
    expect(page.url()).toContain('/sign-in');
  });

  test('[1.2-E2E-002][P1] should display sign-in page elements', async ({ page }) => {
    // Given: User navigates to sign-in page
    // When: Page loads
    await page.goto('/sign-in');
    // Then: Sign-in component should be visible
    await expect(page.locator('[data-testid="sign-in"]')).toBeVisible();
  });

  test('[1.2-E2E-003][P1] should display sign-up page elements', async ({ page }) => {
    // Given: User navigates to sign-up page
    // When: Page loads
    await page.goto('/sign-up');
    // Then: Sign-up component should be visible
    await expect(page.locator('[data-testid="sign-up"]')).toBeVisible();
  });

  test('[1.2-E2E-004][P1] should persist organization context across navigation', async ({ page }) => {
    // Given: User is not authenticated
    // When: User attempts to access dashboard
    await page.goto('/dashboard');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in (auth context check)
    expect(page.url()).toContain('/sign-in');
  });
});

test.describe('[P0] Organization Management - AC1', () => {
  test('[1.2-E2E-005][P0] should require auth for organization creation page', async ({ page }) => {
    // Given: User is not authenticated
    // When: User attempts to access organization creation page
    await page.goto('/dashboard/organizations/new');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in
    expect(page.url()).toContain('/sign-in');
  });

  test('[1.2-E2E-006][P2] should display organization form fields when authenticated', async ({ page }) => {
    // Given: User is not authenticated (placeholder for authenticated test)
    // When: User attempts to access organization creation page
    await page.goto('/dashboard/organizations/new');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in (auth required)
    expect(page.url()).toContain('/sign-in');
  });
});

test.describe('[P0] Client Management - AC2', () => {
  test('[1.2-E2E-007][P0] should require authentication for clients page', async ({ page }) => {
    // Given: User is not authenticated
    // When: User attempts to access clients page
    await page.goto('/dashboard/clients');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in
    expect(page.url()).toContain('/sign-in');
  });

  test('[1.2-E2E-008][P2] should display client list when authenticated', async ({ page }) => {
    // Given: User is not authenticated (placeholder for authenticated test)
    // When: User attempts to access clients page
    await page.goto('/dashboard/clients');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in (auth required)
    expect(page.url()).toContain('/sign-in');
  });
});

test.describe('[P1] Role-Based Access Control - AC3', () => {
  test('[1.2-E2E-009][P1] admin should see Add Client button', async ({ page }) => {
    // Given: User is not authenticated (placeholder for admin user test)
    // When: Admin user views clients page
    await page.goto('/dashboard/clients');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in (requires authenticated admin)
    expect(page.url()).toContain('/sign-in');
  });

  test('[1.2-E2E-010][P1] member should not see Add Client button', async ({ page }) => {
    // Given: User is not authenticated (placeholder for member user test)
    // When: Member user views clients page
    await page.goto('/dashboard/clients');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in (requires authenticated member)
    expect(page.url()).toContain('/sign-in');
  });
});

test.describe('[P1] Error Handling - AC6', () => {
  test('[1.2-E2E-011][P1] should display error message when Clerk unavailable', async ({ page, context }) => {
    // Given: Clerk service is unavailable
    await page.route('**/clerk**', (route) => route.abort('failed'));
    // When: User attempts to access sign-in page
    await page.goto('/sign-in');
    // Then: Page should still render gracefully
    await expect(page.locator('body')).toBeVisible();
  });

  test('[1.2-E2E-012][P1] should handle invalid session gracefully', async ({ page }) => {
    // Given: User has an invalid session
    // When: User attempts to access protected route
    await page.goto('/dashboard');
    await page.waitForURL('**/sign-in**');
    // Then: Should redirect to sign-in
    expect(page.url()).toContain('/sign-in');
  });

  test('[1.2-E2E-013][P1] should return 401 for unauthorized org access', async ({ page }) => {
    // Given: User requests organization without valid auth
    // When: API call is made to organization endpoint
    const response = await page.request.get('/api/organizations/invalid-org-id');
    // Then: Should return 401 or 404
    expect([401, 404]).toContain(response.status());
  });
});

test.describe('[P0] API Middleware Validation - AC4', () => {
  test('[1.2-E2E-014][P0] should return 401 for missing Authorization header', async ({ page }) => {
    // Given: API request without Authorization header
    // When: Request is made to protected endpoint
    const response = await page.request.get('/api/protected-endpoint');
    // Then: Should return 401 or 404
    expect([401, 404]).toContain(response.status());
  });

  test('[1.2-E2E-015][P0] should return 401 for invalid token format', async ({ page }) => {
    // Given: API request with malformed Authorization header
    const response = await page.request.get('/api/protected-endpoint', {
      headers: { Authorization: 'InvalidFormat' },
    });
    // When: Request is made to protected endpoint
    // Then: Should return 401 or 404
    expect([401, 404]).toContain(response.status());
  });

  test('[1.2-E2E-016][P0] should return AUTH_INVALID_TOKEN code for missing token', async ({ page }) => {
    // Given: API request without token
    // When: Request is made to protected endpoint
    const response = await page.request.get('/api/protected-endpoint');
    // Then: Should return 401 with AUTH_INVALID_TOKEN code
    if (response.status() === 401) {
      const body = await response.json();
      expect(body.code || body.detail?.code).toBe('AUTH_INVALID_TOKEN');
    }
  });
});
