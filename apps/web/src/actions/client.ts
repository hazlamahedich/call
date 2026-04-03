"use server";

import { auth } from "@clerk/nextjs/server";
import { Client, ClientSettings } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export async function createClient(data: {
  orgId: string;
  name: string;
  settings?: ClientSettings;
}): Promise<{ client: Client | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { client: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/organizations/${data.orgId}/clients`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: data.name,
          settings: data.settings,
        }),
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to create client";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { client: null, error: errMsg };
    }

    const client = await response.json();
    return { client, error: null };
  } catch (e) {
    return { client: null, error: (e as Error).message };
  }
}

export async function updateClient(data: {
  orgId: string;
  clientId: string;
  updates: Partial<Client>;
}): Promise<{ client: Client | null; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { client: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/organizations/${data.orgId}/clients/${data.clientId}`,
      {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data.updates),
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to update client";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { client: null, error: errMsg };
    }

    const client = await response.json();
    return { client, error: null };
  } catch (e) {
    return { client: null, error: (e as Error).message };
  }
}

export async function deleteClient(data: {
  orgId: string;
  clientId: string;
}): Promise<{ success: boolean; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { success: false, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/organizations/${data.orgId}/clients/${data.clientId}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      },
    );

    if (!response.ok) {
      let errMsg = "Failed to delete client";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { success: false, error: errMsg };
    }

    return { success: true, error: null };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

export async function getClients(
  orgId: string,
): Promise<{ clients: Client[]; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { clients: [], error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/organizations/${orgId}/clients`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    if (!response.ok) {
      let errMsg = "Failed to fetch clients";
      try {
        const err = await response.json();
        errMsg = err.detail?.message || err.message || errMsg;
      } catch {
        // non-JSON response
      }
      return { clients: [], error: errMsg };
    }

    const clients = await response.json();
    return { clients, error: null };
  } catch (e) {
    return { clients: [], error: (e as Error).message };
  }
}
