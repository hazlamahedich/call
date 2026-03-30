import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { StepScriptContext, MIN_LENGTH } from "../StepScriptContext";

describe("[1.6-AC2][StepScriptContext] — Script context text input step", () => {
  it("[1.6-UNIT-010][P0] Given empty value, When rendered, Then textarea is present with placeholder", () => {
    render(<StepScriptContext value="" onChange={vi.fn()} />);
    const textarea = screen.getByRole("textbox", { name: "Script context" });
    expect(textarea).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/We sell premium widgets/),
    ).toBeInTheDocument();
  });

  it("[1.6-UNIT-011][P0] Given value, When typed, Then onChange fires for each character", async () => {
    const onChange = vi.fn();
    render(<StepScriptContext value="" onChange={onChange} />);
    const textarea = screen.getByRole("textbox", { name: "Script context" });
    await userEvent.type(textarea, "Hi");
    expect(onChange).toHaveBeenCalled();
    expect(onChange).toHaveBeenLastCalledWith("i");
    expect(onChange).toHaveBeenCalledWith("H");
  });

  it("[1.6-UNIT-012][P1] Given value shorter than MIN_LENGTH, When rendered, Then char count shows muted style", () => {
    render(<StepScriptContext value="Short" onChange={vi.fn()} />);
    const counter = screen.getByText(`5 / ${MIN_LENGTH} minimum characters`);
    expect(counter).toBeInTheDocument();
    expect(counter.className).toContain("text-muted-foreground");
  });

  it("[1.6-UNIT-013][P1] Given value >= MIN_LENGTH, When rendered, Then char count shows emerald style", () => {
    const longValue = "A".repeat(MIN_LENGTH);
    render(<StepScriptContext value={longValue} onChange={vi.fn()} />);
    const counter = screen.getByText(
      `${MIN_LENGTH} / ${MIN_LENGTH} minimum characters`,
    );
    expect(counter).toBeInTheDocument();
    expect(counter.className).toContain("text-emerald-500");
  });

  it("[1.6-UNIT-014][P2] Given StepScriptContext, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <StepScriptContext value="" onChange={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
