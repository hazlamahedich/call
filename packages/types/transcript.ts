export interface TranscriptEntry {
  id: string;
  role: "assistant-ai" | "assistant-human" | "lead";
  text: string;
  timestamp: number;
  sentiment?: "positive" | "neutral" | "hostile";
}
