"use server";

import { auth } from "@clerk/nextjs/server";
import type { TriggerCallRequest, TriggerCallResponse } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export async function triggerCall(
  payload: TriggerCallRequest,
): Promise<{ data: TriggerCallResponse | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/calls/trigger`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errMsg = "Failed to trigger call";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { data: null, error: errMsg };
    }

    const data: TriggerCallResponse = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}
