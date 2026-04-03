"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { TranscriptEntry, VoiceEventType } from "@call/types";
import {
  VOLUME_SPEAKING,
  VOLUME_IDLE,
  VOLUME_DECAY_RATE,
  VOLUME_THRESHOLD,
  RIPPLE_DURATION_MS,
  INTERRUPTION_RESET_MS,
  DECAY_INTERVAL_MS,
} from "@call/constants";

interface UseVoiceEventsResult {
  volume: number;
  sentiment: number;
  isActive: boolean;
  lastInterruptionAt?: Date;
}

/**
 * Hook to detect voice events from transcript entries
 * Extends useTranscriptStream pattern for voice activity detection
 *
 * @param entries - Transcript entries to parse for voice events
 * @returns Voice activity state (volume, sentiment, isActive, lastInterruptionAt)
 */
export function useVoiceEvents(
  entries: TranscriptEntry[],
): UseVoiceEventsResult {
  const [volume, setVolume] = useState(VOLUME_IDLE);
  const [sentiment] = useState(0.5); // MVP: always neutral
  const [isActive, setIsActive] = useState(false);
  const [lastInterruptionAt, setLastInterruptionAt] = useState<Date | undefined>(
    undefined,
  );

  // Consolidated timer management - single ref for all timers
  const timersRef = useRef<{
    decay: ReturnType<typeof setInterval> | null;
    interruption: ReturnType<typeof setTimeout> | null;
  }>({
    decay: null,
    interruption: null,
  });

  // Unified cleanup function
  const cleanupTimers = useCallback(() => {
    if (timersRef.current.decay) {
      clearInterval(timersRef.current.decay);
      timersRef.current.decay = null;
    }
    if (timersRef.current.interruption) {
      clearTimeout(timersRef.current.interruption);
      timersRef.current.interruption = null;
    }
  }, []);

  // Parse transcript entries for voice events
  useEffect(() => {
    if (entries.length === 0) return;

    // Process latest entry
    const latestEntry = entries[entries.length - 1];
    const eventType = latestEntry.event_type;

    if (eventType === "speech-start") {
      setVolume(VOLUME_SPEAKING);
      setIsActive(true);
    } else if (eventType === "speech-end") {
      setIsActive(false);
    } else if (eventType === "interruption") {
      const interruptionTime = new Date();
      setLastInterruptionAt(interruptionTime);

      // Auto-reset interruption flag after threshold
      cleanupTimers();
      timersRef.current.interruption = setTimeout(() => {
        setLastInterruptionAt(undefined);
      }, INTERRUPTION_RESET_MS);
    }
  }, [entries, cleanupTimers]);

  // Exponential decay when inactive
  useEffect(() => {
    cleanupTimers();

    if (isActive) {
      // Clear decay timer when active
      return;
    }

    // Start decay when inactive
    timersRef.current.decay = setInterval(() => {
      setVolume((v) => {
        const newVolume = v * VOLUME_DECAY_RATE;
        // Stop decaying when very close to zero
        return newVolume < 0.01 ? VOLUME_IDLE : newVolume;
      });
    }, DECAY_INTERVAL_MS);

    return cleanupTimers;
  }, [isActive, cleanupTimers]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanupTimers;
  }, [cleanupTimers]);

  return {
    volume,
    sentiment,
    isActive,
    lastInterruptionAt,
  };
}

/**
 * Hook to integrate useTranscriptStream with voice event detection
 * This hook subscribes to transcript entries and detects voice events
 *
 * @param entries - Transcript entries from useTranscriptStream
 * @param callId - Current call ID for filtering
 * @returns Enhanced entries with voice event types
 */
export function useVoiceEventDetector(
  entries: TranscriptEntry[],
  callId: number | null,
): TranscriptEntry[] {
  const lastEntryRef = useRef<TranscriptEntry | null>(null);
  const speechStartTimeRef = useRef<number | null>(null);

  return entries.map((entry) => {
    // Skip if entry doesn't match current call
    if (callId !== null && entry.callId !== callId) {
      return entry;
    }

    // Detect speech-start: new transcript entry from lead
    const isSpeechStart =
      entry.role === "lead" &&
      (!lastEntryRef.current || lastEntryRef.current.role !== "lead");

    // Detect speech-end: no lead entries for 500ms
    const isSpeechEnd = false; // Will be detected by timeout

    // Detect interruption: rapid speaker changes
    const isInterruption =
      lastEntryRef.current &&
      lastEntryRef.current.role === "assistant-ai" &&
      entry.role === "lead" &&
      entry.startTime - lastEntryRef.current.endTime < 200;

    let eventType: VoiceEventType | undefined;

    if (isInterruption) {
      eventType = "interruption";
    } else if (isSpeechStart) {
      eventType = "speech-start";
      speechStartTimeRef.current = entry.startTime;
    }

    lastEntryRef.current = entry;

    return {
      ...entry,
      event_type: eventType,
    };
  });
}
