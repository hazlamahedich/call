import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/actions/usage", () => ({
  getUsageSummary: vi.fn(),
}));

import { getUsageSummary } from "@/actions/usage";
import DashboardPage from "@/app/(dashboard)/dashboard/page";

const mockGetUsageSummary = vi.mocked(getUsageSummary);

describe("[1.7-AC2,AC3][DashboardPage] — Dashboard alert rendering", () => {
  it("[1.7-UNIT-113][P0] Given warning threshold, When rendered, Then shows threshold alert", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: {
        used: 850,
        cap: 1000,
        percentage: 85.0,
        plan: "free",
        threshold: "warning",
      },
      error: null,
    });

    render(await DashboardPage());
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("80%");
  });

  it("[1.7-UNIT-114][P0] Given ok threshold, When rendered, Then no alert is shown", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: {
        used: 500,
        cap: 1000,
        percentage: 50.0,
        plan: "free",
        threshold: "ok",
      },
      error: null,
    });

    const { container } = render(await DashboardPage());
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("[1.7-UNIT-115][P0] Given critical threshold, When rendered, Then shows error alert", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: {
        used: 970,
        cap: 1000,
        percentage: 97.0,
        plan: "free",
        threshold: "critical",
      },
      error: null,
    });

    render(await DashboardPage());
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("95%");
  });

  it("[1.7-UNIT-116][P0] Given exceeded threshold, When rendered, Then shows error alert", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: {
        used: 1000,
        cap: 1000,
        percentage: 100.0,
        plan: "free",
        threshold: "exceeded",
      },
      error: null,
    });

    render(await DashboardPage());
    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("limit reached");
  });

  it("[1.7-UNIT-117][P1] Given null data, When rendered, Then no alert is shown", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: null,
      error: "Not authenticated",
    });

    const { container } = render(await DashboardPage());
    expect(screen.queryByRole("status")).toBeNull();
  });
});
