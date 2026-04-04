"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AudioPlaybackState {
  playingId: number | null;
  error: string | null;
}

interface AudioPlaybackActions {
  playSample: (presetId: number, audioData: Blob) => Promise<void>;
  stopPlayback: () => void;
  clearError: () => void;
}

/**
 * Custom hook for managing Web Audio API playback.
 *
 * Handles audio context lifecycle, playback state, and error handling.
 * Properly cleans up audio resources on unmount to prevent memory leaks.
 *
 * @returns Tuple of [state, actions]
 */
export function useAudioPlayback(): [
  AudioPlaybackState,
  AudioPlaybackActions
] {
  const audioContextRef = useRef<AudioContext | null>(null);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const audioBufferRef = useRef<AudioBuffer | null>(null);

  const [state, setState] = useState<AudioPlaybackState>({
    playingId: null,
    error: null,
  });

  // Cleanup audio resources on unmount
  useEffect(() => {
    return () => {
      // Stop any playing audio
      if (currentSourceRef.current) {
        try {
          currentSourceRef.current.stop();
        } catch (e) {
          // Source may already be stopped
        }
        currentSourceRef.current = null;
      }

      // Close AudioContext
      if (
        audioContextRef.current &&
        audioContextRef.current.state !== "closed"
      ) {
        audioContextRef.current.close().catch(console.error);
        audioContextRef.current = null;
      }
    };
  }, []);

  const playSample = useCallback(
    async (presetId: number, audioData: Blob) => {
      // Stop currently playing audio if any
      if (currentSourceRef.current) {
        try {
          currentSourceRef.current.stop();
        } catch (err) {
          // Source may already be stopped
        }
        currentSourceRef.current = null;
      }

      // If clicking the same playing preset, just stop and return
      if (state.playingId === presetId) {
        setState({ ...state, playingId: null });
        return;
      }

      try {
        // Initialize AudioContext if needed
        if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext ||
            (window as any).webkitAudioContext)();
        }

        const audioContext = audioContextRef.current;

        // Resume AudioContext if suspended (required by browser autoplay policy)
        if (audioContext.state === "suspended") {
          await audioContext.resume();
        }

        // Decode audio data using Web Audio API
        const arrayBuffer = await audioData.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        audioBufferRef.current = audioBuffer;

        // Create and configure audio source
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);

        // Handle playback end
        source.onended = () => {
          setState({ playingId: null, error: null });
          currentSourceRef.current = null;
        };

        // Handle playback errors
        source.onerror = (err) => {
          console.error("Audio playback error:", err);
          setState({
            playingId: null,
            error: "Failed to play audio",
          });
          currentSourceRef.current = null;
        };

        // Start playback
        source.start(0);
        currentSourceRef.current = source;

        setState({ playingId: presetId, error: null });
      } catch (err: any) {
        console.error("Failed to play audio with Web Audio API:", err);
        setState({
          playingId: null,
          error: `Failed to play audio: ${err?.message || "Unknown error"}`,
        });
        currentSourceRef.current = null;
      }
    },
    [state.playingId]
  );

  const stopPlayback = useCallback(() => {
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (err) {
        // Source may already be stopped
      }
      currentSourceRef.current = null;
    }
    setState({ playingId: null, error: null });
  }, []);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return [
    state,
    {
      playSample,
      stopPlayback,
      clearError,
    },
  ];
}
