import { useWebSocketEvents } from "./useWebSocketEvents";
import { parseTranscriptEntry, parseVoiceEvent } from "./event-parsers";
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

export function useTranscriptStream(
  callId: number | null,
): UseTranscriptStreamResult {
  const { events, isConnected, error } = useWebSocketEvents<TranscriptEntry>({
    callId,
    buildWsUrl,
    eventParsers: [
      (data) => parseTranscriptEntry(data),
      (data) => parseVoiceEvent(data, callId || 0),
    ],
  });

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
