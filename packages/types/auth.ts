import type { Client } from "./organization";

export interface ClerkJWTClaims {
  sub: string;
  org_id?: string;
  org_role?: OrgRole;
  org_slug?: string;
  exp: number;
  iat: number;
}

export type OrgRole = "org:admin" | "org:member";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  type: OrgType;
  plan: PlanType;
  settings: OrganizationSettings;
  clients?: Client[];
  createdAt: string;
  updatedAt?: string;
  deletedAt?: string | null;
}

export type OrgType = "agency" | "platform";
export type PlanType = "free" | "pro" | "enterprise";

export interface OrganizationSettings {
  branding?: BrandingSettings;
  features?: FeatureSettings;
  [key: string]: unknown;
}

export interface BrandingSettings {
  primaryColor?: string;
  logo?: string;
  companyName?: string;
}

export interface FeatureSettings {
  aiScripts?: boolean;
  crmIntegration?: boolean;
  advancedAnalytics?: boolean;
}
