/**
 * Generic WebSocket Events Hook
 *
 * Provides a composable hook for handling WebSocket connections
 * with domain-specific event parsers. This hook manages:
 * - WebSocket connection lifecycle
 * - Authentication token handling
 * - Reconnection logic with exponential backoff
 * - Event buffering and flushing
 * - Domain-specific event parsing
 *
 * Usage:
 *   const transcriptParser = (data: any) => {
 *     if (data.type === "transcript") return parseTranscript(data);
 *     return null;
 *   };
 *
 *   const { events, isConnected } = useWebSocketEvents({
 *     callId,
 *     eventParsers: [transcriptParser, voiceEventParser],
 *   });
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

export type WebSocketEventHandler = (data: any) => any | null;

interface UseWebSocketEventsOptions {
  callId: number | null;
  eventParsers: WebSocketEventHandler[];
  buildWsUrl?: (callId: number) => string;
}

interface UseWebSocketEventsResult<T = any> {
  events: T[];
  isConnected: boolean;
  error: string | null;
  connectionState: "connecting" | "connected" | "disconnected" | "error";
}

function buildDefaultWsUrl(callId: number): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const wsProtocol = apiUrl.startsWith("https") ? "wss" : "ws";
  const base = apiUrl.replace(/^https?/, wsProtocol);
  return `${base}/ws/calls/${callId}/transcript`;
}

export function useWebSocketEvents<T = any>({
  callId,
  eventParsers,
  buildWsUrl = buildDefaultWsUrl,
}: UseWebSocketEventsOptions): UseWebSocketEventsResult<T> {
  const [events, setEvents] = useState<T[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<"connecting" | "connected" | "disconnected" | "error">("disconnected");

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const eventBufferRef = useRef<T[]>([]);
  const currentCallIdRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);

  const { getToken } = useAuth();

  const flushBuffer = useCallback(() => {
    if (eventBufferRef.current.length > 0) {
      const buffered = eventBufferRef.current;
      eventBufferRef.current = [];
      setEvents((prev) => [...prev, ...buffered]);
    }
  }, []);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const processMessage = useCallback((data: any) => {
    // Try each parser in sequence
    for (const parser of eventParsers) {
      try {
        const parsed = parser(data);
        if (parsed !== null) {
          eventBufferRef.current.push(parsed);
          flushBuffer();
          return; // Successfully parsed by this handler
        }
      } catch (err) {
        console.warn("[useWebSocketEvents] Parser error:", err);
      }
    }
  }, [eventParsers, flushBuffer]);

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
      setEvents([]);
      setConnectionState("disconnected");
      eventBufferRef.current = [];
      return;
    }

    setConnectionState("connecting");
    cancelledRef.current = false;

    const activeCallId = callId;

    async function connect() {
      const token = await getToken();
      if (!token || cancelledRef.current) {
        if (!cancelledRef.current) {
          setError("Not authenticated");
          setConnectionState("error");
        }
        return;
      }

      const url = buildWsUrl(activeCallId);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelledRef.current) {
          ws.close();
          return;
        }
        ws.send(JSON.stringify({ token }));
        setIsConnected(true);
        setConnectionState("connected");
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (cancelledRef.current) return;
        try {
          const data = JSON.parse(event.data);
          processMessage(data);
        } catch (error) {
          console.warn("[useWebSocketEvents] Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = () => {
        if (!cancelledRef.current) {
          setError("WebSocket connection error");
          setConnectionState("error");
        }
      };

      ws.onclose = (event) => {
        if (cancelledRef.current) return;
        setIsConnected(false);
        setConnectionState("disconnected");
        wsRef.current = null;

        if (event.code === 1008) {
          setError("Authentication failed");
          setConnectionState("error");
          return;
        }

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const attempt = reconnectAttemptsRef.current;
          const delay = Math.min(
            BASE_RECONNECT_DELAY_MS * Math.pow(2, attempt),
            MAX_RECONNECT_DELAY_MS,
          );
          reconnectAttemptsRef.current += 1;
          setConnectionState("connecting");
          reconnectTimerRef.current = setTimeout(() => {
            if (!cancelledRef.current && currentCallIdRef.current === callId) {
              connect();
            }
          }, delay);
        }
      };
    }

    connect();

    return () => {
      cancelledRef.current = true;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      clearReconnectTimer();
    };
  }, [callId, getToken, buildWsUrl, processMessage, clearReconnectTimer]);

  return { events, isConnected, error, connectionState };
}

/**
 * Higher-order function to create domain-specific event parsers
 *
 * Example:
 *   const transcriptParser = createEventParser((data) => {
 *     if (data.type === "transcript") return parseTranscript(data.entry);
 *     return null;
 *   });
 */
export function createEventParser<T>(
  parserFn: (data: any) => T | null
): WebSocketEventHandler {
  return parserFn;
}
