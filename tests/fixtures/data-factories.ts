/**
 * Data Factories for Test Data Generation
 *
 * Provides factory functions for generating test data with overrides.
 * Uses faker.js for unique, parallel-safe test data.
 */

import { faker } from '@faker-js/faker';

/**
 * Agent Data Factory
 *
 * Generates agent test data with sensible defaults and overrides.
 *
 * @param overrides - Partial agent data to override defaults
 * @returns Complete agent object
 *
 * Usage:
 * ```typescript
 * const agent = createAgentData({
 *   id: 'custom-agent-id',
 *   status: 'active'
 * });
 * ```
 */
export function createAgentData(overrides: Partial<ReturnType<typeof createAgentData>> = {}) {
  return {
    id: faker.string.uuid(),
    name: faker.person.fullName(),
    status: 'active' as const,
    callCount: faker.number.int({ min: 0, max: 20 }),
    lastCallAt: faker.date.recent({ days: 1 }).toISOString(),
    ...overrides,
  };
}

/**
 * Voice Event Data Factory
 *
 * Generates voice event test data with overrides.
 *
 * @param overrides - Partial voice event data to override defaults
 * @returns Complete voice event object
 *
 * Usage:
 * ```typescript
 * const event = createVoiceEventData({
 *   eventType: 'speech-start',
 *   volume: 0.9
 * });
 * ```
 */
export function createVoiceEventData(overrides: Partial<ReturnType<typeof createVoiceEventData>> = {}) {
  return {
    eventType: faker.helpers.arrayElement(['speech-start', 'speech-end', 'interruption']) as any,
    agentId: faker.string.uuid(),
    timestamp: faker.date.recent().getTime(),
    volume: faker.number.float({ min: 0, max: 1, precision: 0.01 }),
    ...overrides,
  };
}

/**
 * User Data Factory
 *
 * Generates user test data with overrides.
 *
 * @param overrides - Partial user data to override defaults
 * @returns Complete user object
 *
 * Usage:
 * ```typescript
 * const user = createUserData({
 *   email: 'test@example.com',
 *   role: 'admin'
 * });
 * ```
 */
export function createUserData(overrides: Partial<ReturnType<typeof createUserData>> = {}) {
  return {
    id: faker.string.uuid(),
    name: faker.person.fullName(),
    email: faker.internet.email(),
    role: 'user' as const,
    createdAt: faker.date.past().toISOString(),
    isActive: true,
    ...overrides,
  };
}

/**
 * Organization Data Factory
 *
 * Generates organization test data with overrides.
 *
 * @param overrides - Partial organization data to override defaults
 * @returns Complete organization object
 */
export function createOrganizationData(overrides: Partial<ReturnType<typeof createOrganizationData>> = {}) {
  return {
    id: faker.string.uuid(),
    name: faker.company.name(),
    slug: faker.helpers.slugify(faker.company.name()).toLowerCase(),
    branding: {
      primaryColor: faker.internet.color(),
      logo: faker.image.url(),
      ...overrides.branding,
    },
    createdAt: faker.date.past().toISOString(),
    ...overrides,
  };
}

/**
 * Call Session Data Factory
 *
 * Generates call session test data with overrides.
 *
 * @param overrides - Partial call session data to override defaults
 * @returns Complete call session object
 */
export function createCallSessionData(overrides: Partial<ReturnType<typeof createCallSessionData>> = {}) {
  const startTime = faker.date.recent();
  return {
    id: faker.string.uuid(),
    agentId: faker.string.uuid(),
    startTime: startTime.toISOString(),
    endTime: faker.date.between({ from: startTime, to: new Date() }).toISOString(),
    duration: faker.number.int({ min: 30, max: 3600 }), // 30s to 1hr
    status: faker.helpers.arrayElement(['active', 'completed', 'failed']) as any,
    transcriptEntries: faker.number.int({ min: 0, max: 100 }),
    ...overrides,
  };
}

/**
 * Transcript Entry Data Factory
 *
 * Generates transcript entry test data with overrides.
 *
 * @param overrides - Partial transcript entry data to override defaults
 * @returns Complete transcript entry object
 */
export function createTranscriptEntryData(overrides: Partial<ReturnType<typeof createTranscriptEntryData>> = {}) {
  return {
    id: faker.string.uuid(),
    agentId: faker.string.uuid(),
    content: faker.lorem.sentence(),
    timestamp: faker.date.recent().getTime(),
    eventType: faker.helpers.arrayElement(['speech-start', 'speech-end', 'interruption', 'transcript']) as any,
    sentiment: faker.number.float({ min: 0, max: 1, precision: 0.01 }),
    ...overrides,
  };
}

/**
 * Batch Data Factory
 *
 * Creates multiple objects of the same type with unique data.
 * Useful for testing with multiple agents, calls, etc.
 *
 * @param factory - Factory function to call
 * @param count - Number of objects to create
 * @param overrides - Optional overrides to apply to all objects
 * @returns Array of generated objects
 *
 * Usage:
 * ```typescript
 * const agents = createBatch(createAgentData, 5, { status: 'active' });
 * expect(agents).toHaveLength(5);
 * expect(new Set(agents.map(a => a.id)).size).toBe(5); // All unique
 * ```
 */
export function createBatch<T>(
  factory: (overrides?: any) => T,
  count: number,
  overrides?: any
): T[] {
  return Array.from({ length: count }, () => factory(overrides));
}
