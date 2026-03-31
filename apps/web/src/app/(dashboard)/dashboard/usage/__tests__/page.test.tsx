import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createUsageSummary } from "@/test/factories/usage";

vi.mock("@/actions/usage", () => ({
  getUsageSummary: vi.fn(),
}));

import { getUsageSummary } from "@/actions/usage";
import UsagePage from "@/app/(dashboard)/dashboard/usage/page";

const mockGetUsageSummary = vi.mocked(getUsageSummary);

describe("[1.7][UsagePage] — Dedicated usage page", () => {
  it("[1.7-UNIT-118][P0] Given valid data, When rendered, Then shows usage summary", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: createUsageSummary(),
      error: null,
    });

    render(await UsagePage());
    expect(screen.getByText("Usage")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
    expect(screen.getByText(/1,000/)).toBeInTheDocument();
  });

  it("[1.7-UNIT-119][P0] Given error, When rendered, Then shows error message", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: null,
      error: "Failed to fetch usage summary",
    });

    render(await UsagePage());
    expect(screen.getByText("Usage")).toBeInTheDocument();
    expect(
      screen.getByText("Failed to fetch usage summary"),
    ).toBeInTheDocument();
  });

  it("[1.7-UNIT-120][P0] Given null data with no error, When rendered, Then shows fallback error", async () => {
    mockGetUsageSummary.mockResolvedValue({
      data: null,
      error: null,
    });

    render(await UsagePage());
    expect(screen.getByText("Usage")).toBeInTheDocument();
    expect(screen.getByText("Unable to load usage data")).toBeInTheDocument();
  });
});
