import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusMessage } from "../status-message";

describe("StatusMessage", () => {
  const variants = ["success", "warning", "error", "info"] as const;

  variants.forEach((variant) => {
    it(`renders ${variant} variant with message`, () => {
      render(
        <StatusMessage variant={variant}>{variant} message</StatusMessage>,
      );
      expect(screen.getByText(`${variant} message`)).toBeInTheDocument();
      const container = screen.getByRole("status");
      expect(container.className).toContain("border-");
    });
  });

  it("has role=status for accessibility", () => {
    render(<StatusMessage variant="success">Test</StatusMessage>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
