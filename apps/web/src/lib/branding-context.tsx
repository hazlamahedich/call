"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useOrganization } from "@clerk/nextjs";
import { getBranding } from "@/actions/branding";

type BrandingContextType = {
  primaryColor: string;
  primaryColorRgb: string;
  logoUrl: string | null;
  brandName: string | null;
  loaded: boolean;
};

const BRAND_DEFAULTS: BrandingContextType = {
  primaryColor: "#10B981",
  primaryColorRgb: "16,185,129",
  logoUrl: null,
  brandName: null,
  loaded: false,
};

function hexToRgb(hex: string): string {
  const result = hex.match(/\w\w/g);
  if (!result) return "16,185,129";
  return result.map((x) => parseInt(x, 16)).join(",");
}

const BrandingContext = createContext<BrandingContextType>(BRAND_DEFAULTS);

export function BrandingProvider({ children }: { children: ReactNode }) {
  const { organization } = useOrganization();
  const [branding, setBranding] = useState<BrandingContextType>(BRAND_DEFAULTS);

  const applyBranding = useCallback((data: BrandingContextType) => {
    const rgb = hexToRgb(data.primaryColor);
    document.documentElement.style.setProperty(
      "--brand-primary",
      data.primaryColor,
    );
    document.documentElement.style.setProperty("--brand-primary-rgb", rgb);
    setBranding({ ...data, primaryColorRgb: rgb, loaded: true });
  }, []);

  useEffect(() => {
    if (!organization) return;

    const cacheKey = `branding_${organization.id}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < 60_000) {
          applyBranding({ ...BRAND_DEFAULTS, ...data, loaded: true });
          return;
        }
      } catch {
        sessionStorage.removeItem(cacheKey);
      }
    }

    getBranding(organization.id).then(({ data }) => {
      if (data) {
        const fullData: BrandingContextType = {
          primaryColor: data.primaryColor,
          primaryColorRgb: hexToRgb(data.primaryColor),
          logoUrl: data.logoUrl,
          brandName: data.brandName,
          loaded: true,
        };
        applyBranding(fullData);
        sessionStorage.setItem(
          cacheKey,
          JSON.stringify({
            data: {
              primaryColor: data.primaryColor,
              logoUrl: data.logoUrl,
              brandName: data.brandName,
            },
            timestamp: Date.now(),
          }),
        );
      } else {
        setBranding((prev) => ({ ...prev, loaded: true }));
      }
    });
  }, [organization, applyBranding]);

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
}

export const useBranding = () => useContext(BrandingContext);
