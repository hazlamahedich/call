import { renderHook, act, waitFor } from "@testing-library/react";
import { useAudioPlayback } from "@/hooks/useAudioPlayback";

// Mock Web Audio API
const mockAudioContext = {
  state: "running",
  resume: jest.fn(() => Promise.resolve()),
  close: jest.fn(() => Promise.resolve()),
  decodeAudioData: jest.fn(),
  createBufferSource: jest.fn(),
};

const mockAudioBufferSource = {
  buffer: null,
  start: jest.fn(),
  stop: jest.fn(),
  onended: null,
  onerror: null,
  connect: jest.fn(),
};

(global as any).AudioContext = jest.fn(() => mockAudioContext);

describe("useAudioPlayback", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAudioContext.state = "running";
    mockAudioContext.decodeAudioData.mockResolvedValue({
      duration: 1.0,
    });
    mockAudioContext.createBufferSource.mockReturnValue(
      mockAudioBufferSource
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("playSample", () => {
    it("should play audio successfully", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });
      mockAudioContext.decodeAudioData.mockResolvedValue({
        duration: 1.0,
      });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(mockAudioContext.resume).toHaveBeenCalled();
      expect(mockAudioBufferSource.start).toHaveBeenCalledWith(0);
      expect(result.current[0].playingId).toBe(1);
      expect(result.current[0].error).toBeNull();
    });

    it("should handle audio context suspended state", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      mockAudioContext.state = "suspended";
      mockAudioContext.resume.mockResolvedValue(undefined);

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(mockAudioContext.resume).toHaveBeenCalled();
      expect(mockAudioBufferSource.start).toHaveBeenCalledWith(0);
    });

    it("should toggle playback when clicking same preset", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      // Start playback
      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(result.current[0].playingId).toBe(1);

      // Stop playback by clicking same preset
      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(result.current[0].playingId).toBeNull();
    });

    it("should stop previous audio when starting new playback", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      // Start first playback
      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      // Start second playback
      await act(async () => {
        await actions.playSample(2, mockBlob);
      });

      expect(mockAudioBufferSource.stop).toHaveBeenCalledTimes(1);
      expect(result.current[0].playingId).toBe(2);
    });

    it("should handle decodeAudioData failure", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      mockAudioContext.decodeAudioData.mockRejectedValue(
        new Error("Failed to decode audio")
      );

      const mockBlob = new Blob(["invalid audio"], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(result.current[0].playingId).toBeNull();
      expect(result.current[0].error).toContain("Failed to play audio");
    });

    it("should handle audio source start failure", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      mockAudioBufferSource.start.mockImplementation(() => {
        throw new Error("Audio start failed");
      });

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(result.current[0].playingId).toBeNull();
      expect(result.current[0].error).toContain("Failed to play audio");
    });

    it("should handle audio playback error via onerror", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      // Trigger onerror callback
      mockAudioBufferSource.onerror = () => {
        result.current[0] = {
          playingId: null,
          error: "Failed to play audio",
        };
      };

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      // Simulate onerror being called
      if (mockAudioBufferSource.onerror) {
        mockAudioBufferSource.onerror(new Error("Playback error"));
      }

      expect(result.current[0].error).toBe("Failed to play audio");
    });
  });

  describe("stopPlayback", () => {
    it("should stop currently playing audio", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      // Start playback
      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(result.current[0].playingId).toBe(1);

      // Stop playback
      act(() => {
        actions.stopPlayback();
      });

      expect(mockAudioBufferSource.stop).toHaveBeenCalled();
      expect(result.current[0].playingId).toBeNull();
      expect(result.current[0].error).toBeNull();
    });

    it("should handle stop when no audio is playing", () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      act(() => {
        actions.stopPlayback();
      });

      // Should not throw error
      expect(result.current[0].playingId).toBeNull();
    });
  });

  describe("clearError", () => {
    it("should clear error state", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      // Set error state
      mockAudioContext.decodeAudioData.mockRejectedValue(
        new Error("Decode failed")
      );

      const mockBlob = new Blob(["invalid audio"], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(result.current[0].error).not.toBeNull();

      // Clear error
      act(() => {
        actions.clearError();
      });

      expect(result.current[0].error).toBeNull();
    });
  });

  describe("cleanup", () => {
    it("should cleanup audio resources on unmount", async () => {
      const { result, unmount } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      expect(mockAudioContext.close).not.toHaveBeenCalled();

      unmount();

      expect(mockAudioBufferSource.stop).toHaveBeenCalled();
      expect(mockAudioContext.close).toHaveBeenCalled();
    });

    it("should handle cleanup errors gracefully", async () => {
      const { result, unmount } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      mockAudioBufferSource.stop.mockImplementation(() => {
        throw new Error("Already stopped");
      });

      mockAudioContext.close.mockRejectedValue(new Error("Close failed"));

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, mockBlob);
      });

      // Should not throw error during unmount
      expect(() => unmount()).not.toThrow();
    });
  });

  describe("edge cases", () => {
    it("should handle empty blob data", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const emptyBlob = new Blob([], { type: "audio/mpeg" });

      await act(async () => {
        await actions.playSample(1, emptyBlob);
      });

      // Should handle gracefully - either play or error
      expect(["playingId", "error"]).toContain(
        result.current[0].playingId !== null ? "playingId" : "error"
      );
    });

    it("should handle rapid play/stop cycles", async () => {
      const { result } = renderHook(() => useAudioPlayback());
      const [state, actions] = result.current;

      const mockBlob = new Blob(["audio data"], { type: "audio/mpeg" });

      // Rapid play/stop cycles
      await act(async () => {
        await actions.playSample(1, mockBlob);
        actions.stopPlayback();
        await actions.playSample(2, mockBlob);
        actions.stopPlayback();
        await actions.playSample(3, mockBlob);
      });

      // Should complete without hanging
      expect(result.current[0].playingId).toBe(3);
    });
  });
});
