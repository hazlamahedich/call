export interface OnboardingPayload {
  businessGoal: string;
  scriptContext: string;
  voiceId: string;
  integrationType: string;
  safetyLevel: string;
}

export interface OnboardingStatus {
  completed: boolean;
}
