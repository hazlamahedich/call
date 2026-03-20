import { cn } from "@/lib/utils"
import { Users, Phone, Zap, ShieldCheck } from "lucide-react"

interface FleetNavigatorProps {
  className?: string
}

export function FleetNavigator({ className }: FleetNavigatorProps) {
  const agents = [
    { id: "agent-1", name: "PHOENIX-01", status: "Active", callCount: 124 },
    { id: "agent-2", name: "TITAN-04", status: "Active", callCount: 89 },
    { id: "agent-3", name: "SHADOW-09", status: "Standby", callCount: 210 },
  ]

  return (
    <aside className={cn("flex flex-col bg-card border-r border-border w-70 h-full", className)}>
      <div className="p-lg">
        <h2 className="text-xs font-bold text-muted-foreground tracking-widest uppercase">
          Fleet Navigator
        </h2>
      </div>

      <nav className="flex-1 overflow-y-auto px-md">
        <div className="space-y-sm">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="group flex flex-col p-sm rounded-md hover:bg-muted transition-colors cursor-pointer border border-transparent hover:border-border"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-mono font-bold tracking-tight">
                  {agent.name}
                </span>
                <span
                  className={cn(
                    "size-2 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)]",
                    agent.status === "Active" ? "bg-neon-emerald" : "bg-muted-foreground"
                  )}
                />
              </div>
              <div className="flex items-center justify-between mt-xs">
                <span className="text-[10px] text-muted-foreground uppercase flex items-center gap-1 font-sans">
                  <Phone className="size-3" /> {agent.callCount} Calls
                </span>
                <span className="text-[10px] text-muted-foreground uppercase font-sans">
                  {agent.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </nav>

      <div className="p-md border-t border-border mt-auto">
        <div className="bg-background/50 rounded-lg p-sm border border-border/50">
          <div className="flex items-center gap-2 mb-xs">
            <Zap className="size-3 text-neon-blue" />
            <span className="text-[10px] font-bold text-muted-foreground tracking-wider uppercase">
              System Health
            </span>
          </div>
          <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-neon-blue w-[94%]" />
          </div>
        </div>
      </div>
    </aside>
  )
}
