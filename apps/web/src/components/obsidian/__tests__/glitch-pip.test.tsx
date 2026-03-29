import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { GlitchPip } from "../glitch-pip";

describe("[1.4-AC1][GlitchPip] — 4x4px micro-indicator component", () => {
  it("[1.4-UNIT-016][P0] Given GlitchPip, When rendered, Then it has size-1 class (4x4px)", () => {
    const { container } = render(<GlitchPip active={true} />);
    const pip = container.firstChild as HTMLElement;
    expect(pip.className).toContain("size-1");
  });

  it("[1.4-UNIT-017][P0] Given active prop toggle, When rerendered, Then animation class toggles", () => {
    const { container, rerender } = render(<GlitchPip active={false} />);
    let pip = container.firstChild as HTMLElement;
    expect(pip.className).not.toContain("animate-glitch-pip");
    expect(pip.className).toContain("bg-muted");

    rerender(<GlitchPip active={true} />);
    pip = container.firstChild as HTMLElement;
    expect(pip.className).toContain("animate-glitch-pip");
    expect(pip.className).toContain("bg-neon-crimson");
  });

  it("[1.4-UNIT-018][P1] Given reducedMotion=true and active, When rendered, Then static crimson dot", () => {
    const { container } = render(
      <GlitchPip active={true} reducedMotion={true} />,
    );
    const pip = container.firstChild as HTMLElement;
    expect(pip.className).not.toContain("animate-glitch-pip");
    expect(pip.className).toContain("bg-neon-crimson");
  });

  it("[1.4-UNIT-019][P1] Given active GlitchPip, When rendered, Then aria-hidden=true is set", () => {
    const { container } = render(<GlitchPip active={true} />);
    const pip = container.firstChild as HTMLElement;
    expect(pip.getAttribute("aria-hidden")).toBe("true");
  });

  it("[1.4-UNIT-020][P2] Given inactive GlitchPip, When rendered, Then aria-hidden=true is set", () => {
    const { container } = render(<GlitchPip active={false} />);
    const pip = container.firstChild as HTMLElement;
    expect(pip.getAttribute("aria-hidden")).toBe("true");
  });

  it("[1.4-UNIT-021][P2] Given inactive with reducedMotion, When rendered, Then muted dot without crimson", () => {
    const { container } = render(
      <GlitchPip active={false} reducedMotion={true} />,
    );
    const pip = container.firstChild as HTMLElement;
    expect(pip.className).toContain("bg-muted");
    expect(pip.className).not.toContain("bg-neon-crimson");
  });

  it("[1.4-UNIT-021b][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <GlitchPip active={true} className="custom" />,
    );
    const pip = container.firstChild as HTMLElement;
    expect(pip.className).toContain("custom");
  });

  it("[1.4-UNIT-022][P1] Given GlitchPip component, When audited, Then no WCAG violations", async () => {
    const { container } = render(<GlitchPip active={true} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
