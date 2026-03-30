import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { UsageSummary } from "../UsageSummary";
import type { UsageSummary as UsageSummaryType } from "@call/types";

const baseSummary: UsageSummaryType = {
  used: 500,
  cap: 1000,
  percentage: 50.0,
  plan: "free",
  threshold: "ok",
};

describe("[1.7-AC5][UsageSummary] — Usage dashboard card", () => {
  it("[1.7-UNIT-054][P0] Given summary data, When rendered, Then usage count is displayed", () => {
    render(<UsageSummary summary={baseSummary} />);
    expect(screen.getByText("500")).toBeInTheDocument();
  });

  it("[1.7-UNIT-055][P0] Given summary data, When rendered, Then cap is displayed", () => {
    render(<UsageSummary summary={baseSummary} />);
    expect(screen.getByText(/1,000/)).toBeInTheDocument();
  });

  it("[1.7-UNIT-056][P0] Given summary data, When rendered, Then plan name is displayed", () => {
    render(<UsageSummary summary={baseSummary} />);
    expect(screen.getByText(/Seed plan/)).toBeInTheDocument();
  });

  it("[1.7-UNIT-057][P1] Given threshold=warning, When rendered, Then threshold alert is shown", () => {
    const warningSummary: UsageSummaryType = {
      ...baseSummary,
      percentage: 85.0,
      threshold: "warning",
    };
    render(<UsageSummary summary={warningSummary} />);
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
  });

  it("[1.7-UNIT-058][P1] Given percentage < 80, When rendered, Then no threshold alert", () => {
    render(<UsageSummary summary={baseSummary} />);
    const alerts = screen.queryByRole("status");
    expect(alerts).toBeNull();
  });

  it("[1.7-UNIT-059][P2] Given UsageSummary, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<UsageSummary summary={baseSummary} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[1.7-UNIT-060][P1] Given pro plan, When rendered, Then Scale label is shown", () => {
    const proSummary = { ...baseSummary, plan: "pro" as const };
    render(<UsageSummary summary={proSummary} />);
    expect(screen.getByText(/Scale plan/)).toBeInTheDocument();
  });
});
