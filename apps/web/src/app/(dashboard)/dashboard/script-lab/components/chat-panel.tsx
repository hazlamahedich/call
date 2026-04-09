"use client";

import { useState, useRef, useEffect, useCallback, KeyboardEvent } from "react";
import {
  sendLabChat,
  type LabChatResponse,
  type SourceAttribution,
  type ClaimVerification,
} from "@/actions/scripts-lab";
import { SourceTooltip } from "./source-tooltip";
import { CorrectionBadge } from "./correction-badge";
import { GlitchPip } from "@/components/obsidian";
import { StatusMessage } from "@/components/ui";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sourceAttributions?: SourceAttribution[];
  groundingConfidence?: number;
  lowConfidenceWarning?: boolean;
  wasCorrected?: boolean;
  correctionCount?: number;
  verificationTimedOut?: boolean;
  verifiedClaims?: ClaimVerification[];
}

interface ChatPanelProps {
  sessionId: number;
}

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);
  return reduced;
}

export function ChatPanel({ sessionId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setLoading(true);

    try {
      const result = await sendLabChat(sessionId, trimmed);
      if (result.error) {
        setError(result.error);
        return;
      }
      if (result.data) {
        const d = result.data;
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: d.responseText,
            sourceAttributions: d.sourceAttributions,
            groundingConfidence: d.groundingConfidence,
            lowConfidenceWarning: d.lowConfidenceWarning,
            wasCorrected: d.wasCorrected ?? false,
            correctionCount: d.correctionCount ?? 0,
            verificationTimedOut: d.verificationTimedOut ?? false,
            verifiedClaims: d.verifiedClaims ?? [],
          },
        ]);
      }
    } catch {
      setError("Failed to send message");
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Start testing your script by sending a message.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message chat-message--${msg.role}`}>
            <div className="chat-message-content">
              {msg.content}
              {msg.role === "assistant" && msg.sourceAttributions && (
                <div className="chat-attribution">
                  <SourceTooltip sources={msg.sourceAttributions} />
                  <span className="confidence-badge">
                    {Math.round((msg.groundingConfidence ?? 0) * 100)}%
                  </span>
                  {msg.lowConfidenceWarning && (
                    <span className="low-confidence-badge">Low Confidence</span>
                  )}
                </div>
              )}
              {msg.role === "assistant" && !msg.sourceAttributions && (
                <div className="chat-attribution" />
              )}
              {msg.role === "assistant" && msg.wasCorrected && (
                <CorrectionBadge
                  correctionCount={msg.correctionCount ?? 0}
                  verifiedClaims={msg.verifiedClaims ?? []}
                />
              )}
              {msg.role === "assistant" && msg.verificationTimedOut && (
                <GlitchPip active reducedMotion={reducedMotion} />
              )}
              {msg.role === "assistant" && msg.verificationTimedOut && (
                <StatusMessage variant="warning">
                  Verification timed out — response may contain unverified
                  claims
                </StatusMessage>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-loading">
              <span className="loading-dots">Generating response...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message to test the script..."
          rows={1}
          disabled={loading}
          className="chat-input"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="chat-send-btn"
        >
          Send
        </button>
      </div>
    </div>
  );
}
