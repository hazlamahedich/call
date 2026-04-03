export type VoiceEventType = "speech-start" | "speech-end" | "interruption";

export interface TranscriptEntry {
  id: number;
  callId: number;
  role: "assistant-ai" | "assistant-human" | "lead";
  text: string;
  startTime: number;
  endTime: number;
  confidence: number | null;
  receivedAt: string;
  timestamp: number;
  sentiment?: "positive" | "neutral" | "hostile";
  event_type?: VoiceEventType;
}
