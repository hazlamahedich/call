import { test as base } from '@playwright/test';

/**
 * Authentication Fixtures for E2E Tests
 *
 * Provides authenticated user session and auth tokens for testing.
 * Extends Playwright's test fixture with authentication state.
 */

export const test = base.extend<{
  authenticatedPage: Page;
  authToken: string;
}>({
  /**
   * authenticatedPage Fixture
   *
   * Provides a page with authenticated user session.
   * Logs in a test user and returns the authenticated page.
   *
   * Usage:
   * ```typescript
   * test('authenticated user can view dashboard', async ({ authenticatedPage }) => {
   *   await authenticatedPage.goto('/dashboard');
   *   await expect(authenticatedPage.getByText('Welcome')).toBeVisible();
   * });
   * ```
   */
  authenticatedPage: async ({ page }, use) => {
    // TODO: Implement actual login flow when authentication is ready
    // For now, just navigate to dashboard (assumes auth bypass in dev)
    await page.goto('/dashboard');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    await use(page);
  },

  /**
   * authToken Fixture
   *
   * Provides authentication token for API requests.
   * Useful for testing authenticated API endpoints.
   *
   * Usage:
   * ```typescript
   * test('authenticated API request', async ({ request, authToken }) => {
   *   const response = await request.get('/api/user', {
   *     headers: { Authorization: `Bearer ${authToken}` }
   *   });
   *   expect(response.ok()).toBeTruthy();
   * });
   * ```
   */
  authToken: async ({ request }, use) => {
    // TODO: Implement actual token retrieval when auth is ready
    // For now, return a mock token
    const mockToken = 'mock-auth-token-for-development';

    await use(mockToken);
  },
});

// Re-export expect for convenience
export { expect } from '@playwright/test';
