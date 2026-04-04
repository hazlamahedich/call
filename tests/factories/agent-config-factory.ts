import { faker } from '@faker-js/faker';

/**
 * Voice Provider type definition
 * Matches the VoiceProvider enum from packages/types
 */
export type VoiceProvider = 'elevenlabs' | 'cartesia' | 'openai';

/**
 * Agent Config type definition matching the API schema
 * Based on AgentConfig SQLModel from apps/api/models/agent_config.py
 */
export type AgentConfig = {
  id?: number;
  agent_id: number;
  org_id: number;
  voice_id: string;
  voice_provider?: VoiceProvider;
  speech_speed: number;
  stability: number;
  temperature?: number;
  use_legacy_behavior?: boolean;
  custom_voice_settings?: Record<string, unknown>;
  updated_at?: string;
  created_at?: string;
};

/**
 * Voice configuration for audio test requests
 * Matches AudioTestRequest schema from apps/api/schemas/agent_config.py
 */
export type AudioTestRequest = {
  text: string;
  voice_config: AgentConfig;
};

/**
 * Voice ID pool for realistic test data
 * Matches default voice IDs from providers
 */
const VOICE_IDS = {
  elevenlabs: [
    'eleven_multilingual_v1',
    'eleven_turbo_v2',
    'eleven_monolingual_v1',
    'rachel', 'domi', 'bella', 'antoni', 'elli',
  ],
  cartesia: [
    'sonic-english',
    'sonic-multilingual',
    'cartesia-english-1',
    'cartesia-multilingual-2',
  ],
  openai: [
    'alloy',
    'echo',
    'fable',
    'onyx',
    'nova',
    'shimmer',
  ],
} as const;

/**
 * Factory function to create unique agent_id
 * Uses faker to generate unique integers for API compatibility
 *
 * @returns Unique agent ID as number
 *
 * @example
 * const agentId = createAgentId();
 * // => 123456
 */
export const createAgentId = (): number => faker.number.int({ min: 100000, max: 999999 });

/**
 * Factory function to create unique org_id
 * Uses faker to generate unique integers for API compatibility
 *
 * @returns Unique org ID as number
 *
 * @example
 * const orgId = createOrgId();
 * // => 12345
 */
export const createOrgId = (): number => faker.number.int({ min: 10000, max: 99999 });

/**
 * Factory function to create realistic voice_id for a provider
 * Selects from known voice IDs for each provider
 *
 * @param provider - Voice provider (defaults to random provider)
 * @returns Realistic voice ID string
 *
 * @example
 * const voiceId = createVoiceId('elevenlabs');
 * // => 'rachel' or 'eleven_turbo_v2'
 *
 * const randomVoiceId = createVoiceId();
 * // => any voice from any provider
 */
export const createVoiceId = (provider?: VoiceProvider): string => {
  const selectedProvider = provider || faker.helpers.arrayElement(['elevenlabs', 'cartesia', 'openai'] as VoiceProvider[]);
  const voices = VOICE_IDS[selectedProvider];
  return faker.helpers.arrayElement(voices);
};

/**
 * Factory function to create a random voice provider
 *
 * @returns Random voice provider
 */
export const createVoiceProvider = (): VoiceProvider => {
  return faker.helpers.arrayElement(['elevenlabs', 'cartesia', 'openai'] as VoiceProvider[]);
};

/**
 * Factory function to create agent config test data
 * Generates unique values to prevent parallel test collisions
 *
 * @param overrides - Partial config data to override defaults
 * @returns Complete agent config object with unique IDs
 *
 * @example
 * // Default config with unique IDs
 * const config = createAgentConfig();
 *
 * // Fast speech config
 * const fastConfig = createAgentConfig({
 *   speech_speed: 1.8,
 *   stability: 0.5,
 * });
 *
 * // Config for specific org/agent
 * const customConfig = createAgentConfig({
 *   org_id: 12345,
 *   agent_id: 67890,
 *   voice_provider: 'elevenlabs',
 * });
 */
export const createAgentConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => {
  const provider = overrides.voice_provider || createVoiceProvider();

  return {
    agent_id: createAgentId(),
    org_id: createOrgId(),
    voice_id: createVoiceId(provider),
    voice_provider: provider,
    speech_speed: faker.number.float({ min: 0.5, max: 2.0, precision: 0.1 }),
    stability: faker.number.float({ min: 0.0, max: 1.0, precision: 0.1 }),
    temperature: faker.number.float({ min: 0.0, max: 1.0, precision: 0.1 }),
    use_legacy_behavior: faker.datatype.boolean(),
    custom_voice_settings: {},
    updated_at: faker.date.recent({ days: 1 }).toISOString(),
    created_at: faker.date.recent({ days: 7 }).toISOString(),
    ...overrides,
  };
};

