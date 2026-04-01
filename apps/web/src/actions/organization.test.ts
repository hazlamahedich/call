/**
 * Story 1-2: Multi-layer Hierarchy & Clerk Auth Integration
 * Unit Tests for Organization Server Actions
 *
 * Test ID Format: 1.2-UNIT-ORG-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { OrgType, PlanType } from "@call/types";

const mockGetToken = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({ getToken: mockGetToken }),
}));

const mockFetch = vi.fn();

const ORG_IDS = {
  validOrgId: "org_2QWXJC123456",
  testOrgId: "org_test123456",
};

describe("[P0] Organization Server Actions - AC1", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch);
    mockFetch.mockReset();
    mockGetToken.mockResolvedValue("test-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("createOrganization", () => {
    it("[1.2-UNIT-ORG-001][P0] should create organization with metadata", async () => {
      const orgData = {
        name: "Test Agency",
        slug: "test-agency",
        type: "agency" as OrgType,
        plan: "pro" as PlanType,
        settings: { features: { advancedAnalytics: true } },
      };
      const mockOrg = { id: ORG_IDS.validOrgId, ...orgData };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrg,
      });

      const { createOrganization } = await import("./organization");
      const result = await createOrganization(orgData);

      expect(result.organization).toEqual(mockOrg);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/organizations"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
    });

    it("[1.2-UNIT-ORG-002][P1] should return error when creation fails", async () => {
      const orgData = {
        name: "Test Agency",
        slug: "test-agency",
        type: "agency" as OrgType,
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: "Organization already exists" }),
      });

      const { createOrganization } = await import("./organization");
      const result = await createOrganization(orgData);

      expect(result.organization).toBeNull();
      expect(result.error).toBe("Organization already exists");
    });

    it("[1.2-UNIT-ORG-003][P2] should handle network errors", async () => {
      const orgData = {
        name: "Test Agency",
        slug: "test-agency",
        type: "agency" as OrgType,
      };

      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { createOrganization } = await import("./organization");
      const result = await createOrganization(orgData);

      expect(result.organization).toBeNull();
      expect(result.error).toBe("Network error");
    });
  });

  describe("updateOrganization", () => {
    it("[1.2-UNIT-ORG-004][P1] should update organization settings", async () => {
      const updates = {
        settings: {
          features: { advancedAnalytics: true, crmIntegration: true },
        },
      };
      const mockOrg = { id: ORG_IDS.validOrgId, settings: updates.settings };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrg,
      });

      const { updateOrganization } = await import("./organization");
      const result = await updateOrganization(ORG_IDS.validOrgId, updates);

      expect(result.organization).toEqual(mockOrg);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/organizations/${ORG_IDS.validOrgId}`),
        expect.objectContaining({
          method: "PATCH",
        }),
      );
    });

    it("[1.2-UNIT-ORG-005][P1] should return error when update fails", async () => {
      const updates = { settings: { features: {} } };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: "Organization not found" }),
      });

      const { updateOrganization } = await import("./organization");
      const result = await updateOrganization(ORG_IDS.testOrgId, updates);

      expect(result.organization).toBeNull();
      expect(result.error).toBe("Organization not found");
    });
  });

  describe("getOrganization", () => {
    it("[1.2-UNIT-ORG-006][P1] should fetch organization by ID", async () => {
      const mockOrg = {
        id: ORG_IDS.validOrgId,
        name: "Test Agency",
        type: "agency",
        plan: "pro",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrg,
      });

      const { getOrganization } = await import("./organization");
      const result = await getOrganization(ORG_IDS.validOrgId);

      expect(result.organization).toEqual(mockOrg);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/organizations/${ORG_IDS.validOrgId}`),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        }),
      );
    });

    it("[1.2-UNIT-ORG-007][P1] should return error when organization not found", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: "Not found" }),
      });

      const { getOrganization } = await import("./organization");
      const result = await getOrganization(ORG_IDS.testOrgId);

      expect(result.organization).toBeNull();
      expect(result.error).toBe("Not found");
    });

    it("[1.2-UNIT-ORG-008][P2] should handle fetch errors", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Connection failed"));

      const { getOrganization } = await import("./organization");
      const result = await getOrganization(ORG_IDS.validOrgId);

      expect(result.organization).toBeNull();
      expect(result.error).toBe("Connection failed");
    });
  });
});
