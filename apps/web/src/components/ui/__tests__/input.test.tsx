import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { Input } from "../input";

describe("[1.4-AC1][Input] — Form input with error and disabled states", () => {
  it("[1.4-UNIT-033][P0] Given default Input, When rendered, Then bg-background, border-input, and text-foreground classes are applied", () => {
    render(<Input placeholder="Test input" />);
    const input = screen.getByPlaceholderText("Test input");
    expect(input.className).toContain("bg-background");
    expect(input.className).toContain("border-input");
    expect(input.className).toContain("text-foreground");
  });

  it("[1.4-UNIT-034][P0] Given error=true, When rendered, Then aria-invalid=true and border-destructive are applied", () => {
    render(<Input error placeholder="Error input" />);
    const input = screen.getByPlaceholderText("Error input");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(input.className).toContain("border-destructive");
  });

  it("[1.4-UNIT-035][P1] Given error=false, When rendered, Then aria-invalid is NOT set", () => {
    render(<Input error={false} placeholder="Clean" />);
    const input = screen.getByPlaceholderText("Clean");
    expect(input.getAttribute("aria-invalid")).toBeNull();
  });

  it("[1.4-UNIT-036][P1] Given disabled=true, When rendered, Then disabled styling is applied", () => {
    render(<Input disabled placeholder="Disabled" />);
    const input = screen.getByPlaceholderText("Disabled") as HTMLInputElement;
    expect(input.disabled).toBe(true);
    expect(input.className).toContain("disabled:cursor-not-allowed");
    expect(input.className).toContain("disabled:opacity-20");
  });

  it("[1.4-UNIT-037][P1] Given type attribute, When rendered, Then correct input type is used", () => {
    const { rerender } = render(<Input type="email" placeholder="Email" />);
    expect(
      (screen.getByPlaceholderText("Email") as HTMLInputElement).type,
    ).toBe("email");

    rerender(<Input type="password" placeholder="Pass" />);
    expect((screen.getByPlaceholderText("Pass") as HTMLInputElement).type).toBe(
      "password",
    );
  });

  it("[1.4-UNIT-038][P2] Given placeholder, When rendered, Then placeholder text is visible", () => {
    render(<Input placeholder="Enter value" />);
    expect(screen.getByPlaceholderText("Enter value")).toBeInTheDocument();
  });

  it("[1.4-UNIT-039][P1] Given labeled Input, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <label>
        Name
        <Input />
      </label>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
