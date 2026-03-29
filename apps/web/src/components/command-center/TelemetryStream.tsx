import { cn } from "@/lib/utils";
import { Activity, Heart, Terminal } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

interface TelemetryStreamProps {
  className?: string;
  sentiment?: "positive" | "hostile" | "neutral";
}

export function TelemetryStream({
  className,
  sentiment = "neutral",
}: TelemetryStreamProps) {
  const logs = [
    {
      time: "10:24:01",
      role: "AI",
      content: "Good morning! Am I speaking with Mr. Henderson?",
      type: "voice",
    },
    {
      time: "10:24:04",
      role: "LEAD",
      content: "Yeah, who's this?",
      type: "voice",
    },
    {
      time: "10:24:06",
      role: "SYS",
      content: "Sentiment Shift: Neutral -> Defensive",
      type: "system",
    },
    {
      time: "10:24:08",
      role: "AI",
      content:
        "This is Alex from Titan Solar. I'm calling about the inquiry you made...",
      type: "voice",
    },
    {
      time: "10:24:12",
      role: "LEAD",
      content: "Not interested. We already have panels.",
      type: "voice",
    },
    {
      time: "10:24:14",
      role: "SYS",
      content: "Objection Detected: Already Owns Product",
      type: "alert",
    },
  ];

  const sentimentColors = {
    positive: "bg-neon-emerald",
    hostile: "bg-neon-crimson",
    neutral: "bg-neon-blue",
  };

  return (
    <Card className={cn("flex flex-col overflow-hidden h-full p-0", className)}>
      <div
        className={cn(
          "h-1 w-full transition-colors duration-500",
          sentimentColors[sentiment],
        )}
      />

      <div className="p-md flex items-center justify-between border-b border-border/50 bg-background/20 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Terminal className="size-4 text-neon-blue" />
          <h3 className="text-xs font-bold font-mono tracking-wider uppercase">
            Live Telemetry
          </h3>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Activity className="size-3 text-neon-emerald opacity-70" />
            <span className="text-[10px] font-mono text-muted-foreground uppercase">
              Ping: 24ms
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Heart
              className={cn(
                "size-3",
                sentiment === "hostile"
                  ? "text-neon-crimson"
                  : "text-neon-emerald",
              )}
            />
            <span className="text-[10px] font-mono text-muted-foreground uppercase">
              Stable
            </span>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="font-mono text-sm p-md space-y-md">
          {logs.map((log, idx) => (
            <div key={idx} className="flex gap-4 group">
              <span className="text-[10px] text-muted-foreground/50 w-16 pt-1 shrink-0">
                {log.time}
              </span>
              <div className="flex flex-col flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={cn(
                      "text-[9px] px-1 rounded border",
                      log.role === "AI"
                        ? "text-neon-emerald border-neon-emerald/30"
                        : log.role === "LEAD"
                          ? "text-neon-blue border-neon-blue/30"
                          : "text-muted-foreground border-border",
                    )}
                  >
                    {log.role}
                  </span>
                  {log.type === "alert" && (
                    <span className="text-[9px] text-neon-crimson font-bold uppercase animate-pulse">
                      Critical
                    </span>
                  )}
                </div>
                <p
                  className={cn(
                    "leading-relaxed",
                    log.role === "SYS"
                      ? "text-muted-foreground italic text-xs"
                      : log.role === "LEAD"
                        ? "text-neon-blue font-medium"
                        : "text-foreground",
                  )}
                >
                  {log.content}
                </p>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      <div className="p-sm bg-background/50 border-t border-border flex items-center gap-3">
        <div className="flex-1 h-10 bg-black/40 rounded border border-border flex items-center px-4">
          <div className="size-1.5 bg-neon-emerald rounded-full animate-ping mr-2" />
          <span className="text-xs text-muted-foreground italic">
            Waiting for input...
          </span>
        </div>
        <Button
          variant="destructive"
          size="sm"
          className="uppercase tracking-widest"
        >
          Intervene
        </Button>
      </div>
    </Card>
  );
}
