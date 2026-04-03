/**
 * Story 1-5: White-labeled Admin Portal & Custom Branding
 * Unit Tests for Branding Server Actions
 *
 * Test ID Format: 1.5-UNIT-BRANDING-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { AgencyBranding, DomainVerificationResult } from "@call/types";

const mockGetToken = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: vi.fn(() => Promise.resolve({ getToken: mockGetToken })),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

const MOCK_BRANDING: AgencyBranding = {
  id: 1,
  orgId: "org_abc123",
  logoUrl: "data:image/png;base64,abc123",
  primaryColor: "#FF5500",
  customDomain: "example.com",
  domainVerified: true,
  brandName: "Test Brand",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

describe("[P0] Branding Server Actions", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockGetToken.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("getBranding", () => {
    it("[1.5-UNIT-001][P0] Given authenticated user, When fetching branding, Then returns branding data", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => MOCK_BRANDING,
      });

      const { getBranding } = await import("./branding");
      const result = await getBranding("org_abc123");

      expect(result.data).toEqual(MOCK_BRANDING);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_URL}/branding`,
        expect.objectContaining({
          headers: { Authorization: "Bearer test-token" },
        }),
      );
    });

    it("[1.5-UNIT-002][P1] Given 404 response, When fetching branding, Then returns null data with no error", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const { getBranding } = await import("./branding");
      const result = await getBranding("org_abc123");

      expect(result.data).toBeNull();
      expect(result.error).toBeNull();
    });

    it("[1.5-UNIT-003][P1] Given no auth token, When fetching branding, Then returns Not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);

      const { getBranding } = await import("./branding");
      const result = await getBranding("org_abc123");

      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.5-UNIT-004][P1] Given server error with JSON body, When fetching branding, Then extracts error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: { message: "Internal server error" } }),
      });

      const { getBranding } = await import("./branding");
      const result = await getBranding("org_abc123");

      expect(result.data).toBeNull();
      expect(result.error).toBe("Internal server error");
    });

    it("[1.5-UNIT-005][P2] Given network error, When fetching branding, Then returns error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { getBranding } = await import("./branding");
      const result = await getBranding("org_abc123");

      expect(result.data).toBeNull();
      expect(result.error).toBe("Network error");
    });

    it("[1.5-UNIT-006][P2] Given non-JSON error response, When fetching branding, Then returns default error", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("Not JSON");
        },
      });

      const { getBranding } = await import("./branding");
      const result = await getBranding("org_abc123");

      expect(result.data).toBeNull();
      expect(result.error).toBe("Failed to fetch branding");
    });
  });

  describe("updateBranding", () => {
    it("[1.5-UNIT-007][P0] Given authenticated admin, When updating branding, Then sends PUT with correct data", async () => {
      mockGetToken.mockResolvedValue("test-token");
      const updated = { ...MOCK_BRANDING, primaryColor: "#0000FF" };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updated,
      });

      const { updateBranding } = await import("./branding");
      const result = await updateBranding("org_abc123", {
        primaryColor: "#0000FF",
      });

      expect(result.data).toEqual(updated);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_URL}/branding`,
        expect.objectContaining({
          method: "PUT",
          headers: {
            Authorization: "Bearer test-token",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ primaryColor: "#0000FF" }),
        }),
      );
    });

    it("[1.5-UNIT-008][P1] Given no auth token, When updating branding, Then returns Not authenticated", async () => {
      mockGetToken.mockResolvedValue(null);

      const { updateBranding } = await import("./branding");
      const result = await updateBranding("org_abc123", {
        primaryColor: "#0000FF",
      });

      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.5-UNIT-009][P1] Given server error, When updating branding, Then returns error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: { message: "Invalid color format" },
        }),
      });

      const { updateBranding } = await import("./branding");
      const result = await updateBranding("org_abc123", {
        primaryColor: "invalid",
      });

      expect(result.data).toBeNull();
      expect(result.error).toBe("Invalid color format");
    });

    it("[1.5-UNIT-010][P2] Given network error, When updating branding, Then returns error", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockRejectedValueOnce(new Error("Connection failed"));

      const { updateBranding } = await import("./branding");
      const result = await updateBranding("org_abc123", {
        primaryColor: "#0000FF",
      });

      expect(result.data).toBeNull();
      expect(result.error).toBe("Connection failed");
    });
  });

  describe("verifyDomain", () => {
    const VERIFY_RESULT: DomainVerificationResult = {
      verified: true,
      message: "CNAME verified successfully",
    };

    it("[1.5-UNIT-011][P0] Given authenticated admin, When verifying domain, Then sends POST and returns result", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => VERIFY_RESULT,
      });

      const { verifyDomain } = await import("./branding");
      const result = await verifyDomain("org_abc123", "example.com");

      expect(result.data).toEqual(VERIFY_RESULT);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_URL}/branding/verify-domain`,
        expect.objectContaining({
          method: "POST",
          headers: {
            Authorization: "Bearer test-token",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ domain: "example.com" }),
        }),
      );
    });

    it("[1.5-UNIT-012][P1] Given no auth token, When verifying domain, Then returns Not authenticated", async () => {
      mockGetToken.mockResolvedValue(null);

      const { verifyDomain } = await import("./branding");
      const result = await verifyDomain("org_abc123", "example.com");

      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.5-UNIT-013][P1] Given server error, When verifying domain, Then returns error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: { message: "Invalid domain format" },
        }),
      });

      const { verifyDomain } = await import("./branding");
      const result = await verifyDomain("org_abc123", "bad-domain");

      expect(result.data).toBeNull();
      expect(result.error).toBe("Invalid domain format");
    });

    it("[1.5-UNIT-014][P2] Given network error, When verifying domain, Then returns error", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockRejectedValueOnce(new Error("DNS lookup failed"));

      const { verifyDomain } = await import("./branding");
      const result = await verifyDomain("org_abc123", "example.com");

      expect(result.data).toBeNull();
      expect(result.error).toBe("DNS lookup failed");
    });
  });
});
