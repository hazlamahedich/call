import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Pulse-Maker Visual Visualizer Component
 * Story: 2.5 - Pulse-Maker Visual Visualizer Component
 * Epic: 2 - Real-Time AI Voice Pipeline
 *
 * Test ID Format: 2.5-E2E-XXX
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('Pulse-Maker E2E User Journey', () => {
  /**
   * Test ID: 2.5-E2E-001
   * Priority: P1
   * Tags: @smoke @p1
   * AC: AC1, AC7
   *
   * Validates that Pulse-Maker component is visible on Fleet Navigator sidebar
   * for active agents. Tests basic component rendering and positioning.
   */
  test('[P1] @smoke @p1 should display Pulse Maker on Fleet Navigator sidebar', async ({ page }) => {
    // Navigate to dashboard with authenticated session
    await page.goto('/dashboard');

    // Wait for Fleet Navigator to load
    await expect(page.getByRole('navigation', { name: 'Fleet Navigator' })).toBeVisible();

    // Verify Pulse Maker is visible for active agents
    const pulseMakers = page.getByTestId('pulse-maker');
    await expect(pulseMakers.first()).toBeVisible();

    // Verify positioning (top-right corner of agent card)
    const firstPulse = pulseMakers.first();
    const box = await firstPulse.boundingBox();
    expect(box).toBeTruthy();
  });

  /**
   * Test ID: 2.5-E2E-002
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC2, AC3
   *
   * Validates that Pulse responds to voice events during active call.
   * Tests integration with useVoiceEvents hook and WebSocket event stream.
   */
  test('[P0] @smoke @p0 should respond to voice events during active call', async ({ page }) => {
    // Setup: Mock WebSocket for voice events
    await page.goto('/dashboard');

    // Intercept WebSocket connection and mock voice events
    await page.route('**/api/v1/calls/voice-events', async (route) => {
      // Mock speech-start event
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'speech_state',
          data: {
            eventType: 'speech-start',
            agentId: 'agent-123',
            timestamp: Date.now(),
            volume: 0.8,
          },
        }),
      });
    });

    // Navigate to Fleet Navigator
    await page.getByRole('navigation', { name: 'Fleet Navigator' }).click();

    // Wait for Pulse to respond to voice event
    const pulse = page.getByTestId('pulse-maker').first();
    await expect(pulse).toHaveAttribute('data-volume', '0.8');
    await expect(pulse).toHaveAttribute('data-active', 'true');
  });

  /**
   * Test ID: 2.5-E2E-003
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

    // Initial idle state
    await expect(pulseCore).toHaveCSS('--pulse-scale', '1.0');
    await expect(pulseCore).toHaveCSS('--pulse-duration', '2s');

    // Mock speech-start event
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: { eventType: 'speech-start', volume: 0.8 }
      }));
    });

    // Speaking state (quickened)
    await expect(pulseCore).toHaveCSS('--pulse-scale', '1.3');
    await expect(pulseCore).toHaveCSS('--pulse-duration', '0.5s');

    // Mock speech-end event (triggers exponential decay)
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: { eventType: 'speech-end', volume: 0.0 }
      }));
    });

    // Wait for decay to complete
    await page.waitForTimeout(600);

    // Back to idle state
    await expect(pulseCore).toHaveCSS('--pulse-scale', '1.0');
    await expect(pulseCore).toHaveCSS('--pulse-duration', '2s');
  });

  /**
   * Test ID: 2.5-E2E-004
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

    // Verify neutral color (Electric Blue)
    const color = await pulseCore.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('--pulse-color');
    });

    expect(color).toBe('#3B82F6');
  });

  /**
   * Test ID: 2.5-E2E-005
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

    // Wait for ripple animation to start
    await page.waitForTimeout(50);

    // Verify ripple elements are present
    const ripple = pulse.getByTestId('pulse-ripple');
    await expect(ripple).toBeVisible();

    // Verify crimson color
    const rippleColor = await ripple.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(rippleColor).toContain('244, 63, 94'); // RGB for #F43F5E

    // Verify ripple fades after 300ms
    await page.waitForTimeout(350);
    await expect(ripple).not.toBeVisible();
  });

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

    // Verify static state (no animations)
    await expect(pulseCore).toHaveCSS('animation', 'none');

    // Verify reduced opacity for "calm" state
    const opacity = await pulseCore.evaluate((el) => {
      return window.getComputedStyle(el).opacity;
    });
    expect(opacity).toBe('0.6');
  });

  /**
   * Test ID: 2.5-E2E-007
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC7
   *
   * Validates multiple Pulse instances display simultaneously with state isolation.
   * Tests Fleet Navigator integration with multiple active agents.
   */
  test('[P0] @smoke @p0 should display multiple Pulse instances with state isolation', async ({ page }) => {
    await page.goto('/dashboard');

    // Create multiple active agents
    await page.evaluate(() => {
      const fleetNavigator = document.querySelector('[data-testid="fleet-navigator"]');
      if (fleetNavigator) {
        // Simulate 3 active agents
        window.dispatchEvent(new CustomEvent('agents-loaded', {
          detail: {
            agents: [
              { id: 'agent-1', name: 'Agent 1', status: 'active' },
              { id: 'agent-2', name: 'Agent 2', status: 'active' },
              { id: 'agent-3', name: 'Agent 3', status: 'active' },
            ]
          }
        }));
      }
    });

    // Wait for all Pulse instances to render
    await page.waitForTimeout(100);

    const pulses = page.getByTestId('pulse-maker');
    await expect(pulses).toHaveCount(3);

    // Verify each Pulse has unique agentId
    const agentIds = await pulses.all().map(async (pulse, index) => {
      return await pulse.getAttribute('data-agent-id');
    });

    const uniqueIds = new Set(agentIds);
    expect(uniqueIds.size).toBe(3);

    // Verify state isolation: trigger event for agent-1 only
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: {
          eventType: 'speech-start',
          agentId: 'agent-1',
          volume: 0.8
        }
      }));
    });

    // Only agent-1 Pulse should be active
    const pulse1 = page.getByTestId('pulse-maker').filter({ hasText: 'agent-1' });
    await expect(pulse1).toHaveAttribute('data-active', 'true');

    const pulse2 = page.getByTestId('pulse-maker').filter({ hasText: 'agent-2' });
    await expect(pulse2).toHaveAttribute('data-active', 'false');
  });

  /**
   * Test ID: 2.5-E2E-008
   * Priority: P2
   * Tags: @p2
   * AC: AC8
   *
   * Validates Obsidian glassmorphism design:
   * - bg-card/40 (40% opacity)
   * - backdrop-blur-md
   * - border-border
   */
  test('[P2] @p2 should display glassmorphism design matching Obsidian theme', async ({ page }) => {
    await page.goto('/dashboard');

    const pulse = page.getByTestId('pulse-maker').first();

    // Verify glassmorphism styles
    const backdropFilter = await pulse.evaluate((el) => {
      return window.getComputedStyle(el).backdropFilter;
    });
    expect(backdropFilter).toContain('blur');

    // Verify border
    const borderWidth = await pulse.evaluate((el) => {
      return window.getComputedStyle(el).borderWidth;
    });
    expect(parseInt(borderWidth)).toBeGreaterThan(0);

    // Verify translucent background
    const backgroundColor = await pulse.evaluate((el) => {
      const color = window.getComputedStyle(el).backgroundColor;
      return color; // Should be rgba with alpha < 1
    });
    expect(backgroundColor).toMatch(/rgba/);
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

    // Verify announcement text updates
    await expect(srText).toContainText('Pulse: speaking, volume: 80%');
  });
});
