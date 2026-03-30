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
