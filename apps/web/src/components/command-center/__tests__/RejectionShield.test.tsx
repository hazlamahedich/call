import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { RejectionShield } from "../RejectionShield";

describe("[1.4-AC1][RejectionShield] — Rejection rate dashboard card with design system primitives", () => {
  it("[1.4-UNIT-121][P0] Given RejectionShield, When rendered, Then Rejection Shield heading is displayed", () => {
    render(<RejectionShield />);
    expect(screen.getByText("Rejection Shield")).toBeInTheDocument();
  });

  it("[1.4-UNIT-122][P1] Given default props, When rendered, Then default rejection rate 12.4% is shown", () => {
    render(<RejectionShield />);
    expect(screen.getByText("12.4%")).toBeInTheDocument();
  });

  it("[1.4-UNIT-123][P1] Given rejectionRate=24.8, When rendered, Then 24.8% is displayed", () => {
    render(<RejectionShield rejectionRate={24.8} />);
    expect(screen.getByText("24.8%")).toBeInTheDocument();
  });

  it("[1.4-UNIT-124][P1] Given RejectionShield, When rendered, Then stats are displayed", () => {
    render(<RejectionShield />);
    expect(screen.getByText("Active Calls")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("8.2%")).toBeInTheDocument();
    expect(screen.getByText("DECENT")).toBeInTheDocument();
  });

  it("[1.4-UNIT-125][P1] Given status=safe, When rendered, Then ShieldCheck icon area uses emerald styling", () => {
    const { container } = render(<RejectionShield status="safe" />);
    const statusArea = container.querySelector(".text-neon-emerald");
    expect(statusArea).toBeInTheDocument();
  });

  it("[1.4-UNIT-126][P1] Given status=alert, When rendered, Then blue styling is applied", () => {
    const { container } = render(<RejectionShield status="alert" />);
    const statusArea = container.querySelector(".text-neon-blue");
    expect(statusArea).toBeInTheDocument();
  });

  it("[1.4-UNIT-127][P1] Given status=critical, When rendered, Then crimson styling is applied", () => {
    const { container } = render(<RejectionShield status="critical" />);
    const statusArea = container.querySelector(".text-neon-crimson");
    expect(statusArea).toBeInTheDocument();
  });

  it("[1.4-UNIT-128][P1] Given RejectionShield, When rendered, Then Shield Optimization section is shown", () => {
    render(<RejectionShield />);
    expect(screen.getByText("Shield Optimization")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("[1.4-UNIT-129][P2] Given RejectionShield uses design system, When rendered, Then Card component wraps content", () => {
    const { container } = render(<RejectionShield />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("bg-card");
  });

  it("[1.4-UNIT-130][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(<RejectionShield className="custom-shield" />);
    expect((container.firstChild as HTMLElement).className).toContain(
      "custom-shield",
    );
  });

  it("[1.4-UNIT-131][P1] Given RejectionShield, When axe audit runs, Then no WCAG violations", async () => {
    const { container } = render(<RejectionShield />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
