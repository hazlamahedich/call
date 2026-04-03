import { Page } from '@playwright/test';

/**
 * Voice Event Mock Fixtures for E2E Tests
 *
 * Provides utilities to mock WebSocket voice events for testing Pulse-Maker.
 * Simulates speech-start, speech-end, and interruption events.
 */

export type VoiceEventType = 'speech-start' | 'speech-end' | 'interruption';

export interface VoiceEvent {
  eventType: VoiceEventType;
  agentId?: string;
  timestamp: number;
  volume?: number;
}

/**
 * Mock Voice Event Fixture
 *
 * Dispatches voice events to the window for testing Pulse-Maker behavior.
 * Tests can simulate real-time voice activity without actual WebSocket connection.
 *
 * @param page - Playwright Page object
 * @param event - Voice event to dispatch
 *
 * Usage:
 * ```typescript
 * import { mockVoiceEvent } from './fixtures/voice-event-mock.fixture';
 *
 * test('pulse responds to speech-start', async ({ page }) => {
 *   await mockVoiceEvent(page, {
 *     eventType: 'speech-start',
 *     agentId: 'agent-123',
 *     timestamp: Date.now(),
 *     volume: 0.8
 *   });
 *
 *   const pulse = page.getByTestId('pulse-maker');
 *   await expect(pulse).toHaveAttribute('data-active', 'true');
 * });
 * ```
 */
export async function mockVoiceEvent(page: Page, event: VoiceEvent): Promise<void> {
  await page.evaluate((eventData) => {
    window.dispatchEvent(new CustomEvent('voice-event', { detail: eventData }));
  }, event);
}

/**
 * Mock Speech Start Event
 *
 * Convenience function to dispatch a speech-start event.
 *
 * @param page - Playwright Page object
 * @param agentId - Agent ID (optional)
 * @param volume - Volume level (default: 0.8)
 */
export async function mockSpeechStart(page: Page, agentId?: string, volume = 0.8): Promise<void> {
  await mockVoiceEvent(page, {
    eventType: 'speech-start',
    agentId,
    timestamp: Date.now(),
    volume,
  });
}

/**
 * Mock Speech End Event
 *
 * Convenience function to dispatch a speech-end event.
 *
 * @param page - Playwright Page object
 * @param agentId - Agent ID (optional)
 */
export async function mockSpeechEnd(page: Page, agentId?: string): Promise<void> {
  await mockVoiceEvent(page, {
    eventType: 'speech-end',
    agentId,
    timestamp: Date.now(),
    volume: 0.0,
  });
}

/**
 * Mock Interruption Event
 *
 * Convenience function to dispatch an interruption event.
 *
 * @param page - Playwright Page object
 * @param agentId - Agent ID (optional)
 */
export async function mockInterruption(page: Page, agentId?: string): Promise<void> {
  await mockVoiceEvent(page, {
    eventType: 'interruption',
    agentId,
    timestamp: Date.now(),
  });
}

/**
 * Mock Voice Event Sequence
 *
 * Dispatches a sequence of voice events to simulate a conversation.
 * Useful for testing exponential decay and animation changes.
 *
 * @param page - Playwright Page object
 * @param agentId - Agent ID
 *
 * Usage:
 * ```typescript
 * test('pulse quickens then slows', async ({ page }) => {
 *   await mockVoiceEventSequence(page, 'agent-123');
 *   // Tests speech-start → speech-end sequence
 * });
 * ```
 */
export async function mockVoiceEventSequence(page: Page, agentId: string): Promise<void> {
  // Speech start
  await mockSpeechStart(page, agentId, 0.8);
  await page.waitForTimeout(200);

  // Speech end
  await mockSpeechEnd(page, agentId);

  // Wait for exponential decay to complete
  await page.waitForTimeout(600);
}

/**
 * Setup Voice Event Listener
 *
 * Sets up a listener for voice events and returns a promise that resolves
 * when the next matching event is received.
 *
 * @param page - Playwright Page object
 * @param eventType - Event type to listen for
 * @returns Promise that resolves with the event data
 *
 * Usage:
 * ```typescript
 * test('listens for voice events', async ({ page }) => {
 *   const eventPromise = setupVoiceEventListener(page, 'speech-start');
 *
 *   await mockSpeechStart(page, 'agent-123');
 *
 *   const event = await eventPromise;
 *   expect(event.eventType).toBe('speech-start');
 * });
 * ```
 */
export function setupVoiceEventListener(
  page: Page,
  eventType: VoiceEventType
): Promise<VoiceEvent> {
  return page.evaluate((type) => {
    return new Promise<VoiceEvent>((resolve) => {
      const handler = (e: CustomEvent<VoiceEvent>) => {
        if (e.detail.eventType === type) {
          window.removeEventListener('voice-event', handler);
          resolve(e.detail);
        }
      };
      window.addEventListener('voice-event', handler);
    });
  }, eventType);
}
