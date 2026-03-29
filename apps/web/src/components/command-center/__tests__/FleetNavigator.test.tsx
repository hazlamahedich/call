import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { FleetNavigator } from "../FleetNavigator";

describe("[1.4-AC1][FleetNavigator] — Sidebar agent list with design system primitives", () => {
  it("[1.4-UNIT-100][P1] Given FleetNavigator, When rendered, Then agent names are displayed", () => {
    render(<FleetNavigator />);
    expect(screen.getByText("PHOENIX-01")).toBeInTheDocument();
    expect(screen.getByText("TITAN-04")).toBeInTheDocument();
    expect(screen.getByText("SHADOW-09")).toBeInTheDocument();
  });

  it("[1.4-UNIT-101][P1] Given FleetNavigator, When rendered, Then Fleet Navigator heading is displayed", () => {
    render(<FleetNavigator />);
    expect(screen.getByText("Fleet Navigator")).toBeInTheDocument();
  });

  it("[1.4-UNIT-102][P1] Given FleetNavigator, When rendered, Then active agents show emerald indicator", () => {
    const { container } = render(<FleetNavigator />);
    const indicators = container.querySelectorAll(".bg-neon-emerald");
    expect(indicators.length).toBeGreaterThanOrEqual(1);
  });

  it("[1.4-UNIT-103][P1] Given FleetNavigator, When rendered, Then call counts are displayed", () => {
    render(<FleetNavigator />);
    expect(screen.getByText(/124 Calls/)).toBeInTheDocument();
    expect(screen.getByText(/89 Calls/)).toBeInTheDocument();
    expect(screen.getByText(/210 Calls/)).toBeInTheDocument();
  });

  it("[1.4-UNIT-104][P1] Given FleetNavigator, When rendered, Then agent statuses are shown", () => {
    render(<FleetNavigator />);
    const activeLabels = screen.getAllByText("Active");
    expect(activeLabels.length).toBe(2);
    expect(screen.getByText("Standby")).toBeInTheDocument();
  });

  it("[1.4-UNIT-105][P1] Given FleetNavigator, When rendered, Then System Health section is present", () => {
    render(<FleetNavigator />);
    expect(screen.getByText("System Health")).toBeInTheDocument();
  });

  it("[1.4-UNIT-106][P2] Given FleetNavigator uses design system, When rendered, Then bg-card class is applied", () => {
    const { container } = render(<FleetNavigator />);
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("bg-card");
  });

  it("[1.4-UNIT-107][P2] Given FleetNavigator uses design system, When rendered, Then border-border class is applied", () => {
    const { container } = render(<FleetNavigator />);
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("border-border");
  });

  it("[1.4-UNIT-108][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(<FleetNavigator className="extra-class" />);
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("extra-class");
  });

  it("[1.4-UNIT-109][P1] Given FleetNavigator, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<FleetNavigator />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
