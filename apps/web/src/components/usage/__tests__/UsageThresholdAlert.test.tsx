import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { UsageThresholdAlert } from "../UsageThresholdAlert";
import { createUsageSummaryAtThreshold } from "@/test/factories/usage";

describe("[1.7-AC2,AC3][UsageThresholdAlert] — Conditional threshold alert", () => {
  it("[1.7-UNIT-049][P0] Given threshold=ok, When rendered, Then nothing is displayed", () => {
    const { container } = render(<UsageThresholdAlert threshold="ok" />);
    expect(container.innerHTML).toBe("");
  });

  it("[1.7-UNIT-050][P0] Given threshold=warning, When rendered, Then StatusMessage with warning variant is shown", () => {
    render(<UsageThresholdAlert threshold="warning" />);
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("80%");
  });

  it("[1.7-UNIT-051][P0] Given threshold=critical, When rendered, Then StatusMessage with error variant is shown", () => {
    const { container } = render(<UsageThresholdAlert threshold="critical" />);
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("95%");
    expect(
      container.querySelector(".border-destructive\\/30"),
    ).toBeInTheDocument();
  });

  it("[1.7-UNIT-052][P0] Given threshold=exceeded, When rendered, Then StatusMessage with error variant is shown", () => {
    render(<UsageThresholdAlert threshold="exceeded" />);
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("limit reached");
  });

  it("[1.7-UNIT-053][P2] Given UsageThresholdAlert, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<UsageThresholdAlert threshold="warning" />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
