"use server";

import { apiClient } from "@/lib/api-client";
import type { Client, ClientSettings } from "@call/types";

export async function createClient(data: {
  orgId: string;
  name: string;
  settings?: ClientSettings;
}): Promise<{ client: Client | null; error: string | null }> {
  const { data: client, error } = await apiClient.post<Client>(
    `/api/organizations/${data.orgId}/clients`,
    { name: data.name, settings: data.settings },
    { fallbackError: "Failed to create client" },
  );
  return { client, error };
}

export async function updateClient(data: {
  orgId: string;
  clientId: string;
  updates: Partial<Client>;
}): Promise<{ client: Client | null; error: string | null }> {
  const { data: client, error } = await apiClient.patch<Client>(
    `/api/organizations/${data.orgId}/clients/${data.clientId}`,
    data.updates,
    { fallbackError: "Failed to update client" },
  );
  return { client, error };
}

export async function deleteClient(data: {
  orgId: string;
  clientId: string;
}): Promise<{ success: boolean; error: string | null }> {
  const { error } = await apiClient.delete(
    `/api/organizations/${data.orgId}/clients/${data.clientId}`,
    { fallbackError: "Failed to delete client" },
  );
  return { success: !error, error };
}

export async function getClients(
  orgId: string,
): Promise<{ clients: Client[]; error: string | null }> {
  const { data, error } = await apiClient.get<Client[]>(
    `/api/organizations/${orgId}/clients`,
    { fallbackError: "Failed to fetch clients" },
  );
  return { clients: data || [], error };
}
