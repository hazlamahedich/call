"use client";

import { useState, useRef, useEffect, useCallback, KeyboardEvent } from "react";
import {
  sendLabChat,
  type LabChatResponse,
  type SourceAttribution,
} from "@/actions/scripts-lab";
import { SourceTooltip } from "./source-tooltip";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sourceAttributions?: SourceAttribution[];
  groundingConfidence?: number;
  lowConfidenceWarning?: boolean;
}

interface ChatPanelProps {
  sessionId: number;
}

export function ChatPanel({ sessionId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.data!.responseText,
            sourceAttributions: result.data!.sourceAttributions,
            groundingConfidence: result.data!.groundingConfidence,
            lowConfidenceWarning: result.data!.lowConfidenceWarning,
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
