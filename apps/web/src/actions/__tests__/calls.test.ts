import { describe, it, expect, vi, beforeEach } from "vitest";

const mockGetToken = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({ getToken: mockGetToken }),
}));

describe("[2.1][calls.ts] — Server actions for calls API", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("fetch", vi.fn());
    mockGetToken.mockResolvedValue("test-token");
  });

  describe("triggerCall", () => {
    it("[2.1-UNIT-400][P0] Given unauthenticated, When triggerCall called, Then returns not authenticated error", async () => {
      mockGetToken.mockResolvedValue(null);
      const { triggerCall } = await import("@/actions/calls");
      const result = await triggerCall({ phoneNumber: "+1234567890" });
      expect(result.data).toBeNull();
      expect(result.error).toBe("Not authenticated");
    });

    it("[2.1-UNIT-401][P0] Given valid token, When API returns 201, Then returns call data", async () => {
      const callData = {
        call: {
          id: 1,
          vapiCallId: "call_abc",
          orgId: "org_123",
          status: "pending",
          phoneNumber: "+1234567890",
        },
      };
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(callData),
      } as Response);
      const { triggerCall } = await import("@/actions/calls");
      const result = await triggerCall({
        phoneNumber: "+1234567890",
        agentId: 5,
        leadId: 10,
      });
      expect(result.data).toEqual(callData);
      expect(result.error).toBeNull();
    });

    it("[2.1-UNIT-402][P0] Given API returns 403 USAGE_LIMIT_EXCEEDED, When triggerCall called, Then returns limit error", async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            detail: {
              message: "Monthly call limit has been reached.",
            },
          }),
      } as Response);
      const { triggerCall } = await import("@/actions/calls");
      const result = await triggerCall({ phoneNumber: "+1234567890" });
      expect(result.data).toBeNull();
      expect(result.error).toContain("Monthly call limit");
    });

    it("[2.1-UNIT-403][P1] Given API returns non-JSON error, When triggerCall called, Then returns fallback error", async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        json: () => Promise.reject(new Error("Not JSON")),
      } as Response);
      const { triggerCall } = await import("@/actions/calls");
      const result = await triggerCall({ phoneNumber: "+1234567890" });
      expect(result.data).toBeNull();
      expect(result.error).toBe("Failed to trigger call");
    });

    it("[2.1-UNIT-404][P1] Given fetch throws, When triggerCall called, Then returns error message", async () => {
      vi.mocked(global.fetch).mockRejectedValue(new Error("Network error"));
      const { triggerCall } = await import("@/actions/calls");
      const result = await triggerCall({ phoneNumber: "+1234567890" });
      expect(result.data).toBeNull();
      expect(result.error).toBe("Network error");
    });

    it("[2.1-UNIT-405][P0] Given valid payload, When triggerCall called, Then sends correct request body", async () => {
      const callData = {
        call: {
          id: 1,
          vapiCallId: "v1",
          status: "pending",
          phoneNumber: "+1234567890",
        },
      };
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(callData),
      } as Response);
      const { triggerCall } = await import("@/actions/calls");
      await triggerCall({
        phoneNumber: "+1234567890",
        agentId: 5,
        leadId: 10,
        campaignId: 99,
      });

      const fetchOpts = vi.mocked(global.fetch).mock
        .calls[0]![1] as RequestInit;
      const body = JSON.parse(fetchOpts.body as string);
      expect(body).toEqual({
        phoneNumber: "+1234567890",
        agentId: 5,
        leadId: 10,
        campaignId: 99,
      });
    });
  });
});
