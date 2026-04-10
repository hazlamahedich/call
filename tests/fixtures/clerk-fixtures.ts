import { test as base, expect } from "@playwright/test";
import { clerk } from "@clerk/testing/playwright";

interface ClerkTestUser {
  email: string;
  password: string;
  orgRole: string;
  userId: string;
  orgId: string;
}

export const clerkTest = base.extend<{
  adminUser: ClerkTestUser;
  memberUser: ClerkTestUser;
}>({
  adminUser: async ({ page, context }, use) => {
    const admin: ClerkTestUser = {
      email: process.env.E2E_CLERK_ADMIN_EMAIL || "admin@test.example",
      password: process.env.E2E_CLERK_ADMIN_PASSWORD || "TestAdmin123!",
      orgRole: "org:admin",
      userId: process.env.E2E_CLERK_ADMIN_USER_ID || "test_admin_user_id",
      orgId: process.env.E2E_CLERK_ADMIN_ORG_ID || "test_admin_org_id",
    };

    await clerk.signIn({
      page,
      signInUrl: "/sign-in",
      email: admin.email,
      password: admin.password,
    });
    await page.waitForURL("**/dashboard**", { timeout: 10000 });

    await use(admin);
  },

  memberUser: async ({ page, context }, use) => {
    const member: ClerkTestUser = {
      email: process.env.E2E_CLERK_MEMBER_EMAIL || "member@test.example",
      password: process.env.E2E_CLERK_MEMBER_PASSWORD || "TestMember123!",
      orgRole: "org:member",
      userId: process.env.E2E_CLERK_MEMBER_USER_ID || "test_member_user_id",
      orgId: process.env.E2E_CLERK_MEMBER_ORG_ID || "test_member_org_id",
    };

    await clerk.signIn({
      page,
      signInUrl: "/sign-in",
      email: member.email,
      password: member.password,
    });
    await page.waitForURL("**/dashboard**", { timeout: 10000 });

    await use(member);
  },
});

export const authenticatedTest = base.extend<{
  authenticatedPage: typeof page;
}>({
  authenticatedPage: async ({ page }, use) => {
    const email = process.env.E2E_CLERK_ADMIN_EMAIL || "admin@test.example";
    const password = process.env.E2E_CLERK_ADMIN_PASSWORD || "TestAdmin123!";

    await clerk.signIn({
      page,
      signInUrl: "/sign-in",
      email,
      password,
    });
    await page.waitForURL("**/dashboard**", { timeout: 10000 });

    await use(page);
  },
});

export function createTestUser(
  overrides: Partial<ClerkTestUser> = {},
): ClerkTestUser {
  return {
    email:
      overrides.email ||
      process.env.E2E_CLERK_ADMIN_EMAIL ||
      "admin@test.example",
    password:
      overrides.password ||
      process.env.E2E_CLERK_ADMIN_PASSWORD ||
      "TestAdmin123!",
    orgRole: overrides.orgRole || "org:admin",
    userId:
      overrides.userId ||
      process.env.E2E_CLERK_ADMIN_USER_ID ||
      "test_admin_user_id",
    orgId:
      overrides.orgId ||
      process.env.E2E_CLERK_ADMIN_ORG_ID ||
      "test_admin_org_id",
  };
}

export async function signInAs(
  page: import("@playwright/test").Page,
  user: ClerkTestUser,
) {
  await clerk.signIn({
    page,
    signInUrl: "/sign-in",
    email: user.email,
    password: user.password,
  });
  await page.waitForURL("**/dashboard**", { timeout: 10000 });
}

export async function createAndSignIn(
  page: import("@playwright/test").Page,
  overrides: Partial<ClerkTestUser> = {},
): Promise<ClerkTestUser> {
  const user = createTestUser(overrides);
  await signInAs(page, user);
  return user;
}

export function getOrgHeaders(orgId: string) {
  return {
    "x-org-id": orgId,
    authorization: "Bearer test-token",
  };
}

export { clerk };
export const test = clerkTest;
export { expect };
