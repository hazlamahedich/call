"use client"

import { useState } from "react"
import { FleetNavigator } from "@/components/command-center/FleetNavigator"
import { TelemetryStream } from "@/components/command-center/TelemetryStream"
import { RejectionShield } from "@/components/command-center/RejectionShield"
import { Search, Bell, Settings, Radio, ShieldCheck, MessageSquare } from "lucide-react"

export default function CommandCenterPage() {
  const [sentiment, setSentiment] = useState<"positive" | "negative" | "neutral">("neutral")

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden text-foreground">
      {/* Top Navigation */}
      <header className="h-16 border-b border-border flex items-center justify-between px-xl shrink-0 bg-background/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="size-6 bg-neon-emerald rounded flex items-center justify-center">
              <Radio className="size-4 text-background" />
            </div>
            <h1 className="text-lg font-bold tracking-tighter uppercase">Titan Cold Caller</h1>
          </div>
          <div className="h-4 w-px bg-border hidden md:block" />
          <nav className="hidden md:flex gap-6">
            <span className="text-sm font-bold text-foreground border-b-2 border-neon-emerald pb-5 pt-1 -mb-1">COMMAND CENTER</span>
            <span className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer pt-1">CAMPAIGNS</span>
            <span className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer pt-1">ANALYTICS</span>
          </nav>
        </div>

        <div className="flex items-center gap-lg">
          <div className="relative group hidden lg:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground group-focus-within:text-foreground transition-colors" />
            <input 
              type="text" 
              placeholder="Search fleet..." 
              className="bg-card/50 border border-border rounded-md px-10 py-1.5 text-sm w-64 focus:outline-none focus:ring-1 focus:ring-ring transition-all placeholder:text-muted-foreground/50"
            />
          </div>
          <div className="flex items-center gap-4">
            <button className="relative p-2 text-muted-foreground hover:text-foreground transition-colors">
              <Bell className="size-4" />
              <span className="absolute top-1.5 right-1.5 size-2 bg-neon-crimson rounded-full border-2 border-background" />
            </button>
            <button className="p-2 text-muted-foreground hover:text-foreground transition-colors">
              <Settings className="size-4" />
            </button>
            <div className="size-8 rounded bg-gradient-to-br from-neon-emerald to-neon-blue border border-white/10" />
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <FleetNavigator className="hidden md:flex shrink-0" />

        {/* Main Telemetry Area */}
        <main className="flex-1 flex flex-col p-lg gap-lg overflow-hidden relative">
          {/* Dashboard Header */}
          <div className="flex items-center justify-between shrink-0">
            <div className="flex flex-col">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-bold text-neon-emerald bg-neon-emerald/10 px-2 py-0.5 rounded border border-neon-emerald/30 uppercase tracking-widest">Live</span>
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Active Call: PHOENIX-01</span>
              </div>
              <h2 className="text-2xl font-black tracking-tight uppercase leading-none">Main Telemetry</h2>
            </div>
            <div className="flex items-center bg-card border border-border p-1 rounded-md">
              <button 
                onClick={() => setSentiment("positive")}
                className={`text-[9px] px-3 py-1 rounded transition-all font-bold uppercase tracking-wider ${sentiment === "positive" ? "bg-neon-emerald text-background" : "text-muted-foreground hover:text-foreground"}`}
              >
                Positive
              </button>
              <button 
                onClick={() => setSentiment("neutral")}
                className={`text-[9px] px-3 py-1 rounded transition-all font-bold uppercase tracking-wider ${sentiment === "neutral" ? "bg-neon-blue text-background" : "text-muted-foreground hover:text-foreground"}`}
              >
                Neutral
              </button>
              <button 
                onClick={() => setSentiment("negative")}
                className={`text-[9px] px-3 py-1 rounded transition-all font-bold uppercase tracking-wider ${sentiment === "negative" ? "bg-neon-crimson text-background" : "text-muted-foreground hover:text-foreground"}`}
              >
                Negative
              </button>
            </div>
          </div>

          {/* Telemetry Stream */}
          <TelemetryStream sentiment={sentiment} className="flex-1 min-h-0" />

          {/* Bottom Grid Overlay Pattern */}
          <div className="absolute inset-0 bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:24px_24px] opacity-20 -z-10 pointer-events-none" />
        </main>

        {/* Right Metrics Panel */}
        <div className="w-80 hidden lg:flex flex-col p-lg border-l border-border gap-lg overflow-y-auto shrink-0 bg-background/50">
          <RejectionShield 
            status={sentiment === "negative" ? "critical" : sentiment === "neutral" ? "alert" : "safe"} 
            rejectionRate={sentiment === "negative" ? 24.8 : 12.4}
          />
          
          <div className="bg-card border border-border rounded-lg p-md">
            <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-md">Quick Actions</h4>
            <div className="grid grid-cols-2 gap-sm">
              <button className="flex flex-col items-center justify-center gap-2 p-sm bg-background/50 border border-border rounded hover:bg-muted hover:border-neon-emerald/30 transition-all group">
                <ShieldCheck className="size-4 text-muted-foreground group-hover:text-neon-emerald" />
                <span className="text-[9px] font-bold uppercase text-muted-foreground group-hover:text-foreground">Verify Compliance</span>
              </button>
              <button className="flex flex-col items-center justify-center gap-2 p-sm bg-background/50 border border-border rounded hover:bg-muted hover:border-neon-blue/30 transition-all group">
                <MessageSquare className="size-4 text-muted-foreground group-hover:text-neon-blue" />
                <span className="text-[9px] font-bold uppercase text-muted-foreground group-hover:text-foreground">Send Prompt</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
