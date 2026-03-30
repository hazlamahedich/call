import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { OnboardingGuard } from "@/components/onboarding-guard";

vi.mock("@clerk/nextjs", () => ({
  useOrganization: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/actions/onboarding", () => ({
  getOnboardingStatus: vi.fn(),
}));

import { useOrganization } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { getOnboardingStatus } from "@/actions/onboarding";

const mockUseOrganization = useOrganization as ReturnType<typeof vi.fn>;
const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
const mockGetOnboardingStatus = getOnboardingStatus as ReturnType<typeof vi.fn>;

describe("[1.6-AC1][OnboardingGuard] — Redirect guard for onboarding status", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue({ push: vi.fn() });
  });

  it("[1.6-UNIT-060][P0] Given no organization, When rendered, Then children are shown immediately", async () => {
    mockUseOrganization.mockReturnValue({ organization: null });
    render(
      <OnboardingGuard>
        <div data-testid="child">Dashboard</div>
      </OnboardingGuard>,
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("[1.6-UNIT-061][P0] Given onboarding complete, When guard checks status, Then children are rendered", async () => {
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_123" },
    });
    mockGetOnboardingStatus.mockResolvedValue({
      data: { completed: true },
      error: null,
    });

    render(
      <OnboardingGuard>
        <div data-testid="child">Dashboard</div>
      </OnboardingGuard>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  it("[1.6-UNIT-062][P0] Given onboarding incomplete, When guard checks status, Then redirects to /onboarding", async () => {
    const push = vi.fn();
    mockUseRouter.mockReturnValue({ push });
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_123" },
    });
    mockGetOnboardingStatus.mockResolvedValue({
      data: { completed: false },
      error: null,
    });

    render(
      <OnboardingGuard>
        <div data-testid="child">Dashboard</div>
      </OnboardingGuard>,
    );

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/onboarding");
    });
  });

  it("[1.6-UNIT-063][P1] Given onboarding status API error, When guard checks, Then children are shown (fail open)", async () => {
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_123" },
    });
    mockGetOnboardingStatus.mockResolvedValue({
      data: null,
      error: "Network error",
    });

    render(
      <OnboardingGuard>
        <div data-testid="child">Dashboard</div>
      </OnboardingGuard>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  it("[1.6-UNIT-064][P1] Given onboarding status throws, When guard catches error, Then children are shown (fail open)", async () => {
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_123" },
    });
    mockGetOnboardingStatus.mockRejectedValue(new Error("Network error"));

    render(
      <OnboardingGuard>
        <div data-testid="child">Dashboard</div>
      </OnboardingGuard>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  it("[1.6-UNIT-065][P1] Given checking state, When guard is loading, Then skeleton is shown", () => {
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_123" },
    });
    mockGetOnboardingStatus.mockReturnValue(new Promise(() => {}));

    const { container } = render(
      <OnboardingGuard>
        <div data-testid="child">Dashboard</div>
      </OnboardingGuard>,
    );

    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });
});
