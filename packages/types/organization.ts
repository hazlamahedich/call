export interface Client {
  id: string;
  name: string;
  createdAt: string;
  updatedAt?: string;
  settings: ClientSettings;
}

export interface ClientSettings {
  branding?: ClientBrandingSettings;
  features?: ClientFeatureSettings;
  [key: string]: unknown;
}

export interface ClientBrandingSettings {
  primaryColor?: string;
  logo?: string;
}

export interface ClientFeatureSettings {
  aiScripts?: boolean;
  crmIntegration?: boolean;
}

export interface ClientWithAgency extends Client {
  agencyId: string;
  agencyName: string;
}
