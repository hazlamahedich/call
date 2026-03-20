"use server";

import { Client, ClientSettings } from "@call/types";

export async function createClient(data: {
  orgId: string;
  name: string;
  settings?: ClientSettings;
}): Promise<{ client: Client | null; error: string | null }> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/organizations/${data.orgId}/clients`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: data.name,
          settings: data.settings,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { client: null, error: error.message || "Failed to create client" };
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
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/organizations/${data.orgId}/clients/${data.clientId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data.updates),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { client: null, error: error.message || "Failed to update client" };
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
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/organizations/${data.orgId}/clients/${data.clientId}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.message || "Failed to delete client" };
    }

    return { success: true, error: null };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

export async function getClients(orgId: string): Promise<{ clients: Client[]; error: string | null }> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/organizations/${orgId}/clients`
    );

    if (!response.ok) {
      const error = await response.json();
      return { clients: [], error: error.message || "Failed to fetch clients" };
    }

    const clients = await response.json();
    return { clients, error: null };
  } catch (e) {
    return { clients: [], error: (e as Error).message };
  }
}