/**
 * Factory function to create default agent config
 * Uses sensible defaults for most tests
 * speech_speed: 1.0 (normal), stability: 0.8 (stable)
 *
 * @param overrides - Partial config data to override defaults
 * @returns Agent config with standard default values
 *
 * @example
 * const defaultConfig = createDefaultAgentConfig();
 * // => { speech_speed: 1.0, stability: 0.8, ... }
 */
export const createDefaultAgentConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => {
  return createAgentConfig({
    speech_speed: 1.0,
    stability: 0.8,
    temperature: 0.7,
    use_legacy_behavior: false,
    ...overrides,
  });
};

/**
 * Factory function to create fast speech config
 * Higher speech_speed (1.5-2.0), lower stability for expressiveness
 *
 * @param overrides - Partial config data to override defaults
 * @returns Agent config optimized for fast speech
 */
export const createFastSpeechConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => {
  return createAgentConfig({
    speech_speed: faker.number.float({ min: 1.5, max: 2.0, precision: 0.1 }),
    stability: faker.number.float({ min: 0.3, max: 0.6, precision: 0.1 }),
    ...overrides,
  });
};

/**
 * Factory function to create slow speech config
 * Lower speech_speed (0.5-0.8), higher stability for consistency
 *
 * @param overrides - Partial config data to override defaults
 * @returns Agent config optimized for slow, clear speech
 */
export const createSlowSpeechConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => {
  return createAgentConfig({
    speech_speed: faker.number.float({ min: 0.5, max: 0.8, precision: 0.1 }),
    stability: faker.number.float({ min: 0.8, max: 1.0, precision: 0.1 }),
    ...overrides,
  });
};

/**
 * Factory function to create highly stable config
 * Maximum stability (0.9-1.0), moderate speech speed
 * Good for professional/serious voice output
 *
 * @param overrides - Partial config data to override defaults
 * @returns Agent config optimized for consistency
 */
export const createStableConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => {
  return createAgentConfig({
    speech_speed: faker.number.float({ min: 0.9, max: 1.1, precision: 0.1 }),
    stability: faker.number.float({ min: 0.9, max: 1.0, precision: 0.05 }),
    ...overrides,
  });
};

/**
 * Factory function to create expressive config
 * Lower stability (0.0-0.5) for varied, emotional speech
 * Good for storytelling, casual conversations
 *
 * @param overrides - Partial config data to override defaults
 * @returns Agent config optimized for expressiveness
 */
export const createExpressiveConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => {
  return createAgentConfig({
    speech_speed: faker.number.float({ min: 0.9, max: 1.2, precision: 0.1 }),
    stability: faker.number.float({ min: 0.0, max: 0.5, precision: 0.1 }),
    temperature: faker.number.float({ min: 0.7, max: 1.0, precision: 0.1 }),
    ...overrides,
  });
};

/**
 * Factory function to create audio test request
 * Combines test text with agent config
 *
 * @param overrides - Partial request data to override defaults
 * @returns Complete audio test request object
 *
 * @example
 * const request = createAudioTestRequest({
 *   voice_config: createFastSpeechConfig(),
 * });
 */
export const createAudioTestRequest = (overrides: Partial<AudioTestRequest> = {}): AudioTestRequest => {
  return {
    text: 'Hello, this is a test of the AI voice configuration. How does it sound?',
    voice_config: createAgentConfig(),
    ...overrides,
  };
};

/**
 * Default test text for audio tests
 * Matches DEFAULT_TEST_TEXT from apps/api/config/settings.py
 */
export const DEFAULT_TEST_TEXT = 'Hello, this is a test of the AI voice configuration. How does it sound?';

/**
 * Voice Preset type definition matching the API schema
 * Based on VoicePreset SQLModel from apps/api/models/voice_preset.py
 */
export type VoicePreset = {
  id?: number;
  org_id: string;
  name: string;
  use_case: 'sales' | 'support' | 'marketing';
  voice_id: string;
  speech_speed: number;
  stability: number;
  temperature: number;
  description: string;
  is_active: boolean;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
};

/**
 * Factory function to create a voice preset
 * Generates realistic preset data for different use cases
 *
 * @param overrides - Partial preset data to override defaults
 * @returns Complete voice preset object
 *
 * @example
 * // Sales preset with high energy
 * const salesPreset = createVoicePreset({
 *   use_case: 'sales',
 *   speech_speed: 1.2,
 *   stability: 0.6,
 * });
 *
 * // Support preset with calm tone
 * const supportPreset = createVoicePreset({
 *   use_case: 'support',
 *   speech_speed: 0.95,
 *   stability: 0.85,
 * });
 */
