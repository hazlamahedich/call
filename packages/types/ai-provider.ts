export type AIProvider = "openai" | "gemini";

export interface AIProviderConfig {
  provider: AIProvider;
  embeddingModel: string;
  embeddingDimensions: number;
  llmModel: string;
  hasApiKey: boolean;
  connectionStatus: "connected" | "disconnected" | "untested";
}

export interface AIProviderUpdatePayload {
  provider: AIProvider;
  apiKey: string;
  embeddingModel?: string;
  llmModel?: string;
}
