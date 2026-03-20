import { OrgRole } from "@call/types";

export function isAdmin(role: OrgRole | undefined): boolean {
  return role === "org:admin";
}

export function isMember(role: OrgRole | undefined): boolean {
  return role === "org:member";
}

export function canManageOrganization(role: OrgRole | undefined): boolean {
  return isAdmin(role);
}

export function canManageMembers(role: OrgRole | undefined): boolean {
  return isAdmin(role);
}

export function canViewAllClients(role: OrgRole | undefined): boolean {
  return isAdmin(role);
}

export function canManageClient(role: OrgRole | undefined, assignedClientId?: string): boolean {
  if (isAdmin(role)) return true;
  if (isMember(role) && assignedClientId) return true;
  return false;
}

export function canCreateClient(role: OrgRole | undefined): boolean {
  return isAdmin(role);
}

export function canDeleteClient(role: OrgRole | undefined): boolean {
  return isAdmin(role);
}
