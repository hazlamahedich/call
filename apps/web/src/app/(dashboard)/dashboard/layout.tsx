"use client";

import { BrandingProvider } from "@/lib/branding-context";
import { DashboardHeader } from "@/components/dashboard-header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <BrandingProvider>
      <div className="flex min-h-screen flex-col">
        <DashboardHeader />
        <main className="flex-1">{children}</main>
      </div>
    </BrandingProvider>
  );
}
