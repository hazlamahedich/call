"use client";

import { useRef, useEffect } from "react";
import { useTranscriptStream } from "@/hooks/useTranscriptStream";
import type { TranscriptEntry } from "@call/types";

interface TelemetryStreamProps {
  callId: number | null;
}

const ROLE_STYLES: Record<string, { color: string; prefix: string }> = {
  "assistant-ai": { color: "#10b981", prefix: "[AI]" },
  "assistant-human": { color: "#3b82f6", prefix: "[Human]" },
  lead: { color: "#a1a1aa", prefix: "[Lead]" },
};

export function TelemetryStream({ callId }: TelemetryStreamProps) {
  const { entries, isConnected, error } = useTranscriptStream(callId);
  const containerRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useRef(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      prefersReducedMotion.current = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
    }
  }, []);

  useEffect(() => {
    if (containerRef.current && !prefersReducedMotion.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [entries]);

  if (!callId) {
    return null;
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 12px",
          borderBottom: "1px solid #27272a",
          fontFamily: "var(--font-geist-mono, monospace)",
          fontSize: "13px",
        }}
      >
        <span style={{ color: "#a1a1aa" }}>Live Transcript</span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            color: isConnected ? "#10b981" : "#ef4444",
            fontSize: "12px",
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: isConnected ? "#10b981" : "#ef4444",
            }}
          />
          {isConnected ? "Connected" : "Disconnected"}
        </span>
      </div>

      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px 12px",
          fontFamily: "var(--font-geist-mono, monospace)",
          fontSize: "13px",
          lineHeight: "1.6",
        }}
      >
        {entries.length === 0 && !error && (
          <span style={{ color: "#71717a" }}>
            Waiting for transcript data...
          </span>
        )}

        {error && (
          <div role="alert" style={{ color: "#ef4444", fontSize: "12px" }}>
            {error}
          </div>
        )}

        {entries.map((entry: TranscriptEntry) => {
          const style = ROLE_STYLES[entry.role] || ROLE_STYLES["lead"];
          return (
            <div key={entry.id} style={{ marginBottom: "4px" }}>
              <span style={{ color: "#71717a", marginRight: "6px" }}>
                {style.prefix}
              </span>
              <span style={{ color: style.color }}>{entry.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
