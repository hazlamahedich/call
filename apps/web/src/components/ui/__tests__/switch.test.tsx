import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Switch } from "../switch";

describe("Switch", () => {
  it("renders with emerald active state styling", () => {
    const { container } = render(<Switch aria-label="Toggle feature" />);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("data-[state=checked]:bg-neon-emerald");
  });

  it("has accessible label", () => {
    render(<Switch aria-label="Dark mode" />);
    expect(
      screen.getByRole("switch", { name: "Dark mode" }),
    ).toBeInTheDocument();
  });
});
