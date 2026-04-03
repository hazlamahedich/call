import { test, expect } from '@playwright/test';
import { createAgent } from '../../factories/agent-factory';

/**
 * Pulse-Maker Accessibility Tests
 * Story: 2.5 - Pulse-Maker Visual Visualizer Component
 * Epic: 2 - Real-Time AI Voice Pipeline
 *
 * Test ID Format: 2.5-E2E-XXX
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('Pulse-Maker Accessibility (WCAG AAA)', () => {
  /**
   * Test ID: 2.5-E2E-006
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC6
   *
   * Validates WCAG AAA motion reduction support.
   * Tests prefers-reduced-motion media query and motionEnabled prop.
   */
  test('[P0] @smoke @p0 should disable animations when prefers-reduced-motion', async ({ page }) => {
    // Enable reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' });

    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();
    const pulseCore = pulse.getByTestId('pulse-core');

    // Wait for element (deterministic)
    await expect(pulseCore).toBeAttached();

    // Verify static state (no animations)
    await expect(pulseCore).toHaveCSS('animation', 'none');

    // Verify reduced opacity for "calm" state
    const opacity = await pulseCore.evaluate((el) => {
      return window.getComputedStyle(el).opacity;
    });
    expect(opacity).toBe('0.6');
  });

  /**
   * Test ID: 2.5-E2E-009
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC9
   *
   * Validates screen reader announcements for pulse state changes.
   * Tests WCAG AAA accessibility compliance.
   */
  test('[P0] @smoke @p0 should announce pulse state changes to screen readers', async ({ page }) => {
    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();

    // Wait for element (deterministic)
    await expect(pulse).toBeAttached();

    // Verify ARIA attributes
    await expect(pulse).toHaveAttribute('role', 'status');

    // Verify screen reader text (visually hidden)
    const srText = pulse.getByTestId('sr-only');
    await expect(srText).toBeVisible();

    // Trigger voice event
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: {
          eventType: 'speech-start',
          volume: 0.8
        }
      }));
    });

    // Wait for announcement text to update (deterministic text content check)
    await page.waitForFunction((el) => {
      return el.textContent?.includes('speaking');
    }, await srText.elementHandle());

    // Verify announcement text updates
    await expect(srText).toContainText('Pulse: speaking, volume: 80%');
  });

  /**
   * Test ID: 2.5-E2E-010
   * Priority: P1
   * Tags: @p1
   * AC: AC9
   *
   * Validates proper ARIA live region behavior.
   * Tests that status updates are announced without duplicate regions.
   */
  test('[P1] @p1 should not have duplicate aria-live regions', async ({ page }) => {
    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();
    await expect(pulse).toBeAttached();

    // Only role="status" should be present, not duplicate aria-live
    const ariaLiveRegions = pulse.locator('[aria-live="polite"]');
    await expect(ariaLiveRegions).toHaveCount(0);

    // sr-only span should not have aria-live (role=status is sufficient)
    const srOnly = pulse.locator('.sr-only');
    await expect(srOnly).toHaveAttribute('aria-live', /^(?!polite)/); // Negative assertion
  });
});
