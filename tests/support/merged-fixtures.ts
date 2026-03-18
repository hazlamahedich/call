import { test as base } from '@playwright/test';

// Define custom fixtures here
export const test = base.extend({
  // Add custom fixtures as needed
  // Example:
  // auth: async ({ page }, use) => { ... }
});

export { expect } from '@playwright/test';
