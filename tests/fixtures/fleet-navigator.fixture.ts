import { Page, expect } from '@playwright/test';

/**
 * Fleet Navigator Fixture for E2E Tests
 *
 * Provides utilities for testing Fleet Navigator integration with Pulse-Maker.
 * Handles agent list management and multi-agent state testing.
 */

export interface Agent {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'offline';
  callCount?: number;
}

/**
 * Setup Fleet Navigator with Agents
 *
 * Initializes Fleet Navigator with multiple active agents for testing.
 * Dispatches a custom event that simulates agent data loading.
 *
 * @param page - Playwright Page object
 * @param agents - Array of agents to load
 *
 * Usage:
 * ```typescript
 * test('multiple agents display', async ({ page }) => {
 *   await setupFleetNavigator(page, [
 *     { id: 'agent-1', name: 'Agent 1', status: 'active' },
 *     { id: 'agent-2', name: 'Agent 2', status: 'active' },
 *     { id: 'agent-3', name: 'Agent 3', status: 'active' },
 *   ]);
 *
 *   const pulses = page.getByTestId('pulse-maker');
 *   await expect(pulses).toHaveCount(3);
 * });
 * ```
 */
export async function setupFleetNavigator(page: Page, agents: Agent[]): Promise<void> {
  await page.evaluate((agentData) => {
    window.dispatchEvent(new CustomEvent('agents-loaded', {
      detail: { agents: agentData }
    }));
  }, agents);

  // Wait for agents to render
  await page.waitForTimeout(100);
}

/**
 * Get Agent Pulse Element
 *
 * Returns the Pulse-Maker element for a specific agent.
 *
 * @param page - Playwright Page object
 * @param agentId - Agent ID to find
 * @returns Locator for the agent's Pulse-Maker
 *
 * Usage:
 * ```typescript
 * test('specific agent pulse', async ({ page }) => {
 *   const pulse = await getAgentPulse(page, 'agent-123');
 *   await expect(pulse).toBeVisible();
 * });
 * ```
 */
export async function getAgentPulse(page: Page, agentId: string) {
  return page.getByTestId(`pulse-maker-${agentId}`);
}

/**
 * Verify Agent Pulse State
 *
 * Asserts that an agent's Pulse-Maker has the expected state.
 *
 * @param page - Playwright Page object
 * @param agentId - Agent ID to verify
 * @param isActive - Expected active state
 * @param volume - Expected volume level (optional)
 *
 * Usage:
 * ```typescript
 * test('agent pulse state', async ({ page }) => {
 *   await verifyAgentPulseState(page, 'agent-123', true, 0.8);
 * });
 * ```
 */
export async function verifyAgentPulseState(
  page: Page,
  agentId: string,
  isActive: boolean,
  volume?: number
): Promise<void> {
  const pulse = await getAgentPulse(page, agentId);

  await expect(pulse).toHaveAttribute('data-agent-id', agentId);
  await expect(pulse).toHaveAttribute('data-active', isActive.toString());

  if (volume !== undefined) {
    await expect(pulse).toHaveAttribute('data-volume', volume.toString());
  }
}

/**
 * Count Active Agents
 *
 * Returns the number of active agents in Fleet Navigator.
 *
 * @param page - Playwright Page object
 * @returns Number of active agents
 *
 * Usage:
 * ```typescript
 * test('count active agents', async ({ page }) => {
 *   const count = await countActiveAgents(page);
 *   expect(count).toBe(3);
 * });
 * ```
 */
export async function countActiveAgents(page: Page): Promise<number> {
  const pulses = page.getByTestId('pulse-maker');
  const count = await pulses.count();
  return count;
}

/**
 * Verify All Pulse Makers Have Unique IDs
 *
 * Asserts that all Pulse-Maker instances have unique agent IDs.
 * This is critical for state isolation in multi-agent scenarios.
 *
 * @param page - Playwright Page object
 *
 * Usage:
 * ```typescript
 * test('unique agent IDs', async ({ page }) => {
 *   await verifyUniqueAgentIds(page);
 *   // Throws if duplicate IDs found
 * });
 * ```
 */
export async function verifyUniqueAgentIds(page: Page): Promise<void> {
  const pulses = page.getByTestId('pulse-maker');
  const count = await pulses.count();

  const agentIds: string[] = [];
  for (let i = 0; i < count; i++) {
    const pulse = pulses.nth(i);
    const agentId = await pulse.getAttribute('data-agent-id');
    expect(agentId).toBeTruthy();
    agentIds.push(agentId!);
  }

  const uniqueIds = new Set(agentIds);
  expect(uniqueIds.size).toBe(count);
}

/**
 * Setup Multi-Agent Scenario
 *
 * Convenience function to setup Fleet Navigator with multiple active agents
 * and verify all Pulse-Makers render correctly.
 *
 * @param page - Playwright Page object
 * @param agentCount - Number of agents to create
 * @returns Array of created agent IDs
 *
 * Usage:
 * ```typescript
 * test('multi-agent scenario', async ({ page }) => {
 *   const agentIds = await setupMultiAgentScenario(page, 3);
 *   expect(agentIds).toHaveLength(3);
 *
 *   // Trigger voice event for first agent
 *   await mockSpeechStart(page, agentIds[0]);
 *
 *   // Verify state isolation
 *   await verifyAgentPulseState(page, agentIds[0], true);
 *   await verifyAgentPulseState(page, agentIds[1], false);
 * });
 * ```
 */
export async function setupMultiAgentScenario(
  page: Page,
  agentCount: number
): Promise<string[]> {
  const agents: Agent[] = Array.from({ length: agentCount }, (_, i) => ({
    id: `agent-${i + 1}`,
    name: `Agent ${i + 1}`,
    status: 'active',
    callCount: Math.floor(Math.random() * 10),
  }));

  await setupFleetNavigator(page, agents);

  // Verify all pulses rendered
  const pulses = page.getByTestId('pulse-maker');
  await expect(pulses).toHaveCount(agentCount);

  // Verify unique IDs
  await verifyUniqueAgentIds(page);

  return agents.map((a) => a.id);
}

/**
 * Mock WebSocket Connection
 *
 * Mocks the WebSocket connection for voice events.
 * This is useful for testing without actual WebSocket server.
 *
 * @param page - Playwright Page object
 *
 * Usage:
 * ```typescript
 * test('with WebSocket mock', async ({ page }) => {
 *   await mockWebSocketConnection(page);
 *
 *   // Now voice events will be intercepted
 *   await mockSpeechStart(page, 'agent-123');
 * });
 * ```
 */
export async function mockWebSocketConnection(page: Page): Promise<void> {
  // Route WebSocket events to mock endpoint
  await page.route('**/api/v1/calls/voice-events', async (route) => {
    // Allow the request to continue (don't block)
    // The mock is done via window.dispatchEvent instead
    await route.continue();
  });
}
