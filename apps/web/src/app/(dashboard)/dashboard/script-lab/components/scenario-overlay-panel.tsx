"use client";

import { useState, useCallback } from "react";
import { setScenarioOverlay } from "@/actions/scripts-lab";

interface ScenarioOverlayPanelProps {
  sessionId: number;
}

interface OverrideEntry {
  key: string;
  value: string;
}

export function ScenarioOverlayPanel({ sessionId }: ScenarioOverlayPanelProps) {
  const [entries, setEntries] = useState<OverrideEntry[]>([
    { key: "", value: "" },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCount, setActiveCount] = useState(0);

  const updateEntry = useCallback(
    (index: number, field: "key" | "value", val: string) => {
      setEntries((prev) => {
        const next = [...prev];
        next[index] = { ...next[index], [field]: val };
        return next;
      });
    },
    [],
  );

  const addEntry = useCallback(() => {
    setEntries((prev) => [...prev, { key: "", value: "" }]);
  }, []);

  const removeEntry = useCallback((index: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const validateEntries = (entries: OverrideEntry[]): string | null => {
    for (const entry of entries) {
      const trimmedKey = entry.key.trim();
      if (trimmedKey === "" && entry.value.trim() === "") continue;
      if (trimmedKey === "") return "Variable name cannot be empty";
      if (trimmedKey.includes("{{") || trimmedKey.includes("}}")) {
        return `Variable name "${trimmedKey}" contains invalid characters`;
      }
    }
    return null;
  };

  const handleSave = useCallback(async () => {
    const validationError = validateEntries(entries);
    if (validationError) {
      setError(validationError);
      return;
    }

    const overlay: Record<string, string> = {};
    let count = 0;
    for (const entry of entries) {
      const trimmedKey = entry.key.trim();
      if (trimmedKey && entry.value.trim()) {
        overlay[trimmedKey] = entry.value.trim();
        count++;
      }
    }

    if (count === 0) {
      setError("At least one variable override is required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const result = await setScenarioOverlay(sessionId, overlay);
      if (result.error) {
        setError(result.error);
        return;
      }
      setActiveCount(count);
    } catch {
      setError("Failed to save overlay");
    } finally {
      setSaving(false);
    }
  }, [entries, sessionId]);

  return (
    <div className="scenario-overlay-panel">
      <h3 className="scenario-overlay-title">
        Variable Overrides
        {activeCount > 0 && (
          <span className="active-badge">{activeCount} active</span>
        )}
      </h3>

      <div className="scenario-overlay-entries">
        {entries.map((entry, i) => (
          <div key={i} className="scenario-overlay-entry">
            <input
              type="text"
              placeholder="Variable name"
              value={entry.key}
              onChange={(e) => updateEntry(i, "key", e.target.value)}
              className="overlay-input overlay-input--key"
            />
            <span className="overlay-equals">=</span>
            <input
              type="text"
              placeholder="Value"
              value={entry.value}
              onChange={(e) => updateEntry(i, "value", e.target.value)}
              className="overlay-input overlay-input--value"
            />
            {entries.length > 1 && (
              <button
                onClick={() => removeEntry(i)}
                className="overlay-remove-btn"
                aria-label="Remove override"
                type="button"
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="scenario-overlay-actions">
        <button onClick={addEntry} type="button" className="overlay-add-btn">
          + Add Variable
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          type="button"
          className="overlay-save-btn"
        >
          {saving ? "Saving..." : "Apply Overrides"}
        </button>
      </div>

      {error && <div className="scenario-overlay-error">{error}</div>}
    </div>
  );
}