export const createVoicePreset = (overrides: Partial<VoicePreset> = {}): VoicePreset => {
  const useCase = overrides.use_case || faker.helpers.arrayElement(['sales', 'support', 'marketing'] as const);

  // Use case-specific presets with optimized settings
  const presetConfigs: Record<typeof useCase, Partial<VoicePreset>> = {
    sales: {
      name: faker.helpers.arrayElement([
        'High Energy',
        'Confident Professional',
        'Friendly Approachable',
        'Direct Efficient',
        'Urgent Closer',
      ]),
      speech_speed: faker.number.float({ min: 1.1, max: 1.3, precision: 0.05 }),
      stability: faker.number.float({ min: 0.55, max: 0.75, precision: 0.05 }),
      temperature: faker.number.float({ min: 0.7, max: 0.9, precision: 0.05 }),
      description: faker.helpers.arrayElement([
        'Enthusiastic, urgent, confident',
        'Professional and self-assured',
        'Warm and easy to talk to',
        'Straight to the point, respectful',
        'High energy sales closer',
      ]),
    },
    support: {
      name: faker.helpers.arrayElement([
        'Calm Reassuring',
        'Empathetic Warm',
        'Efficient Problem Solver',
        'Technical Expert',
      ]),
      speech_speed: faker.number.float({ min: 0.9, max: 1.1, precision: 0.05 }),
      stability: faker.number.float({ min: 0.8, max: 0.95, precision: 0.05 }),
      temperature: faker.number.float({ min: 0.55, max: 0.75, precision: 0.05 }),
      description: faker.helpers.arrayElement([
        'Steady and comforting',
        'Caring and understanding',
        'Quick but patient',
        'Knowledgeable and precise',
      ]),
    },
    marketing: {
      name: faker.helpers.arrayElement([
        'Engaging Storyteller',
        'Enthusiastic Promoter',
        'Trustworthy Guide',
        'Casual Friendly',
      ]),
      speech_speed: faker.number.float({ min: 1.05, max: 1.25, precision: 0.05 }),
      stability: faker.number.float({ min: 0.65, max: 0.85, precision: 0.05 }),
      temperature: faker.number.float({ min: 0.75, max: 0.95, precision: 0.05 }),
      description: faker.helpers.arrayElement([
        'Captivates attention',
        'High energy and exciting',
        'Reliable and informative',
        'Relaxed and approachable',
      ]),
    },
  };

  const config = presetConfigs[useCase];

  return {
    org_id: faker.string.uuid(),
    voice_id: createVoiceId(),
    is_active: true,
    sort_order: faker.number.int({ min: 1, max: 13 }),
    created_at: faker.date.recent({ days: 30 }).toISOString(),
    updated_at: faker.date.recent({ days: 1 }).toISOString(),
    ...config,
    ...overrides,
    use_case,
  };
};

/**
 * Factory function to create multiple voice presets for a use case
 *
 * @param useCase - The use case to create presets for
 * @param count - Number of presets to create
 * @param orgId - Organization ID (defaults to random UUID)
 * @returns Array of voice preset objects
 *
 * @example
 * // Create 5 sales presets
 * const salesPresets = createVoicePresetsForUseCase('sales', 5);
 *
 * // Create 4 support presets for specific org
 * const supportPresets = createVoicePresetsForUseCase('support', 4, 'org-123');
 */
export const createVoicePresetsForUseCase = (
  useCase: 'sales' | 'support' | 'marketing',
  count: number,
  orgId?: string
): VoicePreset[] => {
  const org_id = orgId || faker.string.uuid();

  return Array.from({ length: count }, (_, i) =>
    createVoicePreset({
      org_id,
      use_case,
      sort_order: i + 1,
    })
  );
};

/**
 * Factory function to create all 13 seed presets (matching migration)
 * 5 sales, 4 support, 4 marketing presets
 *
 * @param orgId - Organization ID (defaults to random UUID)
 * @returns Array of all 13 voice presets
 *
 * @example
 * const allPresets = createAllSeedPresets('test-org');
 * // => Array of 13 presets: 5 sales, 4 support, 4 marketing
 */
export const createAllSeedPresets = (orgId?: string): VoicePreset[] => {
  const org_id = orgId || faker.string.uuid();

  return [
    ...createVoicePresetsForUseCase('sales', 5, org_id),
    ...createVoicePresetsForUseCase('support', 4, org_id),
    ...createVoicePresetsForUseCase('marketing', 4, org_id),
  ];
};

/**
 * Helper function to generate multiple configs for bulk tests
 *
 * @param count - Number of configs to generate
 * @param overrides - Partial config data to apply to all configs
 * @returns Array of agent config objects
 *
 * @example
 * const configs = createMultipleAgentConfigs(5);
 * // => Array of 5 unique configs
 *
 * const fastConfigs = createMultipleAgentConfigs(3, {
 *   speech_speed: 1.8,
 * });
 * // => Array of 3 configs with speech_speed 1.8 (different IDs)
 */
export const createMultipleAgentConfigs = (
  count: number,
  overrides: Partial<AgentConfig> = {}
): AgentConfig[] => {
  return Array.from({ length: count }, () => createAgentConfig(overrides));
};
