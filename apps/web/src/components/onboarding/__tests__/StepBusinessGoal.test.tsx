import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { StepBusinessGoal } from "../StepBusinessGoal";
import { BUSINESS_GOALS } from "@/lib/onboarding-constants";

describe("[1.6-AC2][StepBusinessGoal] — Business goal selection step", () => {
  it("[1.6-UNIT-001][P0] Given BUSINESS_GOALS, When rendered, Then all goal options are displayed", () => {
    render(<StepBusinessGoal value="" onChange={vi.fn()} />);
    BUSINESS_GOALS.forEach((goal) => {
      expect(screen.getByText(goal.name)).toBeInTheDocument();
    });
  });

  it("[1.6-UNIT-002][P0] Given a goal is clicked, When user selects it, Then onChange is called with goal id", async () => {
    const onChange = vi.fn();
    render(<StepBusinessGoal value="" onChange={onChange} />);
    await userEvent.click(screen.getByText("Lead Generation"));
    expect(onChange).toHaveBeenCalledWith("lead-generation");
  });

  it("[1.6-UNIT-003][P1] Given a selected value, When rendered, Then correct option has emerald border style", () => {
    const { container } = render(
      <StepBusinessGoal value="cold-outreach" onChange={vi.fn()} />,
    );
    const buttons = container.querySelectorAll('[role="radio"]');
    const selectedButton = Array.from(buttons).find(
      (b) => b.getAttribute("aria-checked") === "true",
    );
    expect(selectedButton).toBeTruthy();
    expect(selectedButton?.className).toContain("border-emerald-500");
  });

  it("[1.6-UNIT-004][P1] Given ARIA radiogroup, When rendered, Then role and labels are present", () => {
    render(<StepBusinessGoal value="" onChange={vi.fn()} />);
    const radiogroup = screen.getByRole("radiogroup", {
      name: "Business goal options",
    });
    expect(radiogroup).toBeInTheDocument();
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(BUSINESS_GOALS.length);
  });

  it("[1.6-UNIT-005][P1] Given keyboard navigation, When pressing Enter on a goal, Then onChange fires", async () => {
    const onChange = vi.fn();
    render(<StepBusinessGoal value="" onChange={onChange} />);
    const firstGoal = screen.getAllByRole("radio")[0];
    await userEvent.type(firstGoal, "{Enter}");
    expect(onChange).toHaveBeenCalledWith(BUSINESS_GOALS[0].id);
  });

  it("[1.6-UNIT-006][P2] Given keyboard navigation, When pressing Space on a goal, Then onChange fires", async () => {
    const onChange = vi.fn();
    render(<StepBusinessGoal value="" onChange={onChange} />);
    const firstGoal = screen.getAllByRole("radio")[0];
    await userEvent.type(firstGoal, " ");
    expect(onChange).toHaveBeenCalledWith(BUSINESS_GOALS[0].id);
  });

  it("[1.6-UNIT-007][P2] Given StepBusinessGoal, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <StepBusinessGoal value="" onChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
