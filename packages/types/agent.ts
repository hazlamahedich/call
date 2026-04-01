import type { TenantScoped } from "./tenant";

export interface Agent extends TenantScoped {
  id: number;
  name: string;
  voiceId: string;
  businessGoal: string;
  safetyLevel: string;
  integrationType?: string;
  onboardingComplete: boolean;
  ttsProvider: "elevenlabs" | "cartesia" | "auto";
  ttsVoiceModel: string;
  fallbackTtsProvider?: string;
}
