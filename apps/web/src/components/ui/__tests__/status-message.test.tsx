import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { StatusMessage } from "../status-message";

describe("[1.4-AC3][StatusMessage] — Status indicator with variant icons", () => {
  const variants = ["success", "warning", "error", "info"] as const;

  variants.forEach((variant) => {
    it(`[1.4-UNIT-040][P0] Given variant=${variant}, When rendered, Then message and border styling are applied`, () => {
      render(
        <StatusMessage variant={variant}>{variant} message</StatusMessage>,
      );
      expect(screen.getByText(`${variant} message`)).toBeInTheDocument();
      const container = screen.getByRole("status");
      expect(container.className).toContain("border-");
    });
  });

  it("[1.4-UNIT-041][P0] Given StatusMessage, When rendered, Then role=status is present", () => {
    render(<StatusMessage variant="success">Test</StatusMessage>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("[1.4-UNIT-042][P1] Given variant=success, When rendered, Then CheckCircle icon with neon-emerald is displayed", () => {
    const { container } = render(
      <StatusMessage variant="success">OK</StatusMessage>,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg?.closest("[class*='neon-emerald']")).toBeTruthy();
  });

  it("[1.4-UNIT-043][P1] Given variant=error, When rendered, Then XCircle icon is displayed", () => {
    const { container } = render(
      <StatusMessage variant="error">Fail</StatusMessage>,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("[1.4-UNIT-044][P2] Given variant=warning, When rendered, Then AlertTriangle icon is displayed", () => {
    const { container } = render(
      <StatusMessage variant="warning">Warn</StatusMessage>,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("[1.4-UNIT-045][P2] Given variant=info, When rendered, Then Info icon is displayed", () => {
    const { container } = render(
      <StatusMessage variant="info">Info</StatusMessage>,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("[1.4-UNIT-046][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <StatusMessage variant="success" className="extra">
        Test
      </StatusMessage>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("extra");
  });

  it("[1.4-UNIT-047][P1] Given StatusMessage, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(
      <StatusMessage variant="success">Accessible</StatusMessage>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
