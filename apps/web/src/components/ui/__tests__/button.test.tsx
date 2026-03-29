import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Button } from "../button";

describe("[1.4-AC1][Button] — Neon-emerald CTA with variants", () => {
  it("[1.4-UNIT-010][P0] Given default Button, When rendered, Then primary variant classes are applied", () => {
    const { container } = render(<Button>Click</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("brand-primary");
    expect(btn.className).toContain("text-background");
    expect(btn.className).toContain("brand-primary-rgb");
  });

  it("[1.4-UNIT-011][P1] Given variant=secondary, When rendered, Then secondary classes are applied", () => {
    const { container } = render(<Button variant="secondary">Sec</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("border");
    expect(btn.className).toContain("bg-transparent");
    expect(btn.className).toContain("text-foreground");
  });

  it("[1.4-UNIT-012][P1] Given variant=destructive, When rendered, Then destructive classes are applied", () => {
    const { container } = render(<Button variant="destructive">Delete</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("border-destructive");
    expect(btn.className).toContain("text-destructive");
  });

  it("[1.4-UNIT-013][P2] Given variant=ghost, When rendered, Then ghost classes are applied", () => {
    const { container } = render(<Button variant="ghost">Ghost</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("text-muted-foreground");
  });

  it("[1.4-UNIT-014][P1] Given size=sm, When rendered, Then small size classes are applied", () => {
    const { container } = render(<Button size="sm">Small</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("h-8");
    expect(btn.className).toContain("px-sm");
  });

  it("[1.4-UNIT-015][P1] Given default size, When rendered, Then md size classes are applied", () => {
    const { container } = render(<Button>Medium</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("h-10");
    expect(btn.className).toContain("px-md");
  });

  it("[1.4-UNIT-016][P1] Given size=lg, When rendered, Then large size classes are applied", () => {
    const { container } = render(<Button size="lg">Large</Button>);
    const btn = container.firstChild as HTMLElement;
    expect(btn.className).toContain("h-12");
    expect(btn.className).toContain("px-lg");
  });

  it("[1.4-UNIT-017][P0] Given disabled Button, When rendered, Then disabled state is applied", () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByText("Disabled") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.className).toContain("disabled:opacity-50");
  });

  it("[1.4-UNIT-018][P0] Given Button with onClick, When clicked, Then handler fires once", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click me</Button>);
    await userEvent.click(screen.getByText("Click me"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("[1.4-UNIT-019][P2] Given type=submit, When rendered, Then button type is submit", () => {
    render(<Button type="submit">Submit</Button>);
    const btn = screen.getByText("Submit") as HTMLButtonElement;
    expect(btn.type).toBe("submit");
  });

  it("[1.4-UNIT-020][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(<Button className="extra-class">Test</Button>);
    expect((container.firstChild as HTMLElement).className).toContain(
      "extra-class",
    );
  });

  it("[1.4-UNIT-021][P1] Given Button, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<Button>Accessible</Button>);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
