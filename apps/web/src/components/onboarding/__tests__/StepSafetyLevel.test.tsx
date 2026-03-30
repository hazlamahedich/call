import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { StepSafetyLevel } from "../StepSafetyLevel";
import { SAFETY_LEVELS } from "@/lib/onboarding-constants";

describe("[1.6-AC5][StepSafetyLevel] — Safety level selection step", () => {
  it("[1.6-UNIT-040][P0] Given no value, When rendered, Then all safety levels are shown", () => {
    render(<StepSafetyLevel value="" onChange={vi.fn()} />);
    for (const level of SAFETY_LEVELS) {
      expect(screen.getByText(level.name)).toBeInTheDocument();
    }
  });

  it("[1.6-UNIT-041][P0] Given value='strict', When rendered, Then Strict is selected", () => {
    const { container } = render(
      <StepSafetyLevel value="strict" onChange={vi.fn()} />,
    );
    const selected = container.querySelector(
      '[role="radio"][aria-checked="true"]',
    );
    expect(selected).toBeInTheDocument();
    expect(selected?.textContent).toContain("Strict");
  });

  it("[1.6-UNIT-042][P0] Given moderate option, When clicked, Then onChange fires with 'moderate'", async () => {
    const onChange = vi.fn();
    render(<StepSafetyLevel value="" onChange={onChange} />);
    await userEvent.click(screen.getByText("Moderate"));
    expect(onChange).toHaveBeenCalledWith("moderate");
  });

  it("[1.6-UNIT-043][P1] Given radiogroup, When rendered, Then correct ARIA role is present", () => {
    render(<StepSafetyLevel value="" onChange={vi.fn()} />);
    expect(
      screen.getByRole("radiogroup", { name: "Safety level options" }),
    ).toBeInTheDocument();
  });

  it("[1.6-UNIT-044][P2] Given StepSafetyLevel, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <StepSafetyLevel value="" onChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
