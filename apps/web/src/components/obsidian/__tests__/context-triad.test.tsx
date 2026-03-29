import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { ContextTriad } from "../context-triad";

describe("[1.4-AC1][ContextTriad] — Tactical briefing component", () => {
  it("[1.4-UNIT-030][P0] Given why/mood/target props, When rendered, Then ALL-CAPS labels with values appear", () => {
    render(
      <ContextTriad
        why="Solar prospect"
        mood="Engaged"
        target="Mr. Henderson"
      />,
    );

    expect(screen.getByText("WHY:")).toBeInTheDocument();
    expect(screen.getByText("MOOD:")).toBeInTheDocument();
    expect(screen.getByText("TARGET:")).toBeInTheDocument();

    expect(screen.getByText("Solar prospect")).toBeInTheDocument();
    expect(screen.getByText("Engaged")).toBeInTheDocument();
    expect(screen.getByText("Mr. Henderson")).toBeInTheDocument();
  });

  it("[1.4-UNIT-031][P1] Given ContextTriad, When rendered, Then mono font and uppercase tracking styling on labels", () => {
    const { container } = render(
      <ContextTriad why="Test" mood="Test" target="Test" />,
    );

    const labels = container.querySelectorAll(".uppercase");
    expect(labels.length).toBe(3);
    labels.forEach((label) => {
      expect(label.className).toContain("font-mono");
      expect(label.className).toContain("text-xs");
      expect(label.className).toContain("tracking-[0.05em]");
    });
  });

  it("[1.4-UNIT-032][P2] Given empty string values, When rendered, Then labels still appear", () => {
    render(<ContextTriad why="" mood="" target="" />);

    expect(screen.getByText("WHY:")).toBeInTheDocument();
    expect(screen.getByText("MOOD:")).toBeInTheDocument();
    expect(screen.getByText("TARGET:")).toBeInTheDocument();
  });

  it("[1.4-UNIT-032b][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <ContextTriad why="A" mood="B" target="C" className="extra-class" />,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("extra-class");
  });

  it("[1.4-UNIT-033][P1] Given ContextTriad component, When audited, Then no WCAG violations", async () => {
    const { container } = render(
      <ContextTriad why="Reason" mood="Happy" target="Lead" />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
