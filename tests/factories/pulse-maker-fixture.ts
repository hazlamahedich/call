import { test as base } from '@playwright/test';
import { createAgent, createVoiceEvent, createSpeakingEvent, createIdleEvent, createInterruptionEvent } from '../factories/agent-factory';

/**
 * PulseMaker Test Fixture
 *
 * Provides reusable test utilities for Pulse-Maker component testing.
 * Extends Playwright's base test with custom fixtures for agent and voice event creation.
 *
 * @example
 * test('my test', async ({ page, createMockAgent, createMockVoiceEvent }) => {
 *   const agent = createMockAgent({ name: 'Test Agent' });
 *   const event = createMockVoiceEvent('speech-start', agent.id);
 * });
 */

export type PulseMakerFixture = {
  /**
   * Factory function to create mock agent data
   * @param overrides - Partial agent data to override defaults
   * @returns Complete agent object with unique ID
   */
  createMockAgent: (overrides?: Partial<{
    id: string;
    name: string;
    status: 'active' | 'idle' | 'offline';
    email: string;
    role: 'user' | 'admin' | 'moderator';
    createdAt: Date;
    isActive: boolean;
  }>) => ReturnType<typeof createAgent>;

  /**
   * Factory function to create mock voice event data
   * @param eventType - Type of voice event
   * @param agentId - Agent ID (optional, generates unique if not provided)
   * @param volume - Speaking volume 0-1 (default: 0.5)
   * @param sentiment - Sentiment 0-1 (default: 0.5)
   * @returns Complete voice event object
   */
  createMockVoiceEvent: (
    eventType: 'speech-start' | 'speech-end' | 'interruption',
    agentId?: string,
    volume?: number,
    sentiment?: number,
  ) => ReturnType<typeof createVoiceEvent>;

  /**
   * Factory function to create a speaking voice event (volume >= 0.8)
   */
  createSpeakingEvent: (agentId?: string) => ReturnType<typeof createSpeakingEvent>;

  /**
   * Factory function to create an idle voice event (volume = 0.0)
   */
  createIdleEvent: (agentId?: string) => ReturnType<typeof createIdleEvent>;

  /**
   * Factory function to create an interruption event
   */
  createInterruptionEvent: (agentId?: string) => ReturnType<typeof createInterruptionEvent>;
};

/**
 * Extended test object with PulseMaker fixtures
 * Use this instead of Playwright's default `test` in Pulse-Maker test files
 */
export const test = base.extend<PulseMakerFixture>({
  createMockAgent: async ({}, use) => {
    // Provide the factory function to tests
    await use(createAgent);
  },

  createMockVoiceEvent: async ({}, use) => {
    await use(createVoiceEvent);
  },

  createSpeakingEvent: async ({}, use) => {
    await use(createSpeakingEvent);
  },

  createIdleEvent: async ({}, use) => {
    await use(createIdleEvent);
  },

  createInterruptionEvent: async ({}, use) => {
    await use(createInterruptionEvent);
  },
});

/**
 * Re-export expect for convenience
 */
export const expect = base.expect;
