"use server";

import { auth } from "@clerk/nextjs/server";
import {
  Organization,
  OrgType,
  PlanType,
  OrganizationSettings,
} from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export async function createOrganization(data: {
  name: string;
  slug: string;
  type: OrgType;
  plan?: PlanType;
  settings?: OrganizationSettings;
}): Promise<{ organization: Organization | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { organization: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/organizations`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      let errMsg = "Failed to create organization";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { organization: null, error: errMsg };
    }

    const organization = await response.json();
    return { organization, error: null };
  } catch (e) {
    return { organization: null, error: (e as Error).message };
  }
}

export async function updateOrganization(
  orgId: string,
  data: Partial<Organization>,
): Promise<{ organization: Organization | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { organization: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/organizations/${orgId}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      let errMsg = "Failed to update organization";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { organization: null, error: errMsg };
    }

    const organization = await response.json();
    return { organization, error: null };
  } catch (e) {
    return { organization: null, error: (e as Error).message };
  }
}

export async function getOrganization(
  orgId: string,
): Promise<{ organization: Organization | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { organization: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/organizations/${orgId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      let errMsg = "Failed to fetch organization";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { organization: null, error: errMsg };
    }

    const organization = await response.json();
    return { organization, error: null };
  } catch (e) {
    return { organization: null, error: (e as Error).message };
  }
}
