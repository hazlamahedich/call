export interface TelecomCall {
  id: string;
  orgId: string;
  clientId?: string;
  status: TelecomCallStatus;
  phoneNumber: string;
  duration?: number;
  recordingUrl?: string;
  transcript?: string;
  complianceStatus?: string | null;
  stateCode?: string | null;
  consentCaptured?: boolean;
  gracefulGoodnightTriggered?: boolean;
  createdAt: string;
  endedAt?: string;
}

export type TelecomCallStatus =
  | "pending"
  | "dialing"
  | "ringing"
  | "in_progress"
  | "completed"
  | "failed"
  | "busy"
  | "no_answer"
  | "blocked_dnc"
  | "blocked_hours"
  | "graceful_goodnight"
  | "escalated";

export interface TriggerCallRequest {
  leadId?: number;
  agentId?: number;
  phoneNumber: string;
  campaignId?: number;
}

export interface TriggerCallResponse {
  call: {
    id: number;
    vapiCallId: string;
    orgId: string;
    leadId: number | null;
    agentId: number | null;
    campaignId: number | null;
    status: string;
    phoneNumber: string;
    complianceStatus?: string | null;
    createdAt: string | null;
  };
}
