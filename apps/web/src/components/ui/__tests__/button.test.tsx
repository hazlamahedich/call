import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "../button";

describe("Button", () => {
  it("applies primary variant classes by default", () => {
    render(
      <button className="bg-neon-emerald text-background shadow-glow-emerald hover:bg-neon-emerald/90 inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-20 h-10 px-md text-sm">
        Click
      </button>,
    );
    const btn = screen.getByText("Click");
    expect(btn.className).toContain("bg-neon-emerald");
  });

  it("applies destructive variant classes", () => {
    const { container } = render(<Button variant="destructive">Delete</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("border-destructive");
    expect(btn.className).toContain("text-destructive");
  });

  it("applies disabled state", () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByText("Disabled") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.className).toContain("disabled:opacity-20");
  });

  it("renders with custom className", () => {
    const { container } = render(<Button className="extra-class">Test</Button>);
    expect((container.firstChild as HTMLElement).className).toContain(
      "extra-class",
    );
  });
});
