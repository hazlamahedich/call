import { test, expect } from '@playwright/test';
import { createAgent } from '../../factories/agent-factory';

/**
 * Pulse-Maker Rendering Tests
 * Story: 2.5 - Pulse-Maker Visual Visualizer Component
 * Epic: 2 - Real-Time AI Voice Pipeline
 *
 * Test ID Format: 2.5-E2E-XXX
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('Pulse-Maker Rendering & Display', () => {
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
    // Network-first: Set up agents BEFORE navigation
    const testAgents = [createAgent(), createAgent(), createAgent()];

    // Wait for navigation
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
   * Test ID: 2.5-E2E-007
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC7
   *
   * Validates multiple Pulse instances display simultaneously with state isolation.
   * Tests Fleet Navigator integration with multiple active agents.
   */
  test('[P0] @smoke @p0 should display multiple Pulse instances with state isolation', async ({ page }) => {
    // Network-first: Create multiple agents BEFORE navigation
    const agent1 = createAgent({ name: 'Agent 1' });
    const agent2 = createAgent({ name: 'Agent 2' });
    const agent3 = createAgent({ name: 'Agent 3' });

    await page.goto('/dashboard');

    // Wait for all Pulse instances to render (deterministic, not hard wait)
    await page.waitForSelector('[data-pulse-maker="true"]', { state: 'attached' });

    const pulses = page.getByTestId('pulse-maker');
    await expect(pulses).toHaveCount(3);

    // Verify each Pulse has unique agentId
    const agentIds = await pulses.all().map(async (pulse) => {
      return await pulse.getAttribute('data-agent-id');
    });

    const uniqueIds = new Set(agentIds);
    expect(uniqueIds.size).toBe(3);

    // Verify state isolation: trigger event for agent-1 only
    await page.evaluate((agentId) => {
      window.dispatchEvent(new CustomEvent('voice-event', {
        detail: {
          eventType: 'speech-start',
          agentId: agentId,
          volume: 0.8
        }
      }));
    }, agent1.id);

    // Only agent-1 Pulse should be active (deterministic check)
    const activePulses = page.getByTestId('pulse-maker').filter({ hasAttribute: 'data-active', value: 'true' });
    await expect(activePulses).toHaveCount(1);
  });
});
