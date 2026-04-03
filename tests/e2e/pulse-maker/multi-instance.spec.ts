import { test, expect } from '@playwright/test';
import { createAgent, createVoiceEvent } from '../../factories/agent-factory';

/**
 * Pulse-Maker Multi-Instance Tests
 * Story: 2.5 - Pulse-Maker Visual Visualizer Component
 * Epic: 2 - Real-Time AI Voice Pipeline
 *
 * Test ID Format: 2.5-E2E-XXX
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('Pulse-Maker Multi-Instance Fleet Navigator Integration', () => {
  /**
   * Test ID: 2.5-E2E-011
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC7
   *
   * Validates state isolation between multiple Pulse instances.
   * Tests that triggering voice event for one agent doesn't affect others.
   */
  test('[P0] @smoke @p0 should maintain state isolation across multiple Pulse instances', async ({ page }) => {
    // Create test agents with factory (unique, parallel-safe)
    const agent1 = createAgent({ name: 'Agent 1', status: 'active' });
    const agent2 = createAgent({ name: 'Agent 2', status: 'active' });
    const agent3 = createAgent({ name: 'Agent 3', status: 'active' });

    await page.goto('/dashboard');

    // Wait for all Pulse instances to render (deterministic)
    await page.waitForSelector('[data-pulse-maker="true"]', { state: 'attached' });

    const pulses = page.getByTestId('pulse-maker');
    await expect(pulses).toHaveCount(3);

    // Verify each Pulse has unique agentId
    const agentIds = await pulses.all().map(async (pulse) => {
      return await pulse.getAttribute('data-agent-id');
    });

    const uniqueIds = new Set(agentIds);
    expect(uniqueIds.size).toBe(3);

    // Trigger event for agent-1 only
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
    const activePulses = pulses.filter({ hasAttribute: 'data-active', value: 'true' });
    await expect(activePulses).toHaveCount(1);

    // Verify it's the correct agent
    await expect(activePulses.first()).toHaveAttribute('data-agent-id', agent1.id);

    // Other agents should remain idle
    const idlePulses = pulses.filter({ hasAttribute: 'data-active', value: 'false' });
    await expect(idlePulses).toHaveCount(2);
  });

  /**
   * Test ID: 2.5-E2E-012
   * Priority: P1
   * Tags: @p1
   * AC: AC7
   *
   * Validates that multiple simultaneous voice events are handled correctly.
   * Tests concurrent state changes across different agent instances.
   */
  test('[P1] @p1 should handle multiple simultaneous voice events', async ({ page }) => {
    // Create test agents
    const agent1 = createAgent({ name: 'Agent 1' });
    const agent2 = createAgent({ name: 'Agent 2' });
    const agent3 = createAgent({ name: 'Agent 3' });

    await page.goto('/dashboard');

    // Wait for all Pulse instances
    await page.waitForSelector('[data-pulse-maker="true"]', { state: 'attached' });

    const pulses = page.getByTestId('pulse-maker');
    await expect(pulses).toHaveCount(3);

    // Trigger simultaneous events for all agents
    await page.evaluate((agents) => {
      agents.forEach(agent => {
        window.dispatchEvent(new CustomEvent('voice-event', {
          detail: {
            eventType: 'speech-start',
            agentId: agent.id,
            volume: 0.8
          }
        }));
      });
    }, [agent1, agent2, agent3]);

    // All pulses should be active (deterministic check)
    const activePulses = pulses.filter({ hasAttribute: 'data-active', value: 'true' });
    await expect(activePulses).toHaveCount(3);

    // Verify all have correct volume
    for (const pulse of await activePulses.all()) {
      await expect(pulse).toHaveAttribute('data-volume', '0.8');
    }
  });

  /**
   * Test ID: 2.5-E2E-013
   * Priority: P2
   * Tags: @p2
   * AC: AC7
   *
   * Validates that Fleet Navigator correctly positions multiple Pulse instances.
   * Tests layout integrity with multiple active agents.
   */
  test('[P2] @p2 should correctly position Pulse instances in Fleet Navigator layout', async ({ page }) => {
    const agents = [createAgent(), createAgent(), createAgent()];

    await page.goto('/dashboard');

    // Wait for Fleet Navigator
    const fleetNav = page.getByRole('navigation', { name: 'Fleet Navigator' });
    await expect(fleetNav).toBeVisible();

    // Wait for all Pulse instances
    await page.waitForSelector('[data-pulse-maker="true"]', { state: 'attached' });

    const pulses = page.getByTestId('pulse-maker');
    await expect(pulses).toHaveCount(3);

    // Verify all pulses are visible and positioned
    for (const pulse of await pulses.all()) {
      await expect(pulse).toBeVisible();

      // Check positioning (should be within Fleet Navigator bounds)
      const box = await pulse.boundingBox();
      expect(box).toBeTruthy();
      expect(box!.width).toBeGreaterThan(0);
      expect(box!.height).toBeGreaterThan(0);
    }

    // Verify Fleet Navigator layout structure
    await expect(fleetNav).toHaveClass(/flex/);
    await expect(fleetNav).toHaveClass(/bg-card/);
  });
});
