"use server";

import { Organization, OrgType, PlanType, OrganizationSettings } from "@call/types";

export async function createOrganization(data: {
  name: string;
  slug: string;
  type: OrgType;
  plan?: PlanType;
  settings?: OrganizationSettings;
}): Promise<{ organization: Organization | null; error: string | null }> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/organizations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      return { organization: null, error: error.message || "Failed to create organization" };
    }

    const organization = await response.json();
    return { organization, error: null };
  } catch (e) {
    return { organization: null, error: (e as Error).message };
  }
}

export async function updateOrganization(
  orgId: string,
  data: Partial<Organization>
): Promise<{ organization: Organization | null; error: string | null }> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/organizations/${orgId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { organization: null, error: error.message || "Failed to update organization" };
    }

    const organization = await response.json();
    return { organization, error: null };
  } catch (e) {
    return { organization: null, error: (e as Error).message };
  }
}

export async function getOrganization(
  orgId: string
): Promise<{ organization: Organization | null; error: string | null }> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/organizations/${orgId}`
    );

    if (!response.ok) {
      const error = await response.json();
      return { organization: null, error: error.message || "Failed to fetch organization" };
    }

    const organization = await response.json();
    return { organization, error: null };
  } catch (e) {
    return { organization: null, error: (e as Error).message };
  }
}
