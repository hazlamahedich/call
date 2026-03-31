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
