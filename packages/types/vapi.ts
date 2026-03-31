export interface VapiCallEvent {
  message: {
    type: string;
    call?: {
      id: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}

export interface VapiCallStartedPayload {
  message: {
    type: "call-start";
    call: {
      id: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}

export interface VapiCallEndedPayload {
  message: {
    type: "call-end";
    call: {
      id: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}

export interface VapiCallFailedPayload {
  message: {
    type: "call-failed";
    call: {
      id: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}

export interface VapiTranscriptWord {
  word: string;
  start: number;
  end: number;
  confidence: number;
}

export interface VapiTranscriptEvent {
  message: {
    type: "transcript";
    call: {
      id: string;
      [key: string]: unknown;
    };
    transcript: {
      role: "assistant" | "user";
      text: string;
      words?: VapiTranscriptWord[];
    };
    [key: string]: unknown;
  };
}

export interface VapiSpeechEvent {
  message: {
    type: "speech-start" | "speech-end";
    call: {
      id: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}
