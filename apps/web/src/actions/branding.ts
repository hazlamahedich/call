"use server";

import { auth } from "@clerk/nextjs/server";
import type { AgencyBranding, DomainVerificationResult } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getBranding(
  orgId: string,
): Promise<{ data: AgencyBranding | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/branding`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 404) return { data: null, error: null };
    if (!response.ok) {
      let errMsg = "Failed to fetch branding";
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

export async function updateBranding(
  orgId: string,
  data: Partial<
    Pick<
      AgencyBranding,
      "logoUrl" | "primaryColor" | "customDomain" | "brandName"
    >
  >,
): Promise<{ data: AgencyBranding | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/branding`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      let errMsg = "Failed to update branding";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { data: null, error: errMsg };
    }

    const result = await response.json();
    return { data: result, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

export async function verifyDomain(
  orgId: string,
  domain: string,
): Promise<{ data: DomainVerificationResult | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/branding/verify-domain`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ domain }),
    });

    if (!response.ok) {
      let errMsg = "Failed to verify domain";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { data: null, error: errMsg };
    }

    const result = await response.json();
    return { data: result, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}
