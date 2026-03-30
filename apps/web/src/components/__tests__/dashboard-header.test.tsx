/**
 * Story 1-5: White-labeled Admin Portal & Custom Branding
 * Unit Tests for DashboardHeader Component
 *
 * Test ID Format: 1.5-UNIT-HEADER-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const mockBranding = vi.fn();

vi.mock("@/lib/branding-context", () => ({
  useBranding: () => mockBranding(),
}));

const { DashboardHeader } = await import("../dashboard-header");

describe("[P0] DashboardHeader Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("[1.5-UNIT-HEADER-001][P0] Given loading state, When rendering, Then shows placeholder text", () => {
    mockBranding.mockReturnValue({
      logoUrl: null,
      brandName: null,
      loaded: false,
    });

    render(<DashboardHeader />);

    expect(screen.getByText("Call")).toBeInTheDocument();
  });

  it("[1.5-UNIT-HEADER-002][P0] Given loaded with no branding, When rendering, Then shows default brand name", () => {
    mockBranding.mockReturnValue({
      logoUrl: null,
      brandName: null,
      loaded: true,
    });

    render(<DashboardHeader />);

    expect(screen.getByText("Call")).toBeInTheDocument();
  });

  it("[1.5-UNIT-HEADER-003][P1] Given loaded with brandName, When rendering, Then shows custom brand name", () => {
    mockBranding.mockReturnValue({
      logoUrl: null,
      brandName: "Acme Corp",
      loaded: true,
    });

    render(<DashboardHeader />);

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("[1.5-UNIT-HEADER-004][P1] Given loaded with logoUrl, When rendering, Then shows logo image", () => {
    mockBranding.mockReturnValue({
      logoUrl: "https://example.com/logo.png",
      brandName: "Acme Corp",
      loaded: true,
    });

    render(<DashboardHeader />);

    const img = screen.getByRole("img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/logo.png");
    expect(img).toHaveAttribute("alt", "Acme Corp");
  });

  it("[1.5-UNIT-HEADER-005][P2] Given loaded with logoUrl and no brandName, When rendering, Then shows logo with default alt", () => {
    mockBranding.mockReturnValue({
      logoUrl: "https://example.com/logo.png",
      brandName: null,
      loaded: true,
    });

    render(<DashboardHeader />);

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("alt", "Brand logo");
  });

  it("[1.5-UNIT-HEADER-006][P2] Given loaded state, When rendering, Then header has correct structure", () => {
    mockBranding.mockReturnValue({
      logoUrl: null,
      brandName: "Test Brand",
      loaded: true,
    });

    const { container } = render(<DashboardHeader />);

    const header = container.querySelector("header");
    expect(header).toBeInTheDocument();
    expect(header?.className).toContain("flex");
  });
});
