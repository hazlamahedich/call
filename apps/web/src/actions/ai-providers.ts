"use server";

import { auth } from "@clerk/nextjs/server";
import type { AIProviderConfig, AIProviderUpdatePayload } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export async function getAIProviderConfig(
  orgId: string,
): Promise<{ data: AIProviderConfig | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/v1/settings/ai-provider`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      let errMsg = "Failed to fetch AI provider config";
      try {
        const err = await response.json();
        errMsg = err.detail || errMsg;
      } catch {
        // non-JSON response
      }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function updateAIProviderConfig(
  orgId: string,
  payload: AIProviderUpdatePayload,
): Promise<{ data: AIProviderConfig | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/v1/settings/ai-provider`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errMsg = "Failed to update AI provider config";
      try {
        const err = await response.json();
        errMsg = err.detail || errMsg;
      } catch {
        // non-JSON response
      }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function testAIProviderConnection(
  orgId: string,
): Promise<{
  data: { success: boolean; message: string } | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/settings/ai-provider/test`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to test connection";
      try {
        const err = await response.json();
        errMsg = err.detail || errMsg;
      } catch {
        // non-JSON response
      }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function getAvailableModels(
  orgId: string,
): Promise<{
  data: Record<string, { embedding: string[]; llm: string[] }> | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/settings/ai-provider/models`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );

    if (!response.ok) {
      return { data: null, error: "Failed to fetch models" };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}
