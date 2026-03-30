"use client";

import { BrandingProvider } from "@/lib/branding-context";
import { DashboardHeader } from "@/components/dashboard-header";
import { OnboardingGuard } from "@/components/onboarding-guard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <BrandingProvider>
      <OnboardingGuard>
        <div className="flex min-h-screen flex-col">
          <DashboardHeader />
          <main className="flex-1">{children}</main>
        </div>
      </OnboardingGuard>
    </BrandingProvider>
  );
}
