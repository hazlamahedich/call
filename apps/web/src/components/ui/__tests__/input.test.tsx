import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "../input";

describe("Input", () => {
  it("renders with default styling", () => {
    render(<Input placeholder="Test input" />);
    const input = screen.getByPlaceholderText("Test input");
    expect(input.className).toContain("bg-background");
  });

  it("applies aria-invalid and error styling when error prop is true", () => {
    render(<Input error placeholder="Error input" />);
    const input = screen.getByPlaceholderText("Error input");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(input.className).toContain("border-destructive");
  });
});
