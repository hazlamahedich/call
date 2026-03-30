/**
 * Story 1-5: White-labeled Admin Portal & Custom Branding
 * Unit Tests for BrandingProvider, hexToRgb, useBranding
 *
 * Test ID Format: 1.5-UNIT-CONTEXT-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import type { AgencyBranding } from "@call/types";

const mockUseOrganization = vi.fn();

vi.mock("@clerk/nextjs", () => ({
  useOrganization: () => mockUseOrganization(),
}));

const mockGetBranding = vi.fn();
vi.mock("@/actions/branding", () => ({
  getBranding: (...args: unknown[]) => mockGetBranding(...args),
}));

function Consumer() {
  const {
    primaryColor,
    primaryColorRgb,
    logoUrl,
    brandName,
    loaded,
    refreshBranding,
  } = useBranding();
  return (
    <div>
      <span data-testid="primaryColor">{primaryColor}</span>
      <span data-testid="primaryColorRgb">{primaryColorRgb}</span>
      <span data-testid="logoUrl">{logoUrl ?? "null"}</span>
      <span data-testid="brandName">{brandName ?? "null"}</span>
      <span data-testid="loaded">{String(loaded)}</span>
      <button data-testid="refresh" onClick={refreshBranding} />
    </div>
  );
}

const MOCK_BRANDING: AgencyBranding = {
  id: 1,
  orgId: "org_test123",
  logoUrl: "https://example.com/logo.png",
  primaryColor: "#FF5500",
  customDomain: null,
  domainVerified: false,
  brandName: "Acme Corp",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

const { useBranding } = await import("@/lib/branding-context");
const { BrandingProvider } = await import("@/lib/branding-context");

describe("[P0] BrandingContext - hexToRgb via provider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_test123" },
    });
    mockGetBranding.mockReset();
    sessionStorage.clear();
    document.documentElement.style.removeProperty("--brand-primary");
    document.documentElement.style.removeProperty("--brand-primary-rgb");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("[1.5-UNIT-CONTEXT-001][P0] Given valid primaryColor #FF5500, When provider loads, Then converts to RGB 255,85,0", async () => {
    mockGetBranding.mockResolvedValueOnce({ data: MOCK_BRANDING, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(screen.getByTestId("primaryColorRgb").textContent).toBe("255,85,0");
  });

  it("[1.5-UNIT-CONTEXT-002][P1] Given default primaryColor #10B981, When provider loads with no data, Then converts to RGB 16,185,129", async () => {
    mockGetBranding.mockResolvedValueOnce({ data: null, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(screen.getByTestId("primaryColorRgb").textContent).toBe(
      "16,185,129",
    );
  });

  it("[1.5-UNIT-CONTEXT-003][P1] Given CSS custom properties, When provider loads, Then sets --brand-primary-rgb", async () => {
    mockGetBranding.mockResolvedValueOnce({ data: MOCK_BRANDING, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(
      document.documentElement.style.getPropertyValue("--brand-primary-rgb"),
    ).toBe("255,85,0");
  });
});

describe("[P0] BrandingProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_test123" },
    });
    mockGetBranding.mockReset();
    sessionStorage.clear();
    document.documentElement.style.removeProperty("--brand-primary");
    document.documentElement.style.removeProperty("--brand-primary-rgb");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("[1.5-UNIT-CONTEXT-004][P0] Given branding data, When provider loads, Then exposes branding via context", async () => {
    mockGetBranding.mockResolvedValueOnce({ data: MOCK_BRANDING, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(mockGetBranding).toHaveBeenCalledWith("org_test123");
    expect(screen.getByTestId("primaryColor").textContent).toBe("#FF5500");
    expect(screen.getByTestId("logoUrl").textContent).toBe(
      "https://example.com/logo.png",
    );
    expect(screen.getByTestId("brandName").textContent).toBe("Acme Corp");
    expect(screen.getByTestId("loaded").textContent).toBe("true");
  });

  it("[1.5-UNIT-CONTEXT-005][P1] Given branding data, When provider loads, Then sets CSS custom properties", async () => {
    mockGetBranding.mockResolvedValueOnce({ data: MOCK_BRANDING, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(
      document.documentElement.style.getPropertyValue("--brand-primary"),
    ).toBe("#FF5500");
  });

  it("[1.5-UNIT-CONTEXT-006][P1] Given no branding data, When provider loads, Then uses defaults", async () => {
    mockGetBranding.mockResolvedValueOnce({ data: null, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(screen.getByTestId("primaryColor").textContent).toBe("#10B981");
    expect(screen.getByTestId("logoUrl").textContent).toBe("null");
    expect(screen.getByTestId("brandName").textContent).toBe("null");
    expect(screen.getByTestId("loaded").textContent).toBe("true");
  });

  it("[1.5-UNIT-CONTEXT-007][P1] Given cached branding in sessionStorage, When provider loads, Then uses cache", async () => {
    const cacheKey = "branding_org_test123";
    const cachedData = {
      data: {
        primaryColor: "#ABCDEF",
        logoUrl: "https://cached.com/logo.png",
        brandName: "Cached Brand",
      },
      timestamp: Date.now(),
    };
    sessionStorage.setItem(cacheKey, JSON.stringify(cachedData));

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(mockGetBranding).not.toHaveBeenCalled();
    expect(screen.getByTestId("primaryColor").textContent).toBe("#ABCDEF");
    expect(screen.getByTestId("brandName").textContent).toBe("Cached Brand");
  });

  it("[1.5-UNIT-CONTEXT-008][P2] Given expired cache, When provider loads, Then fetches fresh data", async () => {
    const cacheKey = "branding_org_test123";
    const expiredCache = {
      data: {
        primaryColor: "#OLD",
        logoUrl: null,
        brandName: null,
      },
      timestamp: Date.now() - 120_000,
    };
    sessionStorage.setItem(cacheKey, JSON.stringify(expiredCache));
    mockGetBranding.mockResolvedValueOnce({ data: MOCK_BRANDING, error: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(mockGetBranding).toHaveBeenCalledWith("org_test123");
  });

  it("[1.5-UNIT-CONTEXT-009][P1] Given no organization, When provider loads, Then does not fetch", async () => {
    mockUseOrganization.mockReturnValue({ organization: null });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(mockGetBranding).not.toHaveBeenCalled();
    expect(screen.getByTestId("loaded").textContent).toBe("false");
  });

  it("[1.5-UNIT-CONTEXT-010][P2] Given refreshBranding called, When provider refreshes with cleared cache, Then fetches fresh data and updates context", async () => {
    mockGetBranding
      .mockResolvedValueOnce({ data: MOCK_BRANDING, error: null })
      .mockResolvedValueOnce({
        data: { ...MOCK_BRANDING, primaryColor: "#0000FF" },
        error: null,
      });

    await act(async () => {
      render(
        <BrandingProvider>
          <Consumer />
        </BrandingProvider>,
      );
    });

    expect(mockGetBranding).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("primaryColor").textContent).toBe("#FF5500");

    sessionStorage.clear();

    await act(async () => {
      screen.getByTestId("refresh").click();
    });

    await waitFor(() => {
      expect(mockGetBranding).toHaveBeenCalledTimes(2);
    });

    expect(screen.getByTestId("primaryColor").textContent).toBe("#0000FF");
  });
});
