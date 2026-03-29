"use client";

import { useState, useEffect, useCallback } from "react";
import { useOrganization } from "@clerk/nextjs";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusMessage } from "@/components/ui/status-message";
import {
  LogoUpload,
  ColorPicker,
  DomainConfig,
  BrandingPreview,
} from "@/components/branding";
import { getBranding, updateBranding, verifyDomain } from "@/actions/branding";
import type { AgencyBranding, DomainVerificationResult } from "@call/types";

export default function BrandingSettingsPage() {
  const { organization } = useOrganization();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [primaryColor, setPrimaryColor] = useState("#10B981");
  const [brandName, setBrandName] = useState<string>("");
  const [customDomain, setCustomDomain] = useState<string | null>(null);
  const [domainVerified, setDomainVerified] = useState(false);
  const [existingId, setExistingId] = useState<number | null>(null);

  useEffect(() => {
    if (!organization) return;
    setLoading(true);
    getBranding(organization.id).then(({ data, error }) => {
      if (data) {
        setExistingId(data.id);
        setLogoUrl(data.logoUrl);
        setPrimaryColor(data.primaryColor);
        setBrandName(data.brandName ?? "");
        setCustomDomain(data.customDomain);
        setDomainVerified(data.domainVerified);
      }
      setLoading(false);
    });
  }, [organization]);

  const handleSave = useCallback(async () => {
    if (!organization) return;
    setSaving(true);
    setMessage(null);

    const updates: Partial<
      Pick<
        AgencyBranding,
        "logoUrl" | "primaryColor" | "customDomain" | "brandName"
      >
    > = {
      logoUrl,
      primaryColor,
      customDomain,
      brandName: brandName || null,
    };

    const { data, error } = await updateBranding(organization.id, updates);
    if (error) {
      setMessage({ type: "error", text: error });
    } else if (data) {
      setExistingId(data.id);
      setLogoUrl(data.logoUrl);
      setPrimaryColor(data.primaryColor);
      setBrandName(data.brandName ?? "");
      setCustomDomain(data.customDomain);
      setDomainVerified(data.domainVerified);
      setMessage({ type: "success", text: "Branding saved successfully" });
      const cacheKey = `branding_${organization.id}`;
      sessionStorage.removeItem(cacheKey);
    }
    setSaving(false);
  }, [organization, logoUrl, primaryColor, brandName, customDomain]);

  const handleVerify = useCallback(
    async (domain: string): Promise<DomainVerificationResult | null> => {
      if (!organization) return null;
      const { data, error } = await verifyDomain(organization.id, domain);
      if (data) {
        setDomainVerified(data.verified);
        return data;
      }
      return null;
    },
    [organization],
  );

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-2 border-border border-t-neon-emerald" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-lg p-lg">
      <div>
        <h1 className="text-lg font-semibold text-foreground">
          Branding Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Customize your agency portal appearance
        </p>
      </div>

      {message && (
        <StatusMessage variant={message.type}>{message.text}</StatusMessage>
      )}

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Logo</CardTitle>
          <CardDescription>
            Upload your agency logo (PNG, JPG, SVG — max 2MB)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LogoUpload currentLogo={logoUrl} onLogoChange={setLogoUrl} />
        </CardContent>
      </Card>

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Colors</CardTitle>
          <CardDescription>Set your brand primary color</CardDescription>
        </CardHeader>
        <CardContent>
          <ColorPicker value={primaryColor} onChange={setPrimaryColor} />
        </CardContent>
      </Card>

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Brand Name</CardTitle>
          <CardDescription>
            Display name shown in the portal header
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Input
            type="text"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="Your Agency Name"
          />
        </CardContent>
      </Card>

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Custom Domain</CardTitle>
          <CardDescription>
            Configure a custom domain for your portal
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DomainConfig
            domain={customDomain}
            verified={domainVerified}
            onVerify={handleVerify}
          />
        </CardContent>
      </Card>

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          <CardDescription>See how your branding will look</CardDescription>
        </CardHeader>
        <CardContent>
          <BrandingPreview
            logoUrl={logoUrl}
            primaryColor={primaryColor}
            brandName={brandName || null}
          />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          variant="primary"
          size="md"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Saving..." : "Save Branding"}
        </Button>
      </div>
    </div>
  );
}
