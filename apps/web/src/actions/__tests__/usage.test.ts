import { describe, it, expect, vi, beforeEach } from "vitest";
import { createUsageSummary } from "@/test/factories/usage";

const mockGetToken = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({ getToken: mockGetToken }),
}));

describe("[1.7][usage.ts] — Server actions for usage API", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("fetch", vi.fn());
    mockGetToken.mockResolvedValue("test-token");
  });

  describe("getUsageSummary", () => {
    it("[1.7-UNIT-090][P0] Given unauthenticated, When called, Then returns not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);
      const { getUsageSummary } = await import("@/actions/usage");
      const result = await getUsageSummary();
      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.7-UNIT-091][P0] Given valid token, When API returns 200, Then returns usage data", async () => {
      const summary = createUsageSummary();
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(summary),
      } as Response);
      const { getUsageSummary } = await import("@/actions/usage");
      const result = await getUsageSummary();
      expect(result.data).toEqual(summary);
      expect(result.error).toBeNull();
    });

    it("[1.7-UNIT-092][P0] Given API returns 403, When called, Then returns error message", async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            detail: { message: "Monthly call limit reached" },
          }),
      } as Response);
      const { getUsageSummary } = await import("@/actions/usage");
      const result = await getUsageSummary();
      expect(result.data).toBeNull();
      expect(result.error).toBe("Monthly call limit reached");
    });

    it("[1.7-UNIT-093][P1] Given API returns non-JSON error, When called, Then returns fallback error", async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        json: () => Promise.reject(new Error("Not JSON")),
      } as Response);
      const { getUsageSummary } = await import("@/actions/usage");
      const result = await getUsageSummary();
      expect(result.data).toBeNull();
      expect(result.error).toBe("Failed to fetch usage summary");
    });

    it("[1.7-UNIT-094][P1] Given fetch throws, When called, Then returns error message", async () => {
      vi.mocked(global.fetch).mockRejectedValue(new Error("Network error"));
      const { getUsageSummary } = await import("@/actions/usage");
      const result = await getUsageSummary();
      expect(result.data).toBeNull();
      expect(result.error).toBe("Network error");
    });
  });

  describe("recordUsage", () => {
    it("[1.7-UNIT-095][P0] Given unauthenticated, When called, Then returns not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);
      const { recordUsage } = await import("@/actions/usage");
      const result = await recordUsage({
        resourceType: "call",
        resourceId: "call_001",
        action: "call_initiated",
      });
      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.7-UNIT-096][P0] Given valid token, When API returns 201, Then returns usage log data", async () => {
      const logData = {
        usageLog: { id: 1, resourceType: "call", action: "call_initiated" },
      };
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(logData),
      } as Response);
      const { recordUsage } = await import("@/actions/usage");
      const result = await recordUsage({
        resourceType: "call",
        resourceId: "call_001",
        action: "call_initiated",
      });
      expect(result.data).toEqual(logData);
      expect(result.error).toBeNull();
    });

    it("[1.7-UNIT-097][P1] Given API returns 403 USAGE_LIMIT_EXCEEDED, When called, Then returns limit error", async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            detail: {
              message:
                "Monthly call limit has been reached. Upgrade your plan.",
            },
          }),
      } as Response);
      const { recordUsage } = await import("@/actions/usage");
      const result = await recordUsage({
        resourceType: "call",
        resourceId: "call_002",
        action: "call_initiated",
      });
      expect(result.data).toBeNull();
      expect(result.error).toContain("Monthly call limit");
    });
  });

  describe("checkUsageCap", () => {
    it("[1.7-UNIT-098][P0] Given unauthenticated, When called, Then returns not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);
      const { checkUsageCap } = await import("@/actions/usage");
      const result = await checkUsageCap();
      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[1.7-UNIT-099][P0] Given valid token, When API returns 200, Then returns threshold data", async () => {
      const checkData = { threshold: "warning", used: 850, cap: 1000 };
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(checkData),
      } as Response);
      const { checkUsageCap } = await import("@/actions/usage");
      const result = await checkUsageCap();
      expect(result.data).toEqual(checkData);
      expect(result.error).toBeNull();
    });

    it("[1.7-UNIT-100][P1] Given API returns error, When called, Then returns error message", async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            detail: { message: "Failed to check usage cap" },
          }),
      } as Response);
      const { checkUsageCap } = await import("@/actions/usage");
      const result = await checkUsageCap();
      expect(result.data).toBeNull();
      expect(result.error).toBe("Failed to check usage cap");
    });
  });
});
