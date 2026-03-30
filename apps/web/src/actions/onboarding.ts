"use server";

import { auth } from "@clerk/nextjs/server";
import type { Agent, OnboardingPayload, OnboardingStatus } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function completeOnboarding(
  wizardData: OnboardingPayload,
): Promise<{ agent: Agent | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { agent: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/onboarding/complete`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(wizardData),
    });

    if (!response.ok) {
      let errMsg = "Failed to complete onboarding";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { agent: null, error: errMsg };
    }

    const data = await response.json();
    return { agent: data.agent, error: null };
  } catch (e) {
    return { agent: null, error: (e as Error).message };
  }
}

export async function getOnboardingStatus(): Promise<{
  data: OnboardingStatus | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/onboarding/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      let errMsg = "Failed to fetch onboarding status";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
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
