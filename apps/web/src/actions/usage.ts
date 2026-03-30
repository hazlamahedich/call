"use server";

import { auth } from "@clerk/nextjs/server";
import type { UsageSummary, UsageThreshold } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UsageCheckResult {
  threshold: UsageThreshold;
  used: number;
  cap: number;
}

export async function getUsageSummary(): Promise<{
  data: UsageSummary | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/usage/summary`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      let errMsg = "Failed to fetch usage summary";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch (parseErr) {
        console.error("[usage] Non-JSON error response:", parseErr);
      }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    console.error("[usage] getUsageSummary failed:", e);
    return { data: null, error: (e as Error).message };
  }
}

export async function recordUsage(payload: {
  resourceType: string;
  resourceId: string;
  action: string;
  metadata?: string;
}): Promise<{ data: Record<string, unknown> | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/usage/record`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errMsg = "Failed to record usage";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch (parseErr) {
        console.error("[usage] Non-JSON error response:", parseErr);
      }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    console.error("[usage] recordUsage failed:", e);
    return { data: null, error: (e as Error).message };
  }
}

export async function checkUsageCap(): Promise<{
  data: UsageCheckResult | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/usage/check`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      let errMsg = "Failed to check usage cap";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch (parseErr) {
        console.error("[usage] Non-JSON error response:", parseErr);
      }
      return { data: null, error: errMsg };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    console.error("[usage] checkUsageCap failed:", e);
    return { data: null, error: (e as Error).message };
  }
}
