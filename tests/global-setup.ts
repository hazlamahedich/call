import { chromium, FullConfig } from '@playwright/test';
import path from 'path';

/**
 * Global setup for Playwright tests
 *
 * Runs once before all tests to:
 * 1. Seed admin user via API (fast, no UI)
 * 2. Authenticate and save session state
 * 3. Reuse auth state across all tests (10-20x faster)
 *
 * Benefits:
 * - Tests start already authenticated (no login overhead)
 * - Parallel execution safe (consistent admin user)
 * - 10-20x faster than UI-based login per test
 */

async function globalSetup(config: FullConfig) {
  console.log('🔧 Global Setup: Starting...');

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const baseURL = config.projects?.[0]?.use?.baseURL ?? 'http://127.0.0.1:3000';

  // Step 1: Create admin user via API (fast!)
  console.log('📋 Creating admin user via API...');

  try {
    const createAdminResponse = await page.request.post(`${baseURL}/api/users`, {
      data: {
        email: 'admin@test.com',
        password: 'password123',
        name: 'Test Admin',
        role: 'admin',
        emailVerified: true, // Skip email verification flow
      },
      // Allow 409 if user already exists (idempotent)
      failOnStatusCode: false,
    });

    if (createAdminResponse.ok()) {
      console.log('✅ Admin user created successfully');
    } else if (createAdminResponse.status() === 409) {
      console.log('ℹ️  Admin user already exists (skipping creation)');
    } else {
      console.log(`⚠️  Failed to create admin user: ${createAdminResponse.status()}`);
      // Continue anyway - user might already exist from previous runs
    }
  } catch (error) {
    console.log('⚠️  API request failed (server may not be running):', error);
    // Continue - tests will handle auth failure gracefully
  }

  // Step 2: Login via UI (once) and save session state
  console.log('🔐 Logging in to save session state...');

  try {
    await page.goto(`${baseURL}/login`);

    // Fill login form
    await page.fill('[data-testid="email"]', 'admin@test.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="login-button"]');

    // Wait for successful login (redirect to dashboard)
    await page.waitForURL('**/dashboard', { timeout: 5000 });
    console.log('✅ Login successful');
  } catch (error) {
    console.log('⚠️  Login flow failed (server may not be running):', error);
    // Continue - tests will handle auth failure
  }

  // Step 3: Save auth state for reuse across all tests
  console.log('💾 Saving auth state to file...');

  const storageStatePath = path.join(__dirname, '.auth', 'admin.json');

  await page.context().storageState({
    path: storageStatePath,
  });

  console.log(`✅ Auth state saved to: ${storageStatePath}`);

  // Cleanup
  await browser.close();
  console.log('✅ Global Setup complete');
}

export default globalSetup;
