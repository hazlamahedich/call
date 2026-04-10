import { createEventParser } from "./useWebSocketEvents";
import type { TranscriptEntry } from "@call/types";

export const parseTranscriptEntry = createEventParser<TranscriptEntry>(
  (data: any) => {
    if (data.type === "transcript" && data.entry) {
      return data.entry as TranscriptEntry;
    }
    return null;
  },
);

export const parseVoiceEvent = createEventParser<TranscriptEntry>(
  (data: any, callId?: number) => {
    if (data.type === "speech_state" && data.state) {
      const voiceEntry: TranscriptEntry = {
        id: Date.now(),
        callId: callId || 0,
        role: "lead",
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
  },
);

export interface CitationEvent {
  type: "citation";
  source: string;
  relevance: number;
  chunkId: string;
  documentName: string;
}

export const parseCitationEvent = createEventParser<CitationEvent>(
  (data: any) => {
    if (data.type === "citation" && data.citation) {
      return {
        type: "citation",
        source: data.citation.source,
        relevance: data.citation.relevance,
        chunkId: data.citation.chunk_id,
        documentName: data.citation.document_name,
      } satisfies CitationEvent;
    }
    return null;
  },
);

export interface SentimentEvent {
  type: "sentiment";
  score: number;
  label: string;
  callId: number;
}

export const parseSentimentEvent = createEventParser<SentimentEvent>(
  (data: any) => {
    if (data.type === "sentiment" && data.sentiment) {
      return {
        type: "sentiment",
        score: data.sentiment.score,
        label: data.sentiment.label,
        callId: data.sentiment.call_id,
      } satisfies SentimentEvent;
    }
    return null;
  },
);
