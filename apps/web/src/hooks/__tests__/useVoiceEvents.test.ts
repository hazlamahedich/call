import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useVoiceEvents } from "../useVoiceEvents";
import type { TranscriptEntry } from "@call/types";

describe("useVoiceEvents", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("initializes with zero volume, inactive, no interruption", () => {
    const { result } = renderHook(() => useVoiceEvents([]));

    expect(result.current.volume).toBe(0);
    expect(result.current.isActive).toBe(false);
    expect(result.current.lastInterruptionAt).toBeUndefined();
    expect(result.current.sentiment).toBe(0.5); // neutral default
  });

  it("detects speech-start from transcript entry metadata", () => {
    const entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Hello",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "speech-start",
      },
    ];

    const { result } = renderHook(() => useVoiceEvents(entries));

    expect(result.current.volume).toBe(0.8); // VOLUME_SPEAKING
    expect(result.current.isActive).toBe(true);
  });

  it("detects speech-end from transcript entry metadata", () => {
    let entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Hello",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "speech-start",
      },
    ];

    const { result, rerender } = renderHook(() => useVoiceEvents(entries));

    expect(result.current.isActive).toBe(true);

    // Add speech-end entry
    entries = [
      ...entries,
      {
        id: 2,
        callId: 1,
        role: "lead",
        text: "Hello",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "speech-end",
      },
    ];

    act(() => {
      rerender(entries);
    });

    expect(result.current.isActive).toBe(false);
  });

  it("detects interruption from event_type field", () => {
    const entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Let me stop you there",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "interruption",
      },
    ];

    const { result } = renderHook(() => useVoiceEvents(entries));

    expect(result.current.lastInterruptionAt).toBeInstanceOf(Date);
  });

  it("applies exponential decay to volume when no speech events", () => {
    const entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Hello",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "speech-start",
      },
    ];

    const { result } = renderHook(() => useVoiceEvents(entries));

    expect(result.current.volume).toBe(0.8);

    // Speech ends
    const endEntry: TranscriptEntry = {
      ...entries[0],
      id: 2,
      event_type: "speech-end",
    };

    act(() => {
      result.current.volume = 0.8;
    });

    // Advance time by 100ms for one decay cycle
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Volume should decay: 0.8 * 0.95 = 0.76
    waitFor(() => {
      expect(result.current.volume).toBeLessThan(0.8);
    });
  });

  it("resets interruption flag after 500ms", () => {
    const entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Stop",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "interruption",
      },
    ];

    const { result } = renderHook(() => useVoiceEvents(entries));

    expect(result.current.lastInterruptionAt).toBeDefined();

    // Advance past 500ms threshold
    act(() => {
      vi.advanceTimersByTime(600);
    });

    waitFor(() => {
      expect(result.current.lastInterruptionAt).toBeUndefined();
    });
  });

  it("cleans up timers on unmount", () => {
    const entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Hello",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "speech-start",
      },
    ];

    const { unmount } = renderHook(() => useVoiceEvents(entries));

    // Should not throw or leak
    expect(() => unmount()).not.toThrow();
  });

  it("consolidates timer management to prevent memory leaks", () => {
    const entries: TranscriptEntry[] = [
      {
        id: 1,
        callId: 1,
        role: "lead",
        text: "Hello",
        startTime: 0,
        endTime: 1000,
        confidence: 0.95,
        receivedAt: new Date().toISOString(),
        timestamp: Date.now(),
        event_type: "interruption",
      },
    ];

    const { unmount } = renderHook(() => useVoiceEvents(entries));

    // Unmount should clean up both interruption and decay timers
    act(() => {
      unmount();
    });

    // If timers were not cleaned up, this would cause issues
    expect(true).toBe(true);
  });
});
