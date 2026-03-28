"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { TranscriptEntry } from "@call/types";

export interface TelemetryStreamObsidianProps extends React.HTMLAttributes<HTMLDivElement> {
  entries: TranscriptEntry[];
  onScrollBottom?: () => void;
  reducedMotion?: boolean;
}

const roleColors: Record<string, string> = {
  "assistant-ai": "text-neon-emerald border-neon-emerald/30",
  "assistant-human": "text-neon-blue border-neon-blue/30",
  lead: "text-neon-blue border-neon-blue/30",
};

const roleLabels: Record<string, string> = {
  "assistant-ai": "AI",
  "assistant-human": "HUMAN",
  lead: "LEAD",
};

export function TelemetryStreamObsidian({
  entries,
  onScrollBottom,
  reducedMotion = false,
  className,
  ...props
}: TelemetryStreamObsidianProps) {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
    });
    onScrollBottom?.();
  }, [entries, onScrollBottom, reducedMotion]);

  return (
    <div
      className={cn(
        "flex flex-col bg-card border border-border rounded-lg overflow-hidden h-full",
        "shadow-[0_4px_24px_rgba(0,0,0,0.5)]",
        className,
      )}
      {...props}
    >
      <ScrollArea className="flex-1">
        <div className="font-mono text-sm p-md space-y-md">
          {entries.map((entry) => (
            <div key={entry.id} className="flex gap-sm">
              <span className="text-muted-foreground/50 shrink-0 text-xs pt-0.5">
                {new Date(entry.timestamp).toLocaleTimeString("en-US", {
                  hour12: false,
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
              <div className="flex flex-col flex-1 min-w-0">
                <span
                  className={cn(
                    "inline-block text-[9px] px-1 rounded border w-fit mb-0.5",
                    roleColors[entry.role] ??
                      "text-muted-foreground border-border",
                  )}
                >
                  {roleLabels[entry.role] ?? entry.role.toUpperCase()}
                </span>
                <p className="leading-relaxed text-foreground break-words">
                  {entry.text}
                </p>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
