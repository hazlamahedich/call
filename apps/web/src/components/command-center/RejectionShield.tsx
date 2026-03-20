import { cn } from "@/lib/utils"
import { Shield, ShieldAlert, ShieldCheck, TrendingDown, TrendingUp, BarChart3 } from "lucide-react"

interface RejectionShieldProps {
  className?: string
  status?: "safe" | "alert" | "critical"
  rejectionRate?: number
}

export function RejectionShield({ className, status = "safe", rejectionRate = 12.4 }: RejectionShieldProps) {
  const stats = [
    { label: "Active Calls", value: "42", trend: "+4", trendDir: "up" },
    { label: "Conversion", value: "8.2%", trend: "-1.2", trendDir: "down" },
    { label: "Sentiment", value: "DECENT", valueColor: "text-neon-blue" },
  ]

  const statusColors = {
    safe: "text-neon-emerald border-neon-emerald/30 bg-neon-emerald/5",
    alert: "text-neon-blue border-neon-blue/30 bg-neon-blue/5",
    critical: "text-neon-crimson border-neon-crimson/30 bg-neon-crimson/5",
  }

  const StatusIcon = status === "safe" ? ShieldCheck : status === "alert" ? Shield : ShieldAlert

  return (
    <div className={cn("bg-card border border-border rounded-lg p-lg space-y-lg shadow-xl", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-muted-foreground tracking-widest uppercase">Rejection Shield</h3>
        <BarChart3 className="size-4 text-muted-foreground/30" />
      </div>

      <div className={cn("flex flex-col items-center justify-center py-xl px-12 border rounded-xl transition-all duration-700", statusColors[status])}>
        <div className="relative">
          <StatusIcon className="size-16 mb-4 drop-shadow-[0_0_15px_rgba(var(--color-primary),0.2)]" />
          <div className="absolute inset-0 bg-current opacity-20 blur-2xl animate-pulse -z-10 rounded-full" />
        </div>
        <span className="text-4xl font-mono font-black tracking-tighter leading-none mb-1">
          {rejectionRate}%
        </span>
        <span className="text-[10px] font-bold uppercase tracking-widest opacity-70">
          Rejection Rate
        </span>
      </div>

      <div className="grid grid-cols-1 gap-md">
        {stats.map((stat, idx) => (
          <div key={idx} className="flex items-center justify-between p-md bg-background/50 rounded-md border border-border">
            <span className="text-xs text-muted-foreground uppercase font-sans tracking-wide">{stat.label}</span>
            <div className="flex items-center gap-2">
              <span className={cn("text-sm font-mono font-bold", stat.valueColor || "text-foreground")}>{stat.value}</span>
              {stat.trend && (
                <div className={cn("flex items-center text-[10px] gap-1", stat.trendDir === "up" ? "text-neon-emerald" : "text-neon-crimson")}>
                  {stat.trendDir === "up" ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
                  {stat.trend}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="pt-md border-t border-border/50">
        <div className="flex justify-between text-[10px] font-bold text-muted-foreground uppercase mb-2">
          <span>Shield Optimization</span>
          <span className="text-neon-emerald">Active</span>
        </div>
        <div className="grid grid-cols-6 gap-sm h-6">
          {[0.8, 0.9, 0.4, 0.7, 0.6, 0.8].map((val, i) => (
            <div key={i} className="bg-muted rounded-t-sm flex flex-col justify-end overflow-hidden">
              <div 
                className={cn("w-full transition-all duration-1000", i === 2 ? "bg-neon-crimson" : "bg-neon-emerald")} 
                style={{ height: `${val * 100}%` }} 
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
