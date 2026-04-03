import { faker } from '@faker-js/faker';

/**
 * Telemetry Event type definition matching the API schema
 */
export type TelemetryEvent = {
  id?: number;
  call_id: number | string;
  org_id: number | string;
  event_type: 'silence' | 'noise' | 'speech' | 'interruption';
  timestamp: string;
  duration_ms?: number;
  audio_level?: number;
  received_at?: string;
  vapi_event_timestamp?: string;
};

/**
 * Telemetry Metrics type definition
 */
export type TelemetryMetrics = {
  current_depth: number;
  avg_depth: number;
  max_depth: number;
  is_running: boolean;
  processing_latency_ms_p95: number;
  events_per_second: number;
  drop_rate?: number;
  degradation_alert?: {
    level: 'warning' | 'critical';
    message: string;
    threshold: number;
    current_value: number;
    duration_seconds?: number;
  };
  consecutive_high_drop_periods?: number;
  time_since_last_drop_seconds?: number;
};

/**
 * Factory function to create unique call_id
 * Uses faker to generate unique integers for API compatibility
 *
 * @returns Unique call ID as number
 */
export const createCallId = (): number => faker.number.int({ min: 100000, max: 999999 });

/**
 * Factory function to create unique org_id
 * Uses faker to generate unique integers for API compatibility
 *
 * @returns Unique org ID as number
 */
export const createOrgId = (): number => faker.number.int({ min: 10000, max: 99999 });

/**
 * Factory function to create unique vapi_call_id (string UUID)
 * More realistic than numeric call_id
 *
 * @returns Unique vapi call ID as string
 */
export const createVapiCallId = (): string => faker.string.uuid();

/**
 * Factory function to create telemetry event test data
 * Generates unique values to prevent parallel test collisions
 *
 * @param overrides - Partial event data to override defaults
 * @returns Complete telemetry event object with unique IDs
 *
 * @example
 * // Default event with unique IDs
 * const event = createTelemetryEvent();
 *
 * // Silence event for specific call
 * const silenceEvent = createTelemetryEvent({
 *   event_type: 'silence',
 *   audio_level: -60,
 * });
 *
 * // Event with custom org
 * const customEvent = createTelemetryEvent({
 *   org_id: 12345,
 *   call_id: 67890,
 * });
 */
export const createTelemetryEvent = (overrides: Partial<TelemetryEvent> = {}): TelemetryEvent => ({
  call_id: createCallId(),
  org_id: createOrgId(),
  event_type: 'silence',
  timestamp: faker.date.recent({ days: 1 }).toISOString(),
  duration_ms: faker.number.int({ min: 100, max: 5000 }),
  audio_level: faker.number.int({ min: -60, max: 0 }),
  received_at: faker.date.recent({ days: 1 }).toISOString(),
  vapi_event_timestamp: faker.date.recent({ days: 1 }).toISOString(),
  ...overrides,
});

/**
 * Factory function to create silence events (low audio level)
 *
 * @param overrides - Partial event data to override defaults
 * @returns Silence event with audio_level typically <= -40
 */
export const createSilenceEvent = (overrides: Partial<TelemetryEvent> = {}): TelemetryEvent =>
  createTelemetryEvent({
    event_type: 'silence',
    audio_level: faker.number.int({ min: -60, max: -40 }),
    ...overrides,
  });

/**
 * Factory function to create noise events (high audio level)
 *
 * @param overrides - Partial event data to override defaults
 * @returns Noise event with audio_level typically >= -20
 */
export const createNoiseEvent = (overrides: Partial<TelemetryEvent> = {}): TelemetryEvent =>
  createTelemetryEvent({
    event_type: 'noise',
    audio_level: faker.number.int({ min: -30, max: -10 }),
    ...overrides,
  });

/**
 * Factory function to create telemetry metrics test data
 * Generates realistic metrics with optional degradation alerts
 *
 * @param overrides - Partial metrics data to override defaults
 * @returns Complete telemetry metrics object
 *
 * @example
 * // Healthy metrics (no degradation)
 * const healthyMetrics = createTelemetryMetrics();
 *
 * // Metrics with high drop rate triggering critical alert
 * const degradedMetrics = createTelemetryMetrics({
 *   drop_rate: 0.15,
 *   degradation_alert: {
 *     level: 'critical',
 *     message: 'Drop rate exceeds 10%',
 *     threshold: 0.1,
 *     current_value: 0.15,
 *   },
 * });
 */
export const createTelemetryMetrics = (overrides: Partial<TelemetryMetrics> = {}): TelemetryMetrics => ({
  current_depth: faker.number.int({ min: 0, max: 10000 }),
  avg_depth: faker.number.int({ min: 0, max: 8000 }),
  max_depth: faker.number.int({ min: 5000, max: 10000 }),
  is_running: faker.datatype.boolean(),
  processing_latency_ms_p95: faker.number.int({ min: 20, max: 200 }),
  events_per_second: faker.number.int({ min: 100, max: 1000 }),
  drop_rate: 0,
  ...overrides,
});

/**
 * Factory function to create healthy metrics (no degradation)
 * Drop rate < 10%, no alerts
 */
export const createHealthyMetrics = (): TelemetryMetrics =>
  createTelemetryMetrics({
    drop_rate: faker.number.float({ min: 0, max: 0.05, precision: 0.001 }),
    is_running: true,
  });

/**
 * Factory function to create degraded metrics (critical alert)
 * Drop rate > 10%, includes degradation_alert
 */
export const createDegradedMetrics = (): TelemetryMetrics =>
  createTelemetryMetrics({
    drop_rate: faker.number.float({ min: 0.10, max: 0.25, precision: 0.001 }),
    degradation_alert: {
      level: 'critical',
      message: 'Drop rate exceeds 10% threshold',
      threshold: 0.1,
      current_value: faker.number.float({ min: 0.10, max: 0.25, precision: 0.001 }),
      duration_seconds: faker.number.int({ min: 30, max: 120 }),
    },
    consecutive_high_drop_periods: faker.number.int({ min: 1, max: 5 }),
  });

/**
 * Factory function to create warning-level metrics
 * Drop rate approaching threshold, includes warning alert
 */
export const createWarningMetrics = (): TelemetryMetrics =>
  createTelemetryMetrics({
    drop_rate: faker.number.float({ min: 0.05, max: 0.09, precision: 0.001 }),
    degradation_alert: {
      level: 'warning',
      message: 'Drop rate elevated',
      threshold: 0.1,
      current_value: faker.number.float({ min: 0.05, max: 0.09, precision: 0.001 }),
    },
  });
