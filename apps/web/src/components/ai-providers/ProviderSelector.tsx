"use client";

import type { AIProvider } from "@call/types";

interface ProviderSelectorProps {
  value: AIProvider;
  onChange: (provider: AIProvider) => void;
}

const providers: { id: AIProvider; name: string; description: string }[] = [
  {
    id: "openai",
    name: "OpenAI",
    description: "GPT-4o, text-embedding-3-small",
  },
  {
    id: "gemini",
    name: "Gemini",
    description: "Gemini 2.0 Flash, gemini-embedding-001",
  },
];

export function ProviderSelector({ value, onChange }: ProviderSelectorProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {providers.map((p) => (
        <button
          key={p.id}
          type="button"
          onClick={() => onChange(p.id)}
          className={`rounded-lg border p-4 text-left transition-all ${
            value === p.id
              ? "border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500"
              : "border-border hover:border-muted-foreground/50"
          }`}
        >
          <div className="flex items-center gap-2">
            <div
              className={`size-3 rounded-full ${
                value === p.id ? "bg-emerald-500" : "bg-muted-foreground/30"
              }`}
            />
            <span className="text-sm font-medium text-foreground">
              {p.name}
            </span>
          </div>
          {value === p.id && (
            <span className="mt-1 block text-xs text-emerald-400">Active</span>
          )}
          <p className="mt-2 text-xs text-muted-foreground">{p.description}</p>
        </button>
      ))}
    </div>
  );
}
