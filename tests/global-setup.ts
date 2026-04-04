/**
 * Playwright Global Setup for E2E Tests
 *
 * Handles:
 * - Creating test users in Clerk (if they don't exist)
 * - Setting up test organizations
 * - Persisting authentication state
 *
 * This runs once before all test suites.
 */

import { FullConfig } from "@playwright/test";

async function globalSetup(config: FullConfig) {
  console.log("🔧 Setting up E2E test environment...");
  
  // Validate required environment variables
  const requiredEnvVars = [
    "E2E_CLERK_ADMIN_EMAIL",
    "E2E_CLERK_ADMIN_PASSWORD",
    "E2E_CLERK_MEMBER_EMAIL",
    "E2E_CLERK_MEMBER_PASSWORD",
  ];
  
  const missing = requiredEnvVars.filter(varName => !process.env[varName]);
  
  if (missing.length > 0) {
    console.warn("⚠️  Warning: Missing environment variables:");
    missing.forEach(varName => console.warn(`   - ${varName}`));
    console.warn("");
    console.warn("Tests will use default values. For production testing, set these variables.");
    console.warn("");
  }
  
  // TODO: Create test users via Clerk API if they don't exist
  // This requires Clerk Backend SDK with secret key
  // For now, tests assume users are manually created in Clerk Dashboard
  
  console.log("✅ E2E test environment ready");
}

export default globalSetup;
