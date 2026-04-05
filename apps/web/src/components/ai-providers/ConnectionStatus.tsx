"use client";

interface ConnectionStatusProps {
  status: "connected" | "disconnected" | "untested";
  testing: boolean;
}

export function ConnectionStatus({ status, testing }: ConnectionStatusProps) {
  if (testing) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <div className="size-3 animate-spin rounded-full border-2 border-border border-t-emerald-500" />
        Testing connection...
      </div>
    );
  }

  const config = {
    connected: { color: "text-emerald-500", label: "Connected" },
    disconnected: { color: "text-red-500", label: "Connection failed" },
    untested: { color: "text-muted-foreground", label: "Not tested" },
  };

  const { color, label } = config[status];

  return (
    <div className={`flex items-center gap-2 text-sm ${color}`}>
      <div
        className={`size-2 rounded-full ${
          status === "connected"
            ? "bg-emerald-500"
            : status === "disconnected"
              ? "bg-red-500"
              : "bg-muted-foreground/30"
        }`}
      />
      {label}
    </div>
  );
}
