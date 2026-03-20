"use client";

import { useState, useEffect, useCallback } from "react";
import { useOrganization, useUser } from "@clerk/nextjs";
import { getClients, createClient, deleteClient } from "@/actions/client";
import { Client } from "@call/types";
import { canCreateClient, canDeleteClient } from "@/lib/permissions";

export default function ClientsPage() {
  const { organization } = useOrganization();
  const { user } = useUser();
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [newClientName, setNewClientName] = useState("");

  const userRole = user?.publicMetadata?.org_role as string | undefined;
  const canAddClient = canCreateClient(userRole);
  const canRemoveClient = canDeleteClient(userRole);

  const loadClients = useCallback(async () => {
    if (!organization?.id) return;
    setIsLoading(true);
    setError(null);
    const result = await getClients(organization.id);
    if (result.error) {
      setError(result.error);
    } else {
      setClients(result.clients);
    }
    setIsLoading(false);
  }, [organization?.id]);

  useEffect(() => {
    if (organization?.id) {
      loadClients();
    }
  }, [organization?.id, loadClients]);

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!organization?.id || !newClientName.trim()) return;

    setError(null);
    const result = await createClient({
      orgId: organization.id,
      name: newClientName.trim(),
    });

    if (result.error) {
      setError(result.error);
    } else {
      setClients((prev) => [...prev, result.client!]);
      setNewClientName("");
      setShowForm(false);
    }
  };

  const handleDeleteClient = async (clientId: string) => {
    if (!organization?.id) return;
    if (!confirm("Are you sure you want to delete this client?")) return;

    const result = await deleteClient({ orgId: organization.id, clientId });
    if (result.error) {
      setError(result.error);
    } else {
      setClients((prev) => prev.filter((c) => c.id !== clientId));
    }
  };

  if (!organization) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <p className="text-zinc-400">
          Please select an organization to manage clients.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Clients</h1>
        {canAddClient && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded bg-[#10B981] px-4 py-2 text-sm font-medium text-white hover:bg-[#10B981]/90"
          >
            Add Client
          </button>
        )}
      </div>

      {error && (
        <div className="rounded bg-red-900/20 p-3 text-red-400">{error}</div>
      )}

      {showForm && (
        <form
          onSubmit={handleCreateClient}
          className="rounded border border-[#27272A] bg-[#18181B] p-4"
        >
          <div className="flex gap-3">
            <input
              type="text"
              value={newClientName}
              onChange={(e) => setNewClientName(e.target.value)}
              placeholder="Client name"
              className="flex-1 rounded border border-[#27272A] bg-[#09090B] px-3 py-2 text-white"
              required
            />
            <button
              type="submit"
              className="rounded bg-[#10B981] px-4 py-2 text-sm font-medium text-white"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded border border-[#27272A] px-4 py-2 text-sm text-zinc-400 hover:bg-[#27272A]"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <p className="text-zinc-400">Loading clients...</p>
        </div>
      ) : clients.length === 0 ? (
        <div className="rounded border border-dashed border-[#27272A] p-8 text-center">
          <p className="text-zinc-400">
            {canAddClient
              ? "No clients yet. Add your first client!"
              : "No clients yet."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {clients.map((client) => (
            <div
              key={client.id}
              className="flex items-center justify-between rounded border border-[#27272A] bg-[#18181B] p-4"
            >
              <div>
                <h3 className="font-medium text-white">{client.name}</h3>
                <p className="text-sm text-zinc-400">
                  Created {new Date(client.createdAt).toLocaleDateString()}
                </p>
              </div>
              {canRemoveClient && (
                <button
                  onClick={() => handleDeleteClient(client.id)}
                  className="rounded px-3 py-1 text-sm text-red-400 hover:bg-red-900/20"
                >
                  Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
