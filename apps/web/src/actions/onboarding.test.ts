/**
 * Story 1-6: 10-Minute Launch Onboarding Wizard
 * Unit Tests for Onboarding Server Actions
 *
 * Test ID Format: 1.6-UNIT-080..089
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockGetToken = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: vi.fn(() => Promise.resolve({ getToken: mockGetToken })),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

describe("[P0] Onboarding Server Actions", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockGetToken.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("getOnboardingStatus", () => {
    it("[1.6-UNIT-080][P0] Given authenticated user, When fetching onboarding status, Then returns status data", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ completed: false }),
      });

      const { getOnboardingStatus } = await import("./onboarding");
      const result = await getOnboardingStatus();

      expect(result.data).toEqual({ completed: false });
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_URL}/onboarding/status`,
        expect.objectContaining({
          headers: { Authorization: "Bearer test-token" },
        }),
      );
    });

    it("[1.6-UNIT-081][P1] Given no auth token, When fetching onboarding status, Then returns Not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);

      const { getOnboardingStatus } = await import("./onboarding");
      const result = await getOnboardingStatus();

      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.6-UNIT-082][P1] Given server error with JSON body, When fetching onboarding status, Then extracts error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: { message: "Internal server error" } }),
      });

      const { getOnboardingStatus } = await import("./onboarding");
      const result = await getOnboardingStatus();

      expect(result.data).toBeNull();
      expect(result.error).toBe("Internal server error");
    });

    it("[1.6-UNIT-083][P2] Given network error, When fetching onboarding status, Then returns error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { getOnboardingStatus } = await import("./onboarding");
      const result = await getOnboardingStatus();

      expect(result.data).toBeNull();
      expect(result.error).toBe("Network error");
    });

    it("[1.6-UNIT-084][P2] Given non-JSON error response, When fetching onboarding status, Then returns default error", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("Not JSON");
        },
      });

      const { getOnboardingStatus } = await import("./onboarding");
      const result = await getOnboardingStatus();

      expect(result.data).toBeNull();
      expect(result.error).toBe("Failed to fetch onboarding status");
    });
  });

  describe("completeOnboarding", () => {
    const MOCK_PAYLOAD = {
      businessGoal: "lead_generation",
      scriptContext: "We sell premium widgets to small businesses",
      voiceId: "voice_abc",
      integrationType: "crm",
      safetyLevel: "standard",
    };

    const MOCK_AGENT_RESPONSE = {
      agent: {
        id: 1,
        name: "Test Agent",
        businessGoal: "lead_generation",
        scriptContext: "We sell premium widgets to small businesses",
        voiceId: "voice_abc",
        integrationType: "crm",
        safetyLevel: "standard",
        createdAt: "2026-01-01T00:00:00Z",
        updatedAt: "2026-01-01T00:00:00Z",
      },
    };

    it("[1.6-UNIT-085][P0] Given authenticated user, When completing onboarding, Then sends POST and returns agent data", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => MOCK_AGENT_RESPONSE,
      });

      const { completeOnboarding } = await import("./onboarding");
      const result = await completeOnboarding(MOCK_PAYLOAD);

      expect(result.agent).toEqual(MOCK_AGENT_RESPONSE.agent);
      expect(result.error).toBeNull();
      expect(mockFetch).toHaveBeenCalledWith(
        `${API_URL}/onboarding/complete`,
        expect.objectContaining({
          method: "POST",
          headers: {
            Authorization: "Bearer test-token",
            "Content-Type": "application/json",
          },
          body: JSON.stringify(MOCK_PAYLOAD),
        }),
      );
    });

    it("[1.6-UNIT-086][P1] Given no auth token, When completing onboarding, Then returns Not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);

      const { completeOnboarding } = await import("./onboarding");
      const result = await completeOnboarding(MOCK_PAYLOAD);

      expect(result.agent).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.6-UNIT-087][P1] Given server error with JSON body, When completing onboarding, Then extracts error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: { message: "Invalid business goal" },
        }),
      });

      const { completeOnboarding } = await import("./onboarding");
      const result = await completeOnboarding(MOCK_PAYLOAD);

      expect(result.agent).toBeNull();
      expect(result.error).toBe("Invalid business goal");
    });

    it("[1.6-UNIT-088][P2] Given network error, When completing onboarding, Then returns error message", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockRejectedValueOnce(new Error("Connection failed"));

      const { completeOnboarding } = await import("./onboarding");
      const result = await completeOnboarding(MOCK_PAYLOAD);

      expect(result.agent).toBeNull();
      expect(result.error).toBe("Connection failed");
    });

    it("[1.6-UNIT-089][P2] Given non-JSON error response, When completing onboarding, Then returns default error", async () => {
      mockGetToken.mockResolvedValue("test-token");
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("Not JSON");
        },
      });

      const { completeOnboarding } = await import("./onboarding");
      const result = await completeOnboarding(MOCK_PAYLOAD);

      expect(result.agent).toBeNull();
      expect(result.error).toBe("Failed to complete onboarding");
    });
  });
});
