import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { GlitchPip } from "../glitch-pip";

describe("GlitchPip", () => {
  it("renders as 4x4px (size-1) element", () => {
    const { container } = render(<GlitchPip active={true} />);
    const pip = container.firstChild as HTMLElement;
    expect(pip.className).toContain("size-1");
  });

  it("toggles animation class based on active prop", () => {
    const { container, rerender } = render(<GlitchPip active={false} />);
    let pip = container.firstChild as HTMLElement;
    expect(pip.className).not.toContain("animate-glitch-pip");
    expect(pip.className).toContain("bg-muted");

    rerender(<GlitchPip active={true} />);
    pip = container.firstChild as HTMLElement;
    expect(pip.className).toContain("animate-glitch-pip");
    expect(pip.className).toContain("bg-neon-crimson");
  });

  it("renders static crimson dot when reducedMotion is true and active", () => {
    const { container } = render(
      <GlitchPip active={true} reducedMotion={true} />,
    );
    const pip = container.firstChild as HTMLElement;
    expect(pip.className).not.toContain("animate-glitch-pip");
    expect(pip.className).toContain("bg-neon-crimson");
  });
});
