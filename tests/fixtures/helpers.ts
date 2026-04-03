import { Page } from '@playwright/test';

/**
 * Helper Utilities for E2E Tests
 *
 * Provides common helper functions for waiting, assertions, and test utilities.
 */

/**
 * Wait for API Response
 *
 * Waits for an API response matching the URL pattern.
 * Useful for network-first testing pattern.
 *
 * @param page - Playwright Page object
 * @param urlPattern - URL pattern to match
 * @returns Promise that resolves with the response
 *
 * Usage:
 * ```typescript
 * test('wait for API response', async ({ page }) => {
 *   await page.goto('/dashboard');
 *   const response = await waitForApiResponse(page, '/api/user');
 *   expect(response.ok()).toBeTruthy();
 * });
 * ```
 */
export async function waitForApiResponse(page: Page, urlPattern: string) {
  return page.waitForResponse((response) =>
    response.url().includes(urlPattern) && response.ok()
  );
}

/**
 * Wait for Custom Event
 *
 * Waits for a custom event to be dispatched on the window.
 * Useful for testing component communication via events.
 *
 * @param page - Playwright Page object
 * @param eventType - Event type to wait for
 * @param timeout - Timeout in milliseconds (default: 5000)
 * @returns Promise that resolves with the event data
 *
 * Usage:
 * ```typescript
 * test('wait for custom event', async ({ page }) => {
 *   const eventData = await waitForCustomEvent(page, 'voice-event');
 *   expect(eventData.eventType).toBe('speech-start');
 * });
 * ```
 */
export function waitForCustomEvent<T = any>(
  page: Page,
  eventType: string,
  timeout = 5000
): Promise<T> {
  return page.evaluate(
    ({ type, ms }) => {
      return new Promise<T>((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          reject(new Error(`Event "${type}" not received within ${ms}ms`));
        }, ms);

        const handler = (e: CustomEvent<T>) => {
          clearTimeout(timeoutId);
          window.removeEventListener(type, handler);
          resolve(e.detail);
        };

        window.addEventListener(type, handler);
      });
    },
    { type: eventType, ms: timeout }
  );
}

/**
 * Get CSS Custom Property Value
 *
 * Retrieves the value of a CSS custom property (--property-name) for an element.
 *
 * @param page - Playwright Page object
 * @param selector - Element selector
 * @param propertyName - CSS property name (with or without -- prefix)
 * @returns Promise resolving to the property value
 *
 * Usage:
 * ```typescript
 * test('CSS custom property', async ({ page }) => {
 *   const value = await getCssCustomProperty(page, '[data-testid="pulse"]', 'pulse-scale');
 *   expect(value).toBe('1.3');
 * });
 * ```
 */
export async function getCssCustomProperty(
  page: Page,
  selector: string,
  propertyName: string
): Promise<string> {
  const propName = propertyName.startsWith('--') ? propertyName : `--${propertyName}`;

  const value = await page.locator(selector).evaluate((el, prop) => {
    return window.getComputedStyle(el).getPropertyValue(prop);
  }, propName);

  return value;
}

/**
 * Verify Element Accessibility
 *
 * Verifies that an element is accessible to screen readers.
 * Checks for ARIA attributes and roles.
 *
 * @param page - Playwright Page object
 * @param selector - Element selector
 * @param requirements - Accessibility requirements to verify
 *
 * Usage:
 * ```typescript
 * test('accessible element', async ({ page }) => {
 *   await verifyElementAccessibility(page, '[role="button"]', {
 *     hasRole: true,
 *     hasLabel: true,
 *     keyboardAccessible: true
 *   });
 * });
 * ```
 */
export async function verifyElementAccessibility(
  page: Page,
  selector: string,
  requirements: {
    hasRole?: boolean;
    hasLabel?: boolean;
    keyboardAccessible?: boolean;
  }
): Promise<void> {
  const element = page.locator(selector);

  if (requirements.hasRole) {
    const role = await element.getAttribute('role');
    expect(role).toBeTruthy();
  }

  if (requirements.hasLabel) {
    const label = await page.locator(selector).getAttribute('aria-label');
    const text = await page.locator(selector).textContent();
    expect(label || text).toBeTruthy();
  }

  if (requirements.keyboardAccessible) {
    const tagName = await element.evaluate((el) => el.tagName.toLowerCase());
    const isKeyboardAccessible = ['button', 'input', 'a', 'textarea', 'select'].includes(tagName);
    const hasTabIndex = await element.getAttribute('tabindex');
    expect(isKeyboardAccessible || hasTabIndex).toBeTruthy();
  }
}

/**
 * Mock Date/Time for Testing
 *
 * Mocks the current date/time for consistent testing.
 * Useful for testing time-sensitive features.
 *
 * @param page - Playwright Page object
 * @param timestamp - Timestamp to mock (in milliseconds)
 *
 * Usage:
 * ```typescript
 * test('mock time', async ({ page }) => {
 *   await mockDateTime(page, new Date('2024-01-01').getTime());
 *   // All Date.now() calls will return this timestamp
 * });
 * ```
 */
export async function mockDateTime(page: Page, timestamp: number): Promise<void> {
  await page.addInitScript(`
    // Mock Date.now()
    const originalDateNow = Date.now;
    Date.now = () => ${timestamp};

    // Mock new Date()
    const MockDate = class extends Date {
      constructor(...args: any[]) {
        if (args.length === 0) {
          super(${timestamp});
        } else {
          super(...args);
        }
      }
    };
    // @ts-ignore
    globalThis.Date = MockDate;
  `);
}

/**
 * Get Console Logs
 *
 * Retrieves console logs from the page.
 * Useful for debugging and verifying expected log messages.
 *
 * @param page - Playwright Page object
 * @returns Array of console log messages
 *
 * Usage:
 * ```typescript
 * test('console logs', async ({ page }) => {
 *   await page.evaluate(() => console.log('Test message'));
 *   const logs = await getConsoleLogs(page);
 *   expect(logs).toContain('Test message');
 * });
 * ```
 */
export async function getConsoleLogs(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    // @ts-ignore
    return (window as any).__consoleLogs || [];
  });
}

/**
 * Setup Console Log Capture
 *
 * Sets up console log capture for debugging.
 * Call this before actions that might log errors.
 *
 * @param page - Playwright Page object
 *
 * Usage:
 * ```typescript
 * test('capture console errors', async ({ page }) => {
 *   await setupConsoleLogCapture(page);
 *
 *   await page.goto('/page-with-errors');
 *
 *   const logs = await getConsoleLogs(page);
 *   const errors = logs.filter(log => log.type === 'error');
 *   expect(errors).toHaveLength(0);
 * });
 * ```
 */
export async function setupConsoleLogCapture(page: Page): Promise<void> {
  await page.addInitScript(() => {
    // @ts-ignore
    window.__consoleLogs = [];

    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    console.log = (...args: any[]) => {
      // @ts-ignore
      window.__consoleLogs.push({ type: 'log', message: args.join(' ') });
      originalLog.apply(console, args);
    };

    console.error = (...args: any[]) => {
      // @ts-ignore
      window.__consoleLogs.push({ type: 'error', message: args.join(' ') });
      originalError.apply(console, args);
    };

    console.warn = (...args: any[]) => {
      // @ts-ignore
      window.__consoleLogs.push({ type: 'warn', message: args.join(' ') });
      originalWarn.apply(console, args);
    };
  });
}
