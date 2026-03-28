export interface TenantScoped {
  orgId: string;
  createdAt: string;
  updatedAt: string;
  softDelete: boolean;
}

export interface WithOrgId {
  orgId: string;
}

export function assertTenantScoped<T extends TenantScoped>(
  record: T,
  expectedOrgId: string,
): void {
  if (record.orgId !== expectedOrgId) {
    throw new Error(
      `Tenant isolation violation: record.orgId (${record.orgId}) !== expectedOrgId (${expectedOrgId})`,
    );
  }
  return true;
}

export interface Lead extends TenantScoped {
  id: number;
  name: string;
  email: string;
  phone?: string;
  status: string;
}

export interface Agency extends TenantScoped {
  id: number;
  name: string;
  clerkOrgId: string;
  plan: "free" | "pro" | "enterprise";
}

export interface Client extends TenantScoped {
  id: number;
  name: string;
  agencyId: string;
}

export interface Campaign extends TenantScoped {
  id: number;
  name: string;
  status: "draft" | "active" | "paused" | "completed";
}

export interface Call extends TenantScoped {
  id: number;
  leadId: number;
  campaignId: number;
  status: "pending" | "in_progress" | "completed" | "failed";
  duration?: number;
}

export interface Script extends TenantScoped {
  id: number;
  name: string;
  content: string;
  version: number;
}

export interface KnowledgeBase extends TenantScoped {
  id: number;
  name: string;
  content: string;
  embedding?: number[];
}

export interface UsageLog extends TenantScoped {
  id: number;
  resourceType: string;
  resourceId: string;
  action: string;
}
