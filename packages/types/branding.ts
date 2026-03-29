export interface AgencyBranding {
  id: number;
  orgId: string;
  logoUrl: string | null;
  primaryColor: string;
  customDomain: string | null;
  domainVerified: boolean;
  brandName: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DomainVerificationResult {
  verified: boolean;
  message: string;
  instructions?: string;
}
