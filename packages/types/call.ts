export interface TelecomCall {
  id: string;
  orgId: string;
  clientId?: string;
  status: TelecomCallStatus;
  phoneNumber: string;
  duration?: number;
  recordingUrl?: string;
  transcript?: string;
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
  | "no_answer";

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
    createdAt: string | null;
  };
}
