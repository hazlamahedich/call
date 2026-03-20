export interface Call {
  id: string;
  orgId: string;
  clientId?: string;
  status: CallStatus;
  phoneNumber: string;
  duration?: number;
  recordingUrl?: string;
  transcript?: string;
  createdAt: string;
  endedAt?: string;
}

export type CallStatus =
  | "pending"
  | "dialing"
  | "ringing"
  | "in_progress"
  | "completed"
  | "failed"
  | "busy"
  | "no_answer";
