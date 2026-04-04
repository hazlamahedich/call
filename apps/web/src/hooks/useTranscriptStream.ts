/**
 * Transcript Stream Hook (Refactored to use generic WebSocket hook)
 *
 * Domain-specific hook for transcript streaming that composes
 * the generic useWebSocketEvents hook with transcript-specific parsers.
 *
 * Handles:
 * - Transcript entries (text from calls)
 * - Voice state events (speaking, silence, interruption)
 *
 * This is now a thin wrapper around useWebSocketEvents with
 * domain-specific parsing logic.
 */

import { useWebSocketEvents, createEventParser } from "./useWebSocketEvents";
import type { TranscriptEntry } from "@call/types";

interface UseTranscriptStreamResult {
  entries: TranscriptEntry[];
  voiceEvents: TranscriptEntry[];
  isConnected: boolean;
  error: string | null;
}

function buildWsUrl(callId: number): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const wsProtocol = apiUrl.startsWith("https") ? "wss" : "ws";
  const base = apiUrl.replace(/^https?/, wsProtocol);
  return `${base}/ws/calls/${callId}/transcript`;
}

/**
 * Parse transcript entry events
 */
const parseTranscriptEntry = createEventParser<TranscriptEntry>((data: any) => {
  if (data.type === "transcript" && data.entry) {
    return data.entry as TranscriptEntry;
  }
  return null;
});

/**
 * Parse voice state events (speech_start, speech_end, interruption)
 * Creates synthetic TranscriptEntry objects for voice events
 */
const parseVoiceEvent = createEventParser<TranscriptEntry>((data: any, callId?: number) => {
  if (data.type === "speech_state" && data.state) {
    const voiceEntry: TranscriptEntry = {
      id: Date.now(),
      callId: callId || 0,
      role: "lead", // Voice events are always from lead perspective
      text: "",
      startTime: 0,
      endTime: 0,
      confidence: null,
      receivedAt: new Date().toISOString(),
      timestamp: Date.now(),
      event_type: data.state.event_type,
    };
    return voiceEntry;
  }
  return null;
});

export function useTranscriptStream(
  callId: number | null,
): UseTranscriptStreamResult {
  // Use the generic WebSocket hook with transcript-specific parsers
  const { events, isConnected, error } = useWebSocketEvents<TranscriptEntry>({
    callId,
    buildWsUrl,
    eventParsers: [
      (data) => parseTranscriptEntry(data),
      (data) => parseVoiceEvent(data, callId || 0),
    ],
  });

  // Split events into transcript entries and voice events
  const entries: TranscriptEntry[] = [];
  const voiceEvents: TranscriptEntry[] = [];

  for (const event of events) {
    if (event.event_type) {
      voiceEvents.push(event);
    } else {
      entries.push(event);
    }
  }

  return { entries, voiceEvents, isConnected, error };
}

/**
 * Future parsers can be added for Epic 3 and beyond:
 *
 * // RAG Citation Events (Story 3.5)
 * const parseCitationEvent = createEventParser((data) => {
 *   if (data.type === "citation" && data.citation) {
 *     return {
 *       type: "citation",
 *       source: data.citation.source,
 *       relevance: data.citation.relevance,
 *       // ... other citation fields
 *     };
 *   }
 *   return null;
 * });
 *
 * // Sentiment Analysis Events (Epic 5)
 * const parseSentimentEvent = createEventParser((data) => {
 *   if (data.type === "sentiment" && data.sentiment) {
 *     return {
 *       type: "sentiment",
 *       score: data.sentiment.score,
 *       label: data.sentiment.label,
 *       // ... other sentiment fields
 *     };
 *   }
 *   return null;
 * });
 */
