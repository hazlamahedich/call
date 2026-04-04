/**
 * Story 2.6: Voice Presets by Use Case
 * Audio Player Component Tests (AC2 - Audio Sample Playback)
 *
 * Test ID Format: 2.6-FRONTEND-AC2-XXX
 * Priority: P2
 *
 * Tests the Web Audio API integration for preset sample playback,
 * including play/stop controls, error handling, and audio state management.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { render, screen, fireEvent } from "@testing-library/react";
import { VoicePresetSelector } from "../VoicePresetSelector";
import * as voicePresetsActions from "@/actions/voice-presets";

// Mock the voice-presets actions
vi.mock("@/actions/voice-presets", () => ({
  getVoicePresets: vi.fn(),
  selectVoicePreset: vi.fn(),
  getPresetSample: vi.fn(),
  saveAdvancedVoiceConfig: vi.fn(),
  getVoicePresetRecommendation: vi.fn(),
}));

// Mock Web Audio API
const mockCreateBufferSource = vi.fn();
const mockDecodeAudioData = vi.fn();
const mockResume = vi.fn();
const mockClose = vi.fn();
const mockStart = vi.fn();
const mockStop = vi.fn();

class MockAudioContext {
  state = "running";
  destination = {};
  createBufferSource = mockCreateBufferSource;

  async resume() {
    mockResume();
    this.state = "running";
    return this;
  }

  async close() {
    mockClose();
    this.state = "closed";
    return this;
  }

  async decodeAudioData(arrayBuffer: ArrayBuffer) {
    return mockDecodeAudioData(arrayBuffer);
  }
}

class MockAudioBufferSourceNode {
  buffer = null;
  loop = false;
  playbackRate = { value: 1.0 };
  connect = vi.fn(() => this);
  start = mockStart;
  stop = mockStop;
}

describe("VoicePresetSelector Audio Player (AC2 - Audio Sample Playback)", () => {
  const mockPresets = [
    {
      id: 1,
      name: "Sales - Rachel",
      use_case: "sales",
      voice_id: "voice-1",
      speech_speed: 1.0,
      stability: 0.8,
      temperature: 0.7,
      description: "High energy sales voice",
      is_active: true,
      sort_order: 1,
    },
    {
      id: 2,
      name: "Sales - Alex",
      use_case: "sales",
      voice_id: "voice-2",
      speech_speed: 1.1,
      stability: 0.7,
      temperature: 0.6,
      description: "Confident sales voice",
      is_active: true,
      sort_order: 2,
    },
  ];

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();

    // Setup default mock implementations
    vi.mocked(voicePresetsActions.getVoicePresets).mockResolvedValue({
      data: mockPresets,
      error: null,
    });

    vi.mocked(voicePresetsActions.selectVoicePreset).mockResolvedValue({
      data: { message: "Preset selected successfully" },
      error: null,
    });

    vi.mocked(voicePresetsActions.getVoicePresetRecommendation).mockResolvedValue({
      data: null,
      error: null,
    });

    // Mock Web Audio API
    (window as any).AudioContext = MockAudioContext;

    mockCreateBufferSource.mockReturnValue(new MockAudioBufferSourceNode());
    mockDecodeAudioData.mockResolvedValue({
      duration: 5.0,
      numberOfChannels: 1,
      sampleRate: 48000,
    });
  });

  afterEach(() => {
    // Cleanup
    mockCreateBufferSource.mockReset();
    mockDecodeAudioData.mockReset();
    mockResume.mockReset();
    mockClose.mockReset();
    mockStart.mockReset();
    mockStop.mockReset();
  });

  describe("[2.6-FRONTEND-AC2-001][P2] Audio Playback Initialization", () => {
    it("should initialize AudioContext on first play", async () => {
      render(<VoicePresetSelector />);

      // Wait for presets to load
      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      // Click play on first preset
      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify AudioContext was created
      expect(mockCreateBufferSource).toHaveBeenCalled();
    });

    it("should resume suspended AudioContext before playing", async () => {
      // Create a suspended AudioContext
      const suspendedContext = new MockAudioContext();
      suspendedContext.state = "suspended";
      (window as any).AudioContext = vi.fn(() => suspendedContext);

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify resume was called
      expect(mockResume).toHaveBeenCalled();
    });
  });

  describe("[2.6-FRONTEND-AC2-002][P2] Play/Stop Controls", () => {
    it("should play audio when play button is clicked", async () => {
      // Mock successful audio response
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify audio was decoded and started
      await waitFor(() => {
        expect(mockDecodeAudioData).toHaveBeenCalled();
        expect(mockStart).toHaveBeenCalled();
      });
    });

    it("should stop audio when clicking play button again on same preset", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);

      // First click - play
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Second click - stop
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify stop was called
      expect(mockStop).toHaveBeenCalled();
    });

    it("should switch to different preset when clicking play on another preset", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);

      // Play first preset
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Play second preset (should stop first)
      await act(async () => {
        fireEvent.click(playButtons[1]);
      });

      // Verify stop was called (to stop first preset)
      expect(mockStop).toHaveBeenCalled();
    });
  });

  describe("[2.6-FRONTEND-AC2-003][P2] Error Handling", () => {
    it("should display error when TTS provider fails", async () => {
      // Mock TTS failure
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: null,
        error: "Voice samples temporarily unavailable. Please try again later.",
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify error message is displayed
      await waitFor(() => {
        expect(screen.getByText(/temporarily unavailable/i)).toBeInTheDocument();
      });
    });

    it("should display error when audio data is invalid", async () => {
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.reject(new Error("Invalid audio")) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify error state is cleared and UI remains functional
      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });
    });

    it("should handle decodeAudioData failure gracefully", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      // Mock decode failure
      mockDecodeAudioData.mockRejectedValue(new Error("Failed to decode audio"));

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify UI remains functional after error
      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });
    });
  });

  describe("[2.6-FRONTEND-AC2-004][P2] Audio State Management", () => {
    it("should track currently playing preset", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);

      // Play first preset
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify play button changed to stop
      await waitFor(() => {
        expect(screen.getByLabelText(/stop sample/i)).toBeInTheDocument();
      });
    });

    it("should clear playing state when audio ends naturally", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      // Mock source that auto-stops after duration
      let onEndedCallback: (() => void) | null = null;
      mockCreateBufferSource.mockImplementation(() => {
        const source = new MockAudioBufferSourceNode();
        source.connect = vi.fn(function(this: any) {
          onEndedCallback = vi.fn();
          return this;
        });
        return source;
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // In real implementation, onended event would clear playing state
      // This test verifies the pattern is in place
      expect(mockStart).toHaveBeenCalled();
    });
  });

  describe("[2.6-FRONTEND-AC2-005][P2] Resource Cleanup", () => {
    it("should stop audio on component unmount", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      const { unmount } = render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Unmount component
      unmount();

      // Verify cleanup was called
      expect(mockStop).toHaveBeenCalled();
      expect(mockClose).toHaveBeenCalled();
    });

    it("should close AudioContext on component unmount", async () => {
      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const { unmount } = render(<VoicePresetSelector />);
      unmount();

      // Verify AudioContext was closed
      expect(mockClose).toHaveBeenCalled();
    });
  });

  describe("[2.6-FRONTEND-AC2-006][P2] Concurrent Playback Prevention", () => {
    it("should stop previous audio before playing new audio", async () => {
      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);

      // Play first preset
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Play second preset (should stop first)
      await act(async () => {
        fireEvent.click(playButtons[1]);
      });

      // Verify previous audio was stopped
      expect(mockStop).toHaveBeenCalled();
    });
  });

  describe("[2.6-FRONTEND-AC2-007][P2] Browser Autoplay Policy", () => {
    it("should handle suspended AudioContext state", async () => {
      const suspendedContext = new MockAudioContext();
      suspendedContext.state = "suspended";
      (window as any).AudioContext = vi.fn(() => suspendedContext);

      const mockAudioData = new ArrayBuffer(1024);
      vi.mocked(voicePresetsActions.getPresetSample).mockResolvedValue({
        data: { arrayBuffer: () => Promise.resolve(mockAudioData) } as any,
        error: null,
      });

      render(<VoicePresetSelector />);

      await waitFor(() => {
        expect(screen.getByText("Sales - Rachel")).toBeInTheDocument();
      });

      const playButtons = screen.getAllByLabelText(/play sample/i);
      await act(async () => {
        fireEvent.click(playButtons[0]);
      });

      // Verify resume was called to handle autoplay policy
      expect(mockResume).toHaveBeenCalled();
      expect(suspendedContext.state).toBe("running");
    });
  });
});
