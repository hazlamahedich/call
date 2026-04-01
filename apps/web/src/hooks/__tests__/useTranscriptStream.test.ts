import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

const mockGetToken = vi.fn();

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: mockGetToken }),
}));

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send = vi.fn();
  close = vi.fn();
}

describe("[2.2][useTranscriptStream] — WebSocket hook for live transcript entries", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    mockGetToken.mockResolvedValue("test-jwt");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function getWs() {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }

  it("[2.2-UNIT-600][P0] Given null callId, When hook mounts, Then no WebSocket is created", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    renderHook(() => useTranscriptStream(null));
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("[2.2-UNIT-601][P0] Given valid callId, When hook mounts, Then WebSocket connects and sends JWT token as first message", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    renderHook(() => useTranscriptStream(42));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    });

    const ws = getWs();
    expect(ws.url).toContain("/ws/calls/42/transcript");
    expect(ws.url).not.toContain("token=");

    act(() => {
      ws.onopen!();
    });

    await waitFor(() => {
      expect(ws.send).toHaveBeenCalledWith(
        JSON.stringify({ token: "test-jwt" }),
      );
    });
  });

  it("[2.2-UNIT-602][P0] Given no auth token, When hook mounts, Then error is set and no WebSocket created", async () => {
    mockGetToken.mockResolvedValue(null);
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() => {
      expect(result.current.error).toBe("Not authenticated");
    });
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("[2.2-UNIT-603][P0] Given connected WebSocket, When transcript message arrives, Then entry is added", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    act(() => {
      ws.onmessage!({
        data: JSON.stringify({
          type: "transcript",
          entry: {
            id: 1,
            callId: 42,
            role: "assistant-ai",
            text: "Hello there",
            startTime: 100,
            endTime: 200,
            confidence: 0.95,
            receivedAt: "2025-01-01T00:00:00Z",
          },
        }),
      });
    });

    await waitFor(() => {
      expect(result.current.entries).toHaveLength(1);
      expect(result.current.entries[0].text).toBe("Hello there");
      expect(result.current.entries[0].role).toBe("assistant-ai");
    });
  });

  it("[2.2-UNIT-604][P1] Given connected WebSocket, When multiple messages arrive, Then entries accumulate", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    for (let i = 1; i <= 3; i++) {
      act(() => {
        ws.onmessage!({
          data: JSON.stringify({
            type: "transcript",
            entry: {
              id: i,
              callId: 42,
              role: "lead",
              text: `Msg ${i}`,
              startTime: i * 100,
              endTime: i * 100 + 50,
            },
          }),
        });
      });
    }

    await waitFor(() => {
      expect(result.current.entries).toHaveLength(3);
    });
  });

  it("[2.2-UNIT-605][P1] Given connected WebSocket, When malformed JSON arrives, Then entry is ignored", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    act(() => {
      ws.onmessage!({ data: "not-valid-json" });
    });

    expect(result.current.entries).toHaveLength(0);
  });

  it("[2.2-UNIT-606][P1] Given connected WebSocket, When onerror fires, Then error state is set", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onerror!();
    });

    await waitFor(() => {
      expect(result.current.error).toBe("WebSocket connection error");
    });
  });

  it("[2.2-UNIT-607][P1] Given connected WebSocket, When onclose fires with non-1008 code, Then reconnect setTimeout is scheduled", async () => {
    const spy = vi.spyOn(global, "setTimeout");
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    spy.mockClear();
    act(() => {
      ws.onclose!({ code: 1006 });
    });
    await waitFor(() => expect(result.current.isConnected).toBe(false));

    const calls = spy.mock.calls.filter(
      (c) => typeof c[0] === "function" && typeof c[1] === "number" && c[1] > 0,
    );
    expect(calls.length).toBeGreaterThanOrEqual(1);
    expect(typeof calls[calls.length - 1][0]).toBe("function");
    spy.mockRestore();
  });

  it("[2.2-UNIT-608][P1] Given connected WebSocket, When onclose fires with code 1008, Then no reconnect setTimeout is scheduled", async () => {
    const spy = vi.spyOn(global, "setTimeout");
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    spy.mockClear();
    act(() => {
      ws.onclose!({ code: 1008 });
    });

    expect(spy).not.toHaveBeenCalled();
    expect(MockWebSocket.instances).toHaveLength(1);
    spy.mockRestore();
  });

  it("[2.2-UNIT-609][P2] Given hook unmount, When cleanup runs, Then WebSocket is closed", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { unmount } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    unmount();

    expect(ws.close).toHaveBeenCalled();
  });

  it("[2.2-UNIT-610][P2] Given message with non-transcript type, When received, Then entry is ignored", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    act(() => {
      ws.onmessage!({
        data: JSON.stringify({ type: "ping", entry: { id: 1 } }),
      });
    });

    expect(result.current.entries).toHaveLength(0);
  });

  it("[2.2-UNIT-611][P1] Given max reconnect attempts exceeded, When onclose fires repeatedly, Then no more reconnects after 10 attempts", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result } = renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    let ws = getWs();

    act(() => {
      ws.onopen!();
    });
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    for (let i = 0; i < 11; i++) {
      act(() => {
        ws.onclose!({ code: 1006 });
      });
      await waitFor(() => expect(result.current.isConnected).toBe(false));

      const nextWs = getWs();
      if (nextWs !== ws) {
        ws = nextWs;
        act(() => {
          ws.onopen!();
        });
      }
    }

    expect(MockWebSocket.instances.length).toBeLessThanOrEqual(11);
  });

  it("[2.2-UNIT-612][P1] Given callId changes, When new hook renders, Then new WebSocket connects to new callId", async () => {
    const { useTranscriptStream } = await import("../useTranscriptStream");
    const { result, rerender } = renderHook(
      ({ callId }) => useTranscriptStream(callId),
      { initialProps: { callId: 42 } },
    );

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws1 = getWs();
    expect(ws1.url).toContain("/ws/calls/42/transcript");

    rerender({ callId: 99 });

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2),
    );
    const ws2 = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    expect(ws2.url).toContain("/ws/calls/99/transcript");
  });

  it("[2.2-UNIT-613][P1] Given https API URL, When WebSocket connects, Then uses wss protocol", async () => {
    const originalEnv = process.env.NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";

    const { useTranscriptStream } = await import("../useTranscriptStream");
    renderHook(() => useTranscriptStream(42));

    await waitFor(() =>
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1),
    );
    const ws = getWs();
    expect(ws.url).toContain("wss://api.example.com/ws/calls/42/transcript");

    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });
});
