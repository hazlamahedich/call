/**
 * Voice Telemetry Types
 * Story 2.4: Asynchronous Telemetry Sidecars for Voice Events
 */

/**
 * Voice event types detected during calls
 */
export type VoiceEventType = "silence" | "noise" | "interruption" | "talkover";

/**
 * Providers that can detect voice events
 */
export type TelemetryProvider = "vapi" | "deepgram" | "cartesia";

/**
 * Voice telemetry event record
 * Matches VoiceTelemetry SQLModel in apps/api/models/voice_telemetry.py
 */
export interface VoiceTelemetry {
  id: number;
  orgId: string;
  callId?: number;
  eventType: VoiceEventType;
  timestamp: string;
  durationMs?: number;
  audioLevel?: number;
  confidenceScore?: number;
  sentimentScore?: number;
  provider: TelemetryProvider;
  sessionMetadata?: Record<string, unknown>;
  queueDepthAtCapture?: number;
  processingLatencyMs?: number;
  createdAt: string;
  updatedAt: string;
  softDelete: boolean;
}

/**
 * Telemetry metrics from queue monitoring
 */
export interface TelemetryMetrics {
  currentDepth: number;
  avgDepth: number;
  maxDepth: number;
  isRunning: boolean;
  processingLatencyMsP95: number;
  eventsPerSecond: number;
}

/**
 * Query parameters for telemetry events API
 */
export interface TelemetryEventQueryParams {
  callId?: number;
  eventType?: VoiceEventType;
  startTime?: string;
  endTime?: string;
  limit?: number;
}

/**
 * Response from telemetry events query
 */
export interface TelemetryEventResponse {
  events: VoiceTelemetry[];
  total: number;
  limit: number;
  offset: number;
}
