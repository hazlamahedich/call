/**
 * Clerk Test Fixtures for Playwright E2E Tests
 *
 * Provides authenticated test users and organizations for E2E testing.
 * Uses @clerk/testing package for test authentication.
 *
 * Test ID Format: [X.X-E2E-XXX]
 */

import { test as base } from "@playwright/test";

/**
 * Clerk test user fixture
 *
 * Provides pre-configured test users with different roles:
 * - admin: Full permissions, can create orgs/clients
 * - member: Limited permissions, assigned to specific clients
 */
interface ClerkTestUser {
  email: string;
  password: string;
  orgRole: string;
  userId: string;
  orgId: string;
}

/**
 * Extended test fixture with Clerk test users
 */
export const clerkTest = base.extend<{
  adminUser: ClerkTestUser;
  memberUser: ClerkTestUser;
}>({
  adminUser: async ({ page }, use) => {
    // Admin user with full permissions
    const admin: ClerkTestUser = {
      email: process.env.E2E_CLERK_ADMIN_EMAIL || "admin@test.example",
      password: process.env.E2E_CLERK_ADMIN_PASSWORD || "TestAdmin123!",
      orgRole: "org:admin",
      userId: process.env.E2E_CLERK_ADMIN_USER_ID || "test_admin_user_id",
      orgId: process.env.E2E_CLERK_ADMIN_ORG_ID || "test_admin_org_id",
    };

    // Sign in as admin
    await page.goto("/sign-in");
    await page.fill('input[name="email"]', admin.email);
    await page.fill('input[name="password"]', admin.password);
    await page.click('button[type="submit"]');
    
    // Wait for redirect to dashboard (successful sign-in)
    await page.waitForURL("**/dashboard**", { timeout: 10000 });

    await use(admin);
  },

  memberUser: async ({ page }, use) => {
    // Member user with limited permissions
    const member: ClerkTestUser = {
      email: process.env.E2E_CLERK_MEMBER_EMAIL || "member@test.example",
      password: process.env.E2E_CLERK_MEMBER_PASSWORD || "TestMember123!",
      orgRole: "org:member",
      userId: process.env.E2E_CLERK_MEMBER_USER_ID || "test_member_user_id",
      orgId: process.env.E2E_CLERK_MEMBER_ORG_ID || "test_member_org_id",
    };

    // Sign in as member
    await page.goto("/sign-in");
    await page.fill('input[name="email"]', member.email);
    await page.fill('input[name="password"]', member.password);
    await page.click('button[type="submit"]');
    
    // Wait for redirect to dashboard (successful sign-in)
    await page.waitForURL("**/dashboard**", { timeout: 10000 });

    await use(member);
  },
});

/**
 * Authenticated page fixture
 * 
 * Automatically signs in as admin before each test.
 * Useful for tests that don't need specific user roles.
 */
export const authenticatedTest = base.extend<{
  authenticatedPage: typeof page;
}>({
  authenticatedPage: async ({ page }, use) => {
    const email = process.env.E2E_CLERK_ADMIN_EMAIL || "admin@test.example";
    const password = process.env.E2E_CLERK_ADMIN_PASSWORD || "TestAdmin123!";

    await page.goto("/sign-in");
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard**", { timeout: 10000 });

    await use(page);
  },
});

/**
 * Re-export default test for backward compatibility
 */
export const test = clerkTest;
export { expect } from "@playwright/test";
