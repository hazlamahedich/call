"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface BrandingPreviewProps {
  logoUrl: string | null;
  primaryColor: string;
  brandName: string | null;
  reducedMotion?: boolean;
}

export function BrandingPreview({
  logoUrl,
  primaryColor,
  brandName,
  reducedMotion,
}: BrandingPreviewProps) {
  return (
    <Card variant="standard" className="p-0 overflow-hidden">
      <div
        className="flex h-10 items-center gap-sm border-b border-border px-sm"
        style={{
          backgroundColor: "var(--color-obsidian-black, #09090B)",
        }}
      >
        {logoUrl ? (
          <img
            src={logoUrl}
            alt="Logo preview"
            className="max-h-[24px] max-w-[80px] object-contain"
          />
        ) : (
          <span className="text-xs font-medium text-foreground">
            {brandName || "Call"}
          </span>
        )}
        <div className="flex-1" />
        <div
          className="h-4 w-16 rounded-sm"
          style={{ backgroundColor: primaryColor, opacity: 0.3 }}
        />
      </div>
      <div className="flex flex-col gap-xs p-md">
        <p className="text-xs text-muted-foreground">Preview</p>
        <div className="flex items-center gap-sm">
          <Button
            variant="primary"
            size="sm"
            style={
              {
                "--brand-primary": primaryColor,
                backgroundColor: primaryColor,
                boxShadow: `0 0 8px ${primaryColor}66`,
              } as React.CSSProperties
            }
          >
            Primary Action
          </Button>
          <div
            className="h-8 w-px"
            style={{ backgroundColor: primaryColor, opacity: 0.3 }}
          />
          <span className="text-xs" style={{ color: primaryColor }}>
            Accent text
          </span>
        </div>
      </div>
    </Card>
  );
}
