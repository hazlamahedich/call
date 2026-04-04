/**
 * Test Data Factory Functions for Story 2.6 - Voice Presets
 *
 * Provides factory functions with overrides for generating test data.
 * Follows data-factories.md best practices from TEA knowledge base.
 */

import { faker } from "@faker-js/faker";

/**
 * Voice Preset Factory
 * Creates voice preset objects with sensible defaults and override support
 */
export function createVoicePreset(overrides: Partial<VoicePreset> = {}): VoicePreset {
  const useCases = ["sales", "support", "marketing"] as const;
  const useCase = useCases[Math.floor(Math.random() * useCases.length)];

  return {
    id: faker.number.int({ min: 1, max: 1000 }),
    name: `${useCase.charAt(0).toUpperCase() + useCase.slice(1)} - ${faker.person.fullName()}`,
    use_case: useCase,
    voice_id: `voice-${faker.string.uuid()}`,
    speech_speed: faker.number.float({ min: 0.8, max: 1.2, precision: 0.1 }),
    stability: faker.number.float({ min: 0.5, max: 1.0, precision: 0.1 }),
    temperature: faker.number.float({ min: 0.3, max: 0.9, precision: 0.1 }),
    description: faker.lorem.sentence(),
    is_active: true,
    sort_order: faker.number.int({ min: 1, max: 10 }),
    ...overrides,
  };
}

/**
 * Voice Preset Factory for Specific Use Cases
 */
export function createSalesPreset(overrides: Partial<VoicePreset> = {}): VoicePreset {
  return createVoicePreset({
    use_case: "sales",
    name: `Sales - ${faker.person.fullName()}`,
    ...overrides,
  });
}

export function createSupportPreset(overrides: Partial<VoicePreset> = {}): VoicePreset {
  return createVoicePreset({
    use_case: "support",
    name: `Support - ${faker.person.fullName()}`,
    ...overrides,
  });
}

export function createMarketingPreset(overrides: Partial<VoicePreset> = {}): VoicePreset {
  return createVoicePreset({
    use_case: "marketing",
    name: `Marketing - ${faker.person.fullName()}`,
    ...overrides,
  });
}

/**
 * User Factory (for tenant isolation tests)
 */
export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: faker.string.uuid(),
    email: faker.internet.email(),
    name: faker.person.fullName(),
    role: "user",
    org_id: faker.string.uuid(),
    ...overrides,
  };
}

export function createAdminUser(overrides: Partial<User> = {}): User {
  return createUser({
    role: "admin",
    ...overrides,
  });
}

/**
 * Agent Factory (for multi-agent tests)
 */
export function createAgent(overrides: Partial<Agent> = {}): Agent {
  return {
    id: faker.string.uuid(),
    name: `${faker.person.firstName()} Agent ${faker.number.int({ min: 1, max: 10 })}`,
    preset_id: faker.number.int({ min: 1, max: 100 }),
    org_id: faker.string.uuid(),
    ...overrides,
  };
}

/**
 * Recommendation Factory (for AC6 tests)
 */
export function createRecommendation(overrides: Partial<Recommendation> = {}): Recommendation {
  return {
    preset_name: faker.helpers.arrayElement([
      "Sales - Rachel",
      "Sales - Alex",
      "Support - James",
      "Marketing - Sophia",
    ]),
    improvement_pct: faker.number.int({ min: 10, max: 30 }),
    reasoning: faker.lorem.sentence(),
    ...overrides,
  };
}

/**
 * Audio Sample Factory
 */
export function createAudioSample(overrides: Partial<AudioSample> = {}): AudioSample {
  const bufferSize = 1024 * 10; // 10KB mock audio
  return {
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(bufferSize)),
    duration: faker.number.int({ min: 3, max: 10 }),
    format: "mp3",
    ...overrides,
  };
}

// Type definitions
export interface VoicePreset {
  id: number;
  name: string;
  use_case: "sales" | "support" | "marketing";
  voice_id: string;
  speech_speed: number;
  stability: number;
  temperature: number;
  description: string;
  is_active: boolean;
  sort_order: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string;
}

export interface Agent {
  id: string;
  name: string;
  preset_id: number;
  org_id: string;
}

export interface Recommendation {
  preset_name: string;
  improvement_pct: number;
  reasoning: string;
}

export interface AudioSample {
  arrayBuffer: () => Promise<ArrayBuffer>;
  duration?: number;
  format?: string;
}
