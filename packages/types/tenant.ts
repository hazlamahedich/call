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
): asserts record is T & { orgId: string } {
  if (record.orgId !== expectedOrgId) {
    throw new Error(
      `Tenant isolation violation: record.orgId (${record.orgId}) !== expectedOrgId (${expectedOrgId})`,
    );
  }
}

export interface Lead extends TenantScoped {
  id: number;
  name: string;
  email: string;
  phone?: string;
  status: string;
}

export interface DbAgency extends TenantScoped {
  id: number;
  name: string;
  clerkOrgId: string;
  plan: "free" | "pro" | "enterprise";
}

export interface DbClient extends TenantScoped {
  id: number;
  name: string;
  agencyId: string;
}

export interface DbCampaign extends TenantScoped {
  id: number;
  name: string;
  status: "draft" | "active" | "paused" | "completed";
}

export interface DbCall extends TenantScoped {
  id: number;
  leadId: number;
  campaignId: number;
  status: "pending" | "in_progress" | "completed" | "failed";
  duration?: number;
}

export interface DbScript extends TenantScoped {
  id: number;
  name: string;
  content: string;
  version: number;
  agentId?: number;
  scriptContext?: string;
}

export interface DbKnowledgeBase extends TenantScoped {
  id: number;
  name: string;
  content: string;
  embedding?: number[];
}

export interface DbUsageLog extends TenantScoped {
  id: number;
  resourceType: string;
  resourceId: string;
  action: string;
  metadataJson?: string;
}
