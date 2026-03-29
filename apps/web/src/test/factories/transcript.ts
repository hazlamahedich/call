import type { TranscriptEntry } from "@call/types";

let counter = 0;

export function createTranscriptEntry(
  overrides: Partial<TranscriptEntry> = {},
): TranscriptEntry {
  counter++;
  return {
    id: `entry-${counter}`,
    role: "assistant-ai",
    text: `Test transcript entry ${counter}`,
    timestamp: new Date("2026-03-29T10:00:00").getTime() + counter * 60000,
    sentiment: "neutral",
    ...overrides,
  };
}
