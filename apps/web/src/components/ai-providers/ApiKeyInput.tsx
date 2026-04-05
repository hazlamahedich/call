"use client";

import { useState } from "react";

interface ApiKeyInputProps {
  value: string;
  hasExistingKey: boolean;
  onChange: (value: string) => void;
}

export function ApiKeyInput({
  value,
  hasExistingKey,
  onChange,
}: ApiKeyInputProps) {
  const [showKey, setShowKey] = useState(false);

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-foreground">API Key</label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={showKey ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={
              hasExistingKey
                ? "Key stored (enter new to replace)"
                : "sk-... or AIza..."
            }
            className="w-full rounded-md border border-border bg-card px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground"
          >
            {showKey ? "Hide" : "Show"}
          </button>
        </div>
      </div>
    </div>
  );
}
