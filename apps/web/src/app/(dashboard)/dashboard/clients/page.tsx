"use client";

import { useState, useEffect, useCallback } from "react";
import { useOrganization, useUser } from "@clerk/nextjs";
import { getClients, createClient, deleteClient } from "@/actions/client";
import { Client, OrgRole } from "@call/types";
import { canCreateClient, canDeleteClient } from "@/lib/permissions";
import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status-message";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ConfirmAction } from "@/components/ui/confirm-action";

export default function ClientsPage() {
  const { organization } = useOrganization();
  const { user } = useUser();
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [newClientName, setNewClientName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const userRole = user?.publicMetadata?.org_role as OrgRole | undefined;
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

    const result = await deleteClient({ orgId: organization.id, clientId });
    if (result.error) {
      setError(result.error);
    } else {
      setClients((prev) => prev.filter((c) => c.id !== clientId));
    }
    setDeleteTarget(null);
  };

  if (!organization) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <p className="text-muted-foreground">
          Please select an organization to manage clients.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Clients</h1>
        {canAddClient && (
          <Button onClick={() => setShowForm(true)}>Add Client</Button>
        )}
      </div>

      {error && <StatusMessage variant="error">{error}</StatusMessage>}

      {showForm && (
        <Card className="p-4">
          <form onSubmit={handleCreateClient} className="flex gap-3">
            <Input
              type="text"
              value={newClientName}
              onChange={(e) => setNewClientName(e.target.value)}
              placeholder="Client name"
              className="flex-1"
              required
            />
            <Button type="submit">Create</Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </form>
        </Card>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <p className="text-muted-foreground">Loading clients...</p>
        </div>
      ) : clients.length === 0 ? (
        <EmptyState
          title="No clients yet"
          description={
            canAddClient ? "Add your first client to get started." : undefined
          }
          action={
            canAddClient ? (
              <Button onClick={() => setShowForm(true)}>Add Client</Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {clients.map((client) => (
            <Card
              key={client.id}
              className="flex items-center justify-between p-4"
            >
              <div>
                <h3 className="font-medium text-foreground">{client.name}</h3>
                <p className="text-sm text-muted-foreground">
                  Created {new Date(client.createdAt).toLocaleDateString()}
                </p>
              </div>
              {canRemoveClient && (
                <ConfirmAction
                  title="Delete Client"
                  description="Are you sure you want to delete this client? This action cannot be undone."
                  confirmLabel="Delete"
                  onConfirm={() => handleDeleteClient(client.id)}
                  open={deleteTarget === client.id}
                  onOpenChange={(open) =>
                    setDeleteTarget(open ? client.id : null)
                  }
                >
                  <Button variant="destructive" size="sm">
                    Delete
                  </Button>
                </ConfirmAction>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
