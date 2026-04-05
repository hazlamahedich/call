"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useOrganization } from "@clerk/nextjs";
import { getUsageSummary } from "@/actions/usage";
import { UsageThresholdAlert } from "@/components/usage/UsageThresholdAlert";
import { Card } from "@/components/ui/card";
import type { UsageSummary } from "@call/types";
import {
  Users,
  Settings,
  BarChart3,
  Palette,
  Building,
  Beaker,
  Mic,
  FileText,
  Phone,
  Activity,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { organization } = useOrganization();
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  useEffect(() => {
    getUsageSummary()
      .then((result) => result.data && setSummary(result.data))
      .catch(() => {});
  }, []);

  if (!organization) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <p className="text-muted-foreground">
          Please select an organization to continue.
        </p>
      </div>
    );
  }

  const implementedActions = [
    {
      title: "Manage Clients",
      description: "Add and manage your client list",
      icon: Users,
      href: "/dashboard/clients",
      color: "bg-neon-emerald",
      status: "✓",
    },
    {
      title: "Configure AI",
      description: "Set up AI providers and models",
      icon: Settings,
      href: "/dashboard/settings/ai-providers",
      color: "bg-neon-blue",
      status: "✓",
    },
    {
      title: "View Usage",
      description: "Check your usage statistics",
      icon: BarChart3,
      href: "/dashboard/usage",
      color: "bg-neon-crimson",
      status: "✓",
    },
    {
      title: "Custom Branding",
      description: "Personalize your brand appearance",
      icon: Palette,
      href: "/dashboard/settings/branding",
      color: "bg-neon-purple",
      status: "✓",
    },
    {
      title: "Organizations",
      description: "Manage your organization settings",
      icon: Building,
      href: "/dashboard/organizations/new",
      color: "bg-neon-orange",
      status: "✓",
    },
    {
      title: "Onboarding",
      description: "Complete your setup wizard",
      icon: Beaker,
      href: "/onboarding",
      color: "bg-neon-teal",
      status: "✓",
    },
  ];

  const backendOnlyActions = [
    {
      title: "Voice Presets",
      description: "TTS voice management (API ready)",
      icon: Mic,
      color: "bg-muted",
      status: "🔧",
    },
    {
      title: "Knowledge Base",
      description: "Document upload & search (API ready)",
      icon: FileText,
      color: "bg-muted",
      status: "🔧",
    },
    {
      title: "Make Calls",
      description: "Trigger outbound calls (API ready)",
      icon: Phone,
      color: "bg-muted",
      status: "🔧",
    },
    {
      title: "Live Telemetry",
      description: "Real-time call metrics (API ready)",
      icon: Activity,
      color: "bg-muted",
      status: "🔧",
    },
  ];

  return (
    <div className="p-lg space-y-lg">
      {summary && summary.threshold !== "ok" && (
        <UsageThresholdAlert threshold={summary.threshold} />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Welcome to your AI Cold Calling platform
          </p>
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-foreground mb-3">
          ✅ Implemented Features
        </h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {implementedActions.map((action) => {
            const Icon = action.icon;
            return (
              <Card
                key={action.href}
                className="p-3 hover:shadow-md transition-all cursor-pointer group border-l-4 border-l-neon-emerald"
                onClick={() => router.push(action.href)}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${action.color} group-hover:opacity-80 transition-opacity`}>
                    <Icon className="size-4 text-background" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-foreground text-sm">
                        {action.title}
                      </h3>
                      <span className="text-xs text-neon-emerald">{action.status}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {action.description}
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-foreground mb-3">
          🔧 Backend Only (Coming Soon)
        </h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {backendOnlyActions.map((action) => {
            const Icon = action.icon;
            return (
              <Card key={action.title} className="p-3 border-l-4 border-l-muted opacity-75">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${action.color}`}>
                    <Icon className="size-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-foreground text-sm">
                        {action.title}
                      </h3>
                      <span className="text-xs text-muted-foreground">{action.status}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {action.description}
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      <Card className="p-4 bg-neon-emerald/5 border-neon-emerald/20">
        <h2 className="font-medium text-foreground text-sm mb-2">🚀 Getting Started</h2>
        <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
          <li>Complete onboarding wizard</li>
          <li>Configure AI provider (OpenAI or Gemini)</li>
          <li>Add your first client</li>
          <li>Customize your branding</li>
          <li>Monitor usage and stay within limits</li>
        </ol>
        <p className="text-xs text-muted-foreground mt-2">
          Voice, Knowledge Base, and Calling features are available via API
        </p>
      </Card>
    </div>
  );
}
