import { faker } from '@faker-js/faker';

/**
 * Agent type definition matching the application schema
 */
export type Agent = {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'offline';
  email?: string;
  role?: 'user' | 'admin' | 'moderator';
  createdAt: Date;
  isActive: boolean;
};

/**
 * Voice Event type definition
 */
export type VoiceEvent = {
  type: 'speech_state' | 'interruption';
  data: {
    eventType: 'speech-start' | 'speech-end' | 'interruption';
    agentId: string;
    timestamp: number;
    volume?: number;
    sentiment?: number;
  };
};

/**
 * Factory function to create agent test data with unique values
 * Prevents parallel test collisions using faker for dynamic data
 *
 * @param overrides - Partial agent data to override defaults
 * @returns Complete agent object with unique ID and timestamp
 *
 * @example
 * // Default agent
 * const agent = createAgent();
 *
 * // Admin agent with explicit name
 * const admin = createAgent({ name: 'Test Admin', role: 'admin' });
 *
 * // Inactive agent
 * const inactive = createAgent({ status: 'offline', isActive: false });
 */
export const createAgent = (overrides: Partial<Agent> = {}): Agent => ({
  id: faker.string.uuid(),
  name: faker.person.firstName(),
  status: 'active',
  email: faker.internet.email(),
  role: 'user',
  createdAt: faker.date.recent({ days: 1 }),
  isActive: true,
  ...overrides,
});

/**
 * Factory function to create specialized admin agents
 * Shorthand for createAgent({ role: 'admin', ...overrides })
 */
export const createAdminAgent = (overrides: Partial<Agent> = {}): Agent =>
  createAgent({ role: 'admin', name: `Admin ${faker.person.firstName()}`, ...overrides });

/**
 * Factory function to create inactive/offline agents
 */
export const createInactiveAgent = (overrides: Partial<Agent> = {}): Agent =>
  createAgent({ status: 'offline', isActive: false, ...overrides });

/**
 * Factory function to create voice event test data
 * Generates unique timestamps to prevent timing collisions
 *
 * @param eventType - The type of voice event
 * @param agentId - The agent ID (optional, will generate if not provided)
 * @param volume - Speaking volume 0-1 (optional)
 * @param sentiment - Sentiment score 0-1 (optional, defaults to 0.5)
 * @returns Complete voice event object
 *
 * @example
 * // Speech start event with defaults
 * const event = createVoiceEvent('speech-start');
 *
 * // Speech end with specific volume
 * const endEvent = createVoiceEvent('speech-end', 'agent-123', 0.3);
 *
 * // Interruption event
 * const interruption = createVoiceEvent('interruption');
 */
export const createVoiceEvent = (
  eventType: 'speech-start' | 'speech-end' | 'interruption',
  agentId?: string,
  volume: number = 0.5,
  sentiment: number = 0.5,
): VoiceEvent => ({
  type: eventType === 'interruption' ? 'interruption' : 'speech_state',
  data: {
    eventType,
    agentId: agentId || faker.string.uuid(),
    timestamp: Date.now(),
    volume: eventType === 'interruption' ? undefined : volume,
    sentiment: eventType === 'interruption' ? undefined : sentiment,
  },
});

/**
 * Factory function to create a speaking voice event (volume >= threshold)
 * Uses VOLUME_THRESHOLD constant (0.8) from application constants
 */
export const createSpeakingEvent = (agentId?: string): VoiceEvent =>
  createVoiceEvent('speech-start', agentId, 0.8, 0.5);

/**
 * Factory function to create an idle voice event (volume < threshold)
 */
export const createIdleEvent = (agentId?: string): VoiceEvent =>
  createVoiceEvent('speech-end', agentId, 0.0, 0.5);

/**
 * Factory function to create an interruption event
 */
export const createInterruptionEvent = (agentId?: string): VoiceEvent =>
  createVoiceEvent('interruption', agentId);
