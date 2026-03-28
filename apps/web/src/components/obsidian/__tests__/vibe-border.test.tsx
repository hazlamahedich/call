import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VibeBorder } from "../vibe-border";

describe("VibeBorder", () => {
  it("applies correct CSS class per sentiment state", () => {
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

  it("has aria-live=polite for sentiment changes", () => {
    const { container } = render(
      <VibeBorder sentiment="neutral">Content</VibeBorder>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-live")).toBe("polite");
  });

  it("updates ARIA label when sentiment changes", () => {
    const { container, rerender } = render(
      <VibeBorder sentiment="neutral">Content</VibeBorder>,
    );
    let el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-label")).toBe("Sentiment: neutral");

    rerender(<VibeBorder sentiment="hostile">Content</VibeBorder>);
    el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-label")).toBe("Sentiment: hostile");
  });

  it("renders static styling when reducedMotion is true", () => {
    const { container } = render(
      <VibeBorder sentiment="hostile" reducedMotion={true}>
        Content
      </VibeBorder>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).not.toContain("animate-jitter-crimson");
    expect(el.className).toContain("border-neon-crimson");
  });
});
