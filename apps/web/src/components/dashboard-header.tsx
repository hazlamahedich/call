"use client";

import { useBranding } from "@/lib/branding-context";

export function DashboardHeader() {
  const { logoUrl, brandName, loaded } = useBranding();

  if (!loaded) {
    return (
      <header className="flex h-12 items-center border-b border-border px-md">
        <span className="text-sm font-medium text-muted-foreground">Call</span>
      </header>
    );
  }

  return (
    <header className="flex h-12 items-center border-b border-border px-md">
      {logoUrl ? (
        <img
          src={logoUrl}
          alt={brandName || "Brand logo"}
          className="max-h-[28px] max-w-[100px] object-contain"
        />
      ) : (
        <span className="text-sm font-semibold text-foreground">
          {brandName || "Call"}
        </span>
      )}
    </header>
  );
}
