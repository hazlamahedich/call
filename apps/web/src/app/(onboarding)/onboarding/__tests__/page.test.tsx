import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OnboardingPage from "../../onboarding/page";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/actions/onboarding", () => ({
  completeOnboarding: vi.fn(),
}));

vi.mock("@/components/obsidian/cockpit-container", () => ({
  CockpitContainer: ({
    onBootComplete,
    children,
  }: {
    onBootComplete: () => void;
    children: React.ReactNode;
    active?: boolean;
    reducedMotion?: boolean;
  }) => (
    <div data-testid="cockpit-container" onClick={onBootComplete}>
      {children}
    </div>
  ),
}));

vi.mock("@/components/onboarding/OnboardingProgress", () => ({
  OnboardingProgress: ({
    currentStep,
    totalSteps,
  }: {
    currentStep: number;
    totalSteps: number;
    reducedMotion?: boolean;
  }) => (
    <div data-testid="progress">
      Step {currentStep} of {totalSteps}
    </div>
  ),
}));

import { useRouter } from "next/navigation";
import { completeOnboarding } from "@/actions/onboarding";

const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
const mockCompleteOnboarding = completeOnboarding as ReturnType<typeof vi.fn>;

describe("[1.6-AC2][OnboardingPage] — Wizard orchestrator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const push = vi.fn();
    mockUseRouter.mockReturnValue({ push });
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
  });

  async function fillThroughStep2() {
    await userEvent.click(screen.getByText("Lead Generation"));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    const textarea = screen.getByRole("textbox", { name: "Script context" });
    await userEvent.type(
      textarea,
      "We sell premium widgets to small businesses",
    );
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
  }

  async function fillThroughStep3() {
    await fillThroughStep2();
    await userEvent.click(screen.getByText("Avery"));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
  }

  async function fillThroughStep4() {
    await fillThroughStep3();
    await userEvent.click(screen.getByText("Skip for now"));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
  }

  it("[1.6-UNIT-070][P0] Given wizard start, When rendered, Then step 1 is shown with Back disabled", () => {
    render(<OnboardingPage />);
    expect(screen.getByText("Step 1 of 5")).toBeInTheDocument();
    expect(screen.getByText("Launch Your Agent")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back" })).toBeDisabled();
  });

  it("[1.6-UNIT-071][P0] Given step 1 with no selection, When rendered, Then Next button is disabled", () => {
    render(<OnboardingPage />);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("[1.6-UNIT-072][P0] Given step 1, When selecting a goal and clicking Next, Then step 2 is shown", async () => {
    render(<OnboardingPage />);
    await userEvent.click(screen.getByText("Lead Generation"));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();
  });

  it("[1.6-UNIT-073][P1] Given step 2, When entering valid text and clicking Next, Then step 3 is shown", async () => {
    render(<OnboardingPage />);
    await fillThroughStep2();
    expect(screen.getByText("Step 3 of 5")).toBeInTheDocument();
  });

  it("[1.6-UNIT-074][P1] Given step 3, When selecting a voice, Then step 4 is shown after Next", async () => {
    render(<OnboardingPage />);
    await fillThroughStep3();
    expect(screen.getByText("Step 4 of 5")).toBeInTheDocument();
  });

  it("[1.6-UNIT-075][P1] Given wizard, When navigating back from step 4, Then step 3 is shown", async () => {
    render(<OnboardingPage />);
    await fillThroughStep3();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Step 3 of 5")).toBeInTheDocument();
  });

  it("[1.6-UNIT-076][P0] Given step 5, When submitting successfully, Then boot animation is shown", async () => {
    mockCompleteOnboarding.mockResolvedValue({
      agent: { id: 1, name: "My First Agent" },
      error: null,
    });
    render(<OnboardingPage />);
    await fillThroughStep4();
    await userEvent.click(screen.getByText("Strict (recommended)"));
    await userEvent.click(screen.getByRole("button", { name: "Launch Agent" }));
    await waitFor(() => {
      expect(screen.getByTestId("cockpit-container")).toBeInTheDocument();
    });
  });

  it("[1.6-UNIT-077][P1] Given submission failure, When error occurs, Then error message with Try Again is shown", async () => {
    mockCompleteOnboarding.mockResolvedValue({
      agent: null,
      error: "Server error",
    });
    render(<OnboardingPage />);
    await fillThroughStep4();
    await userEvent.click(screen.getByText("Strict (recommended)"));
    await userEvent.click(screen.getByRole("button", { name: "Launch Agent" }));
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });
  });

  it("[1.6-UNIT-078][P1] Given boot animation completes, When onBootComplete fires, Then navigates to /dashboard", async () => {
    const push = vi.fn();
    mockUseRouter.mockReturnValue({ push });
    mockCompleteOnboarding.mockResolvedValue({
      agent: { id: 1, name: "My First Agent" },
      error: null,
    });
    render(<OnboardingPage />);
    await fillThroughStep4();
    await userEvent.click(screen.getByText("Strict (recommended)"));
    await userEvent.click(screen.getByRole("button", { name: "Launch Agent" }));
    await waitFor(() => {
      expect(screen.getByTestId("cockpit-container")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTestId("cockpit-container"));
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("[1.6-UNIT-079][P2] Given step 5, When all steps completed, Then Launch Agent button is shown instead of Next", async () => {
    render(<OnboardingPage />);
    await fillThroughStep4();
    expect(screen.getByText("Step 5 of 5")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Next" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Launch Agent" }),
    ).toBeInTheDocument();
  });
});
