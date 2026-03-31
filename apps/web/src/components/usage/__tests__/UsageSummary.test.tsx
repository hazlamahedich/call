import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { UsageSummary } from "../UsageSummary";
import {
  createUsageSummary,
  createUsageSummaryAtThreshold,
} from "@/test/factories/usage";

describe("[1.7-AC5][UsageSummary] — Usage dashboard card", () => {
  it("[1.7-UNIT-054][P0] Given summary data, When rendered, Then usage count is displayed", () => {
    render(<UsageSummary summary={createUsageSummary()} />);
    expect(screen.getByText("500")).toBeInTheDocument();
  });

  it("[1.7-UNIT-055][P0] Given summary data, When rendered, Then cap is displayed", () => {
    render(<UsageSummary summary={createUsageSummary()} />);
    expect(screen.getByText(/1,000/)).toBeInTheDocument();
  });

  it("[1.7-UNIT-056][P0] Given summary data, When rendered, Then plan name is displayed", () => {
    render(<UsageSummary summary={createUsageSummary()} />);
    expect(screen.getByText(/Seed plan/)).toBeInTheDocument();
  });

  it("[1.7-UNIT-057][P1] Given threshold=warning, When rendered, Then threshold alert is shown", () => {
    render(<UsageSummary summary={createUsageSummaryAtThreshold("warning")} />);
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
  });

  it("[1.7-UNIT-058][P1] Given percentage < 80, When rendered, Then no threshold alert", () => {
    render(<UsageSummary summary={createUsageSummary()} />);
    const alerts = screen.queryByRole("status");
    expect(alerts).toBeNull();
  });

  it("[1.7-UNIT-059][P2] Given UsageSummary, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <UsageSummary summary={createUsageSummary()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });

  it("[1.7-UNIT-060][P1] Given pro plan, When rendered, Then Scale label is shown", () => {
    render(<UsageSummary summary={createUsageSummary({ plan: "pro" })} />);
    expect(screen.getByText(/Scale plan/)).toBeInTheDocument();
  });
});
