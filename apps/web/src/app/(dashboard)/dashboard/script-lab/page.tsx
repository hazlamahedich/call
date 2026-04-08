"use client";

import { useState, useCallback } from "react";
import {
  createLabSession,
  deleteLabSession,
  type LabSession,
} from "@/actions/scripts-lab";
import { ChatPanel } from "./components/chat-panel";
import { ScenarioOverlayPanel } from "./components/scenario-overlay-panel";

export default function ScriptLabPage() {
  const [agentId, setAgentId] = useState("");
  const [scriptId, setScriptId] = useState("");
  const [session, setSession] = useState<LabSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreate = useCallback(async () => {
    const aid = parseInt(agentId, 10);
    const sid = parseInt(scriptId, 10);
    if (isNaN(aid) || isNaN(sid)) {
      setError("Valid Agent ID and Script ID are required");
      return;
    }

    setCreating(true);
    setError(null);

    const result = await createLabSession(aid, sid);
    if (result.error) {
      setError(result.error);
      setCreating(false);
      return;
    }
    if (result.data) {
      setSession(result.data);
    }
    setCreating(false);
  }, [agentId, scriptId]);

  const handleDelete = useCallback(async () => {
    if (!session) return;
    const result = await deleteLabSession(session.sessionId);
    if (result.error) {
      setError(result.error);
      return;
    }
    setSession(null);
  }, [session]);

  if (!session) {
    return (
      <div className="script-lab-setup">
        <h1 className="script-lab-title">Script Lab</h1>
        <p className="script-lab-subtitle">
          Test your scripts in a sandbox environment with source attribution
        </p>

        <div className="script-lab-form">
          <div className="form-field">
            <label htmlFor="agent-id">Agent ID</label>
            <input
              id="agent-id"
              type="number"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              placeholder="Enter agent ID"
              className="form-input"
            />
          </div>

          <div className="form-field">
            <label htmlFor="script-id">Script ID</label>
            <input
              id="script-id"
              type="number"
              value={scriptId}
              onChange={(e) => setScriptId(e.target.value)}
              placeholder="Enter script ID"
              className="form-input"
            />
          </div>

          <button
            onClick={handleCreate}
            disabled={creating || !agentId || !scriptId}
            className="btn-primary"
          >
            {creating ? "Creating Session..." : "Start Lab Session"}
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}
      </div>
    );
  }

  return (
    <div className="script-lab-active">
      <header className="script-lab-header">
        <h1>Script Lab</h1>
        <div className="session-meta">
          <span>Session #{session.sessionId}</span>
          <span>Status: {session.status}</span>
          <span>
            Expires: {new Date(session.expiresAt).toLocaleTimeString()}
          </span>
          <button onClick={handleDelete} className="btn-danger">
            End Session
          </button>
        </div>
      </header>

      <div className="script-lab-layout">
        <main className="script-lab-main">
          <ChatPanel sessionId={session.sessionId} />
        </main>
        <aside className="script-lab-sidebar">
          <ScenarioOverlayPanel sessionId={session.sessionId} />
        </aside>
      </div>

      {error && <div className="form-error">{error}</div>}
    </div>
  );
}
