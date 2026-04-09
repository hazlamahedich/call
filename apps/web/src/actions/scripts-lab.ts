"use server";

import { auth } from "@clerk/nextjs/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface LabSession {
  sessionId: number;
  agentId: number;
  scriptId: number;
  leadId: number | null;
  status: string;
  expiresAt: string;
  scenarioOverlay: Record<string, string> | null;
}

export interface SourceAttribution {
  chunkId: number;
  documentName: string;
  pageNumber: number | null;
  excerpt: string;
  similarityScore: number;
}

export interface ClaimVerification {
  claimText: string;
  isSupported: boolean;
  maxSimilarity: number;
  verificationError: boolean;
}

export interface LabChatResponse {
  responseText: string;
  sourceAttributions: SourceAttribution[];
  groundingConfidence: number;
  turnNumber: number;
  lowConfidenceWarning: boolean;
  wasCorrected: boolean;
  correctionCount: number;
  verificationTimedOut: boolean;
  verifiedClaims: ClaimVerification[];
}

export interface LabSourceEntry {
  turnNumber: number;
  userMessage: string;
  aiResponse: string;
  sources: SourceAttribution[];
  groundingConfidence: number;
}

export async function createLabSession(
  agentId: number,
  scriptId: number,
  leadId?: number,
): Promise<{ data: LabSession | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const body: Record<string, unknown> = { agentId, scriptId };
    if (leadId !== undefined) body.leadId = leadId;

    const response = await fetch(`${API_URL}/api/v1/script-lab/sessions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let errMsg = "Failed to create lab session";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.error?.message || errMsg;
      } catch {}
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function sendLabChat(
  sessionId: number,
  message: string,
): Promise<{ data: LabChatResponse | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/script-lab/sessions/${sessionId}/chat`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to send message";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.error?.message || errMsg;
      } catch {}
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function setScenarioOverlay(
  sessionId: number,
  overlay: Record<string, string>,
): Promise<{ data: LabSession | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/script-lab/sessions/${sessionId}/scenario-overlay`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ overlay }),
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to set scenario overlay";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.error?.message || errMsg;
      } catch {}
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function getLabSources(sessionId: number): Promise<{
  data: {
    sessionId: number;
    totalTurns: number;
    sources: LabSourceEntry[];
  } | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/script-lab/sessions/${sessionId}/sources`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to get sources";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.error?.message || errMsg;
      } catch {}
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function deleteLabSession(
  sessionId: number,
): Promise<{ error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/script-lab/sessions/${sessionId}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to delete session";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.error?.message || errMsg;
      } catch {}
      return { error: errMsg };
    }

    return { error: null };
  } catch (e) {
    return { error: (e as Error).message };
  }
}
