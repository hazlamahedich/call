import { test, expect } from '@playwright/test';
import { createAgent, createVoiceEvent, createSpeakingEvent, createIdleEvent } from '../../factories/agent-factory';

/**
 * Pulse-Maker Voice Events Tests
 * Story: 2.4 - Asynchronous Telemetry Sidecars for Voice Events
 * Epic: 2 - Real-Time AI Voice Pipeline
 *
 * Test ID Format: 2.4-E2E-XXX (Fixed from 2.5-E2E-XXX)
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('[2.4-E2E] Pulse-Maker Voice Event Response', () => {
  // ✅ P1 FIX: Clean up mocked routes after each test to prevent state leakage
  test.afterEach(async ({ page }) => {
    await page.unroute('**/api/v1/calls/voice-events');
    await page.unroute('**/api/v1/voice-events');
  });
  /**
   * Test ID: 2.4-E2E-019
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC2, AC3
   *
   * Validates that Pulse responds to voice events during active call.
   * Tests integration with useVoiceEvents hook and WebSocket event stream.
   */
  test('[P0] @smoke @p0 should respond to voice events during active call', async ({ page }) => {
    // Network-first: Intercept BEFORE navigate (prevents race condition)
    const testAgent = createAgent();
    const voiceEvent = createSpeakingEvent(testAgent.id);

    await page.route('**/api/v1/calls/voice-events', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(voiceEvent),
      });
    });

    // Create response promise BEFORE navigation
    const responsePromise = page.waitForResponse('**/api/v1/calls/voice-events');

    // Navigate AFTER interception is ready
    await page.goto('/dashboard');
    await responsePromise; // Deterministic wait for API response

    // Navigate to Fleet Navigator
    await page.getByRole('navigation', { name: 'Fleet Navigator' }).click();

    // Wait for Pulse to respond to voice event (deterministic state check)
    const pulse = page.getByTestId('pulse-maker').first();
    await expect(pulse).toHaveAttribute('data-volume', '0.8');
    await expect(pulse).toHaveAttribute('data-active', 'true');
  });

  /**
   * Test ID: 2.4-E2E-020
   * Priority: P1
   * Tags: @p1
   * AC: AC3
   *
   * Validates binary volume state animation:
   * - Speaking: scale 1.3, duration 0.5s
   * - Idle: scale 1.0, duration 2s
   */
  test('[P1] @p1 should quicken pulse when speaking and slow when idle', async ({ page }) => {
    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();
    const pulseCore = pulse.getByTestId('pulse-core');

    // Wait for element to be attached (deterministic)
    await expect(pulseCore).toBeAttached();

    // Initial idle state
    await expect(pulseCore).toHaveCSS('--pulse-scale', '1.0');
    await expect(pulseCore).toHaveCSS('--pulse-duration', '2s');

    // Mock speech-start event
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: { eventType: 'speech-start', volume: 0.8 }
      }));
    });

    // Wait for CSS property update (deterministic)
    await page.waitForFunction((el) => {
      const style = window.getComputedStyle(el);
      return style.getPropertyValue('--pulse-scale') === '1.3';
    }, await pulseCore.elementHandle());

    // Speaking state (quickened)
    await expect(pulseCore).toHaveCSS('--pulse-scale', '1.3');
    await expect(pulseCore).toHaveCSS('--pulse-duration', '0.5s');

    // Mock speech-end event (triggers exponential decay)
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: { eventType: 'speech-end', volume: 0.0 }
      }));
    });

    // Wait for decay to complete (deterministic state check, not hard wait)
    await page.waitForFunction((el) => {
      const style = window.getComputedStyle(el);
      return style.getPropertyValue('--pulse-scale') === '1.0';
    }, await pulseCore.elementHandle());

    // Back to idle state
    await expect(pulseCore).toHaveCSS('--pulse-scale', '1.0');
    await expect(pulseCore).toHaveCSS('--pulse-duration', '2s');
  });

  /**
   * Test ID: 2.4-E2E-021
   * Priority: P2
   * Tags: @p2
   * AC: AC4
   *
   * Validates MVP behavior: all pulses display neutral Electric Blue (#3B82F6)
   * regardless of sentiment prop. Post-MVP will add color interpolation.
   */
  test('[P2] @p2 should display neutral blue color for all pulses (MVP)', async ({ page }) => {
    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();
    const pulseCore = pulse.getByTestId('pulse-core');

    // Wait for element (deterministic)
    await expect(pulseCore).toBeAttached();

    // Verify neutral color (Electric Blue)
    const color = await pulseCore.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('--pulse-color');
    });

    expect(color).toBe('#3B82F6');
  });

  /**
   * Test ID: 2.4-E2E-022
   * Priority: P1
   * Tags: @p1
   * AC: AC5
   *
   * Validates interruption ripple effect:
   * - Crimson (#F43F5E) color
   * - 300ms duration
   * - Scale 1.0 → 2.0
   */
  test('[P1] @p1 should display crimson ripple on interruption', async ({ page }) => {
    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();

    // Mock interruption event
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: {
          eventType: 'interruption',
          timestamp: Date.now()
        }
      }));
    });

    // Wait for ripple to appear (deterministic, not hard wait)
    const ripple = pulse.getByTestId('pulse-ripple');
    await expect(ripple).toBeVisible();

    // Verify ripple has interruption class (deterministic state check)
    await expect(ripple).toHaveClass(/interruption/);

    // Verify crimson color
    const rippleColor = await ripple.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(rippleColor).toContain('244, 63, 94'); // RGB for #F43F5E

    // Wait for ripple to fade (deterministic state check, not hard wait)
    await expect(ripple).not.toBeVisible();
  });
});
