import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { OnboardingProgress } from "../OnboardingProgress";

describe("[1.6-AC6][OnboardingProgress] — Progress indicator for wizard steps", () => {
  it("[1.6-UNIT-050][P0] Given currentStep=1, When rendered, Then step 1 is active and text shows 'Step 1 of 5'", () => {
    render(<OnboardingProgress currentStep={1} />);
    expect(screen.getByText("Step 1 of 5: Business Goal")).toBeInTheDocument();
    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toHaveAttribute("aria-valuenow", "1");
  });

  it("[1.6-UNIT-051][P0] Given currentStep=3, When rendered, Then steps 1-2 are completed, 3 is active", () => {
    const { container } = render(<OnboardingProgress currentStep={3} />);
    const dots = container.querySelectorAll('[aria-label^="Step"]');
    expect(dots[0]).toHaveAttribute(
      "aria-label",
      "Step 1: Business Goal (completed)",
    );
    expect(dots[1]).toHaveAttribute(
      "aria-label",
      "Step 2: Script Context (completed)",
    );
    expect(dots[2]).toHaveAttribute(
      "aria-label",
      "Step 3: Voice Selection (current)",
    );
    expect(dots[3]).toHaveAttribute("aria-label", "Step 4: Integration");
    expect(dots[4]).toHaveAttribute("aria-label", "Step 5: Safety Level");
  });

  it("[1.6-UNIT-052][P1] Given currentStep=5, When rendered, Then text shows 'Step 5 of 5: Safety Level'", () => {
    render(<OnboardingProgress currentStep={5} />);
    expect(screen.getByText("Step 5 of 5: Safety Level")).toBeInTheDocument();
  });

  it("[1.6-UNIT-053][P1] Given totalSteps=3, When rendered, Then only 3 dots are shown", () => {
    const { container } = render(
      <OnboardingProgress currentStep={1} totalSteps={3} />,
    );
    const dots = container.querySelectorAll('[aria-label^="Step"]');
    expect(dots).toHaveLength(3);
    expect(screen.getByText("Step 1 of 3: Business Goal")).toBeInTheDocument();
  });

  it("[1.6-UNIT-054][P1] Given reducedMotion=true, When rendered, Then transition-all is NOT applied", () => {
    const { container } = render(
      <OnboardingProgress currentStep={1} reducedMotion={true} />,
    );
    const dot = container.querySelector('[aria-label^="Step"]');
    expect(dot?.className).not.toContain("transition-all");
  });

  it("[1.6-UNIT-055][P2] Given OnboardingProgress, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<OnboardingProgress currentStep={1} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
