"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import type { TranscriptEntry } from "@call/types";

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

interface UseTranscriptStreamResult {
  entries: TranscriptEntry[];
  isConnected: boolean;
  error: string | null;
  voiceEvents: TranscriptEntry[];
}

function buildWsUrl(callId: number): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const wsProtocol = apiUrl.startsWith("https") ? "wss" : "ws";
  const base = apiUrl.replace(/^https?/, wsProtocol);
  return `${base}/ws/calls/${callId}/transcript`;
}

export function useTranscriptStream(
  callId: number | null,
): UseTranscriptStreamResult {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [voiceEvents, setVoiceEvents] = useState<TranscriptEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const entriesBufferRef = useRef<TranscriptEntry[]>([]);
  const voiceEventsBufferRef = useRef<TranscriptEntry[]>([]);
  const currentCallIdRef = useRef<number | null>(null);

  const { getToken } = useAuth();

  const flushBuffer = useCallback(() => {
    if (entriesBufferRef.current.length > 0) {
      const buffered = entriesBufferRef.current;
      entriesBufferRef.current = [];
      setEntries((prev) => [...prev, ...buffered]);
    }
    if (voiceEventsBufferRef.current.length > 0) {
      const buffered = voiceEventsBufferRef.current;
      voiceEventsBufferRef.current = [];
      setVoiceEvents((prev) => [...prev, ...buffered]);
    }
  }, []);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (currentCallIdRef.current !== callId) {
      clearReconnectTimer();
      reconnectAttemptsRef.current = 0;
      currentCallIdRef.current = callId;
    }
  }, [callId, clearReconnectTimer]);

  useEffect(() => {
    if (!callId) {
      setIsConnected(false);
      setError(null);
      setEntries([]);
      setVoiceEvents([]);
      entriesBufferRef.current = [];
      voiceEventsBufferRef.current = [];
      return;
    }

    let cancelled = false;

    const activeCallId = callId;

    async function connect() {
      const token = await getToken();
      if (!token || cancelled) {
        if (!cancelled) {
          setError("Not authenticated");
        }
        return;
      }

      const url = buildWsUrl(activeCallId);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) {
          ws.close();
          return;
        }
        ws.send(JSON.stringify({ token }));
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(event.data);

          // Handle transcript entries
          if (data.type === "transcript" && data.entry) {
            entriesBufferRef.current.push(data.entry);
            flushBuffer();
          }

          // Handle voice state events from backend
          if (data.type === "speech_state" && data.state) {
            // Create a synthetic entry for voice events
            const voiceEntry: TranscriptEntry = {
              id: Date.now(),
              callId: activeCallId,
              role: "lead", // Voice events are always from lead perspective
              text: "",
              startTime: 0,
              endTime: 0,
              confidence: null,
              receivedAt: new Date().toISOString(),
              timestamp: Date.now(),
              event_type: data.state.event_type,
            };
            voiceEventsBufferRef.current.push(voiceEntry);
            flushBuffer();
          }
        } catch (error) {
          // Log malformed JSON but don't crash
          console.warn("[useTranscriptStream] Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = () => {
        if (!cancelled) {
          setError("WebSocket connection error");
        }
      };

      ws.onclose = (event) => {
        if (cancelled) return;
        setIsConnected(false);
        wsRef.current = null;

        if (event.code === 1008) {
          setError("Authentication failed");
          return;
        }

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const attempt = reconnectAttemptsRef.current;
          const delay = Math.min(
            BASE_RECONNECT_DELAY_MS * Math.pow(2, attempt),
            MAX_RECONNECT_DELAY_MS,
          );
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            if (!cancelled && currentCallIdRef.current === callId) {
              connect();
            }
          }, delay);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      clearReconnectTimer();
    };
  }, [callId, getToken, flushBuffer, clearReconnectTimer]);

  return { entries, isConnected, error, voiceEvents };
}
