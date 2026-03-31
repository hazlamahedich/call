"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import type { TranscriptEntry } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");
const RECONNECT_BASE_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;

interface UseTranscriptStreamResult {
  entries: TranscriptEntry[];
  isConnected: boolean;
  error: string | null;
}

export function useTranscriptStream(
  callId: number | null,
): UseTranscriptStreamResult {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const entriesBuffer = useRef<TranscriptEntry[]>([]);
  const { getToken } = useAuth();

  const connect = useCallback(async () => {
    if (!callId) return;

    try {
      const token = await getToken();
      if (!token) {
        setError("Not authenticated");
        return;
      }

      const url = `${WS_URL}/ws/calls/${callId}/transcript?token=${token}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "transcript" && data.entry) {
            const entry: TranscriptEntry = {
              id: data.entry.id,
              callId: data.entry.callId,
              role: data.entry.role,
              text: data.entry.text,
              startTime: data.entry.startTime,
              endTime: data.entry.endTime,
              confidence: data.entry.confidence ?? null,
              receivedAt: data.entry.receivedAt ?? new Date().toISOString(),
              timestamp: data.entry.startTime ?? Date.now() / 1000,
            };
            entriesBuffer.current = [...entriesBuffer.current, entry];
            setEntries([...entriesBuffer.current]);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        setError("WebSocket connection error");
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        if (event.code !== 1008 && callId) {
          const delay = Math.min(
            RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttempts.current),
            MAX_RECONNECT_DELAY,
          );
          reconnectAttempts.current += 1;
          setTimeout(() => connect(), delay);
        }
      };
    } catch (e) {
      setError((e as Error).message);
    }
  }, [callId, getToken]);

  useEffect(() => {
    entriesBuffer.current = [];
    setEntries([]);
    setError(null);
    setIsConnected(false);
    reconnectAttempts.current = 0;

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { entries, isConnected, error };
}
