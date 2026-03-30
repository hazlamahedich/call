"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
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
  refreshBranding: () => void;
};

const BRAND_DEFAULTS: Omit<BrandingContextType, "refreshBranding"> = {
  primaryColor: "#10B981",
  primaryColorRgb: "16,185,129",
  logoUrl: null,
  brandName: null,
  loaded: false,
};

const HEX_RGB_RE = /^#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/;

function hexToRgb(hex: string): string {
  const match = HEX_RGB_RE.exec(hex);
  if (!match) return "16,185,129";
  return `${parseInt(match[1], 16)},${parseInt(match[2], 16)},${parseInt(match[3], 16)}`;
}

const CACHE_TTL_MS = 60_000;
const BROADCAST_CHANNEL = "branding-updated";

const BrandedContext = createContext<BrandingContextType>({
  ...BRAND_DEFAULTS,
  refreshBranding: () => {},
});

export function BrandingProvider({ children }: { children: ReactNode }) {
  const { organization } = useOrganization();
  const [branding, setBranding] =
    useState<Omit<BrandingContextType, "refreshBranding">>(BRAND_DEFAULTS);
  const [refreshKey, setRefreshKey] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const channelRef = useRef<BroadcastChannel | null>(null);

  const applyBranding = useCallback(
    (data: Omit<BrandingContextType, "refreshBranding">) => {
      const rgb = hexToRgb(data.primaryColor);
      document.documentElement.style.setProperty(
        "--brand-primary",
        data.primaryColor,
      );
      document.documentElement.style.setProperty("--brand-primary-rgb", rgb);
      setBranding({ ...data, primaryColorRgb: rgb, loaded: true });
    },
    [],
  );

  const invalidateCache = useCallback((orgId: string) => {
    try {
      sessionStorage.removeItem(`branding_${orgId}`);
    } catch {
      // storage unavailable
    }
  }, []);

  const refreshBranding = useCallback(() => {
    setBranding((prev) => ({ ...prev, loaded: false }));
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !organization) return;

    const channel = new BroadcastChannel(BROADCAST_CHANNEL);
    channelRef.current = channel;

    channel.onmessage = (event) => {
      if (
        event.data?.type === "branding-changed" &&
        event.data?.orgId === organization.id
      ) {
        invalidateCache(organization.id);
        refreshBranding();
      }
    };

    return () => {
      channel.close();
      channelRef.current = null;
    };
  }, [organization, invalidateCache, refreshBranding]);

  useEffect(() => {
    if (!organization) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const cacheKey = `branding_${organization.id}`;
    try {
      const cached = sessionStorage.getItem(cacheKey);
      if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < CACHE_TTL_MS) {
          applyBranding({ ...BRAND_DEFAULTS, ...data, loaded: true });
          return;
        }
      }
    } catch {
      try {
        sessionStorage.removeItem(cacheKey);
      } catch {
        // storage unavailable
      }
    }

    getBranding(organization.id).then(({ data }) => {
      if (controller.signal.aborted) return;
      if (data) {
        const fullData: Omit<BrandingContextType, "refreshBranding"> = {
          primaryColor: data.primaryColor,
          primaryColorRgb: hexToRgb(data.primaryColor),
          logoUrl: data.logoUrl,
          brandName: data.brandName,
          loaded: true,
        };
        applyBranding(fullData);
        try {
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
        } catch {
          // quota exceeded or storage unavailable
        }
      } else {
        setBranding((prev) => ({ ...prev, loaded: true }));
      }
    });

    return () => {
      controller.abort();
    };
  }, [organization, applyBranding, refreshKey]);

  return (
    <BrandedContext.Provider value={{ ...branding, refreshBranding }}>
      {children}
    </BrandedContext.Provider>
  );
}

export const useBranding = () => useContext(BrandedContext);

export function broadcastBrandingChange(orgId: string) {
  if (typeof window === "undefined") return;
  try {
    const channel = new BroadcastChannel(BROADCAST_CHANNEL);
    channel.postMessage({ type: "branding-changed", orgId });
    channel.close();
  } catch {
    // BroadcastChannel not supported
  }
}
