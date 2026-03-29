import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import { VibeBorder } from "../vibe-border";

describe("[1.4-AC1][VibeBorder] — Sentiment-reactive border component", () => {
  it("[1.4-UNIT-022][P0] Given each sentiment state, When rendered, Then correct CSS class is applied", () => {
    const { rerender, container } = render(
      <VibeBorder sentiment="neutral">Content</VibeBorder>,
    );
    let el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-zinc-700");

    rerender(<VibeBorder sentiment="positive">Content</VibeBorder>);
    el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-neon-emerald");
    expect(el.className).toContain("animate-pulse-emerald");

    rerender(<VibeBorder sentiment="hostile">Content</VibeBorder>);
    el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-neon-crimson");
    expect(el.className).toContain("animate-jitter-crimson");
  });

  it("[1.4-UNIT-023][P0] Given VibeBorder, When rendered, Then aria-live=polite is present", () => {
    const { container } = render(
      <VibeBorder sentiment="neutral">Content</VibeBorder>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-live")).toBe("polite");
  });

  it("[1.4-UNIT-024][P0] Given sentiment change, When rerendered, Then ARIA label updates", () => {
    const { container, rerender } = render(
      <VibeBorder sentiment="neutral">Content</VibeBorder>,
    );
    let el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-label")).toBe("Sentiment: neutral");

    rerender(<VibeBorder sentiment="hostile">Content</VibeBorder>);
    el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-label")).toBe("Sentiment: hostile");
  });

  it("[1.4-UNIT-025][P1] Given reducedMotion=true and hostile, When rendered, Then no animation class", () => {
    const { container } = render(
      <VibeBorder sentiment="hostile" reducedMotion={true}>
        Content
      </VibeBorder>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).not.toContain("animate-jitter-crimson");
    expect(el.className).toContain("border-neon-crimson");
  });

  it("[1.4-UNIT-026][P2] Given children, When rendered, Then children appear inside border", () => {
    render(<VibeBorder sentiment="neutral">Inner content</VibeBorder>);
    expect(screen.getByText("Inner content")).toBeInTheDocument();
  });

  it("[1.4-UNIT-027][P2] Given VibeBorder, When rendered, Then rounded-lg and transition classes are applied", () => {
    const { container } = render(
      <VibeBorder sentiment="neutral">Content</VibeBorder>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("rounded-lg");
    expect(el.className).toContain("transition-colors");
  });

  it("[1.4-UNIT-028][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <VibeBorder sentiment="neutral" className="extra">
        Content
      </VibeBorder>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("extra");
  });

  it("[1.4-UNIT-029][P1] Given VibeBorder component, When audited, Then no WCAG violations", async () => {
    const { container } = render(
      <VibeBorder sentiment="neutral">Accessible</VibeBorder>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
