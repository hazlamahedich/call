import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Switch } from "../switch";

describe("[1.4-AC5][Switch] — Radix Switch with emerald active state", () => {
  it("[1.4-UNIT-051][P1] Given Switch, When rendered, Then emerald active state styling is applied", () => {
    const { container } = render(<Switch aria-label="Toggle feature" />);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("data-[state=checked]:bg-neon-emerald");
  });

  it("[1.4-UNIT-052][P1] Given Switch, When rendered, Then accessible label is present", () => {
    render(<Switch aria-label="Dark mode" />);
    expect(
      screen.getByRole("switch", { name: "Dark mode" }),
    ).toBeInTheDocument();
  });

  it("[1.4-UNIT-053][P1] Given Switch, When rendered, Then role=switch is present", () => {
    render(<Switch aria-label="Toggle" />);
    const sw = screen.getByRole("switch");
    expect(sw).toBeInTheDocument();
  });

  it("[1.4-UNIT-054][P1] Given Switch click, When toggled, Then checked/unchecked state changes", async () => {
    render(<Switch aria-label="Toggle" />);
    const sw = screen.getByRole("switch");

    expect(sw).toHaveAttribute("data-state", "unchecked");
    expect(sw.getAttribute("aria-checked")).toBe("false");

    await userEvent.click(sw);
    expect(sw).toHaveAttribute("data-state", "checked");
    expect(sw.getAttribute("aria-checked")).toBe("true");
  });

  it("[1.4-UNIT-055][P1] Given Space key press on Switch, When toggled, Then checked state changes", async () => {
    render(<Switch aria-label="Toggle" />);
    const sw = screen.getByRole("switch");

    sw.focus();
    await userEvent.keyboard(" ");
    expect(sw).toHaveAttribute("data-state", "checked");
  });

  it("[1.4-UNIT-056][P2] Given disabled Switch, When rendered, Then disabled styling is applied", () => {
    render(<Switch aria-label="Toggle" disabled />);
    const sw = screen.getByRole("switch") as HTMLButtonElement;
    expect(sw.disabled).toBe(true);
    expect(sw.className).toContain("disabled:cursor-not-allowed");
  });

  it("[1.4-UNIT-057][P1] Given Switch component, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<Switch aria-label="Accessible toggle" />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
