import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { axe } from "vitest-axe";
import { CockpitContainer } from "../cockpit-container";

describe("[1.4-AC4][CockpitContainer] — Glassmorphism boot container", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("[1.4-UNIT-001][P0] Given active=false, When rendered, Then boot animation is NOT applied", () => {
    const onBootComplete = vi.fn();
    const { container } = render(
      <CockpitContainer active={false} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("animate-boot-glow");
    expect(onBootComplete).not.toHaveBeenCalled();
  });

  it("[1.4-UNIT-002][P0] Given active prop changes to true, When 300ms elapses, Then boot animation triggers and onBootComplete fires", () => {
    const onBootComplete = vi.fn();
    const { rerender } = render(
      <CockpitContainer active={false} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    rerender(
      <CockpitContainer active={true} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(onBootComplete).toHaveBeenCalledOnce();
  });

  it("[1.4-UNIT-003][P1] Given glassmorphism styling, When rendered, Then bg-card/40 and backdrop-blur-md classes are applied", () => {
    const { container } = render(
      <CockpitContainer>
        <div>Content</div>
      </CockpitContainer>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("bg-card/40");
    expect(wrapper.className).toContain("backdrop-blur-md");
  });

  it("[1.4-UNIT-004][P1] Given reducedMotion=true, When rendered with active=true, Then boot animation is NOT applied", () => {
    const { container } = render(
      <CockpitContainer active={true} reducedMotion={true}>
        <div>Content</div>
      </CockpitContainer>,
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("animate-boot-glow");
  });

  it("[1.4-UNIT-005][P1] Given children, When rendered, Then children are visible", () => {
    render(
      <CockpitContainer>
        <div>Child content</div>
      </CockpitContainer>,
    );
    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("[1.4-UNIT-006][P1] Given grid overlay, When rendered, Then pointer-events-none linear-gradient background is applied", () => {
    const { container } = render(
      <CockpitContainer>
        <div>Content</div>
      </CockpitContainer>,
    );

    const overlay = container.querySelector('[class*="pointer-events-none"]');
    expect(overlay).toBeInTheDocument();
    expect(overlay?.getAttribute("style")).toContain("linear-gradient");
    expect(overlay?.getAttribute("style")).toContain("background-size");
  });

  it("[1.4-UNIT-007][P0] Given already booted, When rerendered with active=true, Then onBootComplete is NOT called again", () => {
    const onBootComplete = vi.fn();
    const { rerender } = render(
      <CockpitContainer active={true} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(onBootComplete).toHaveBeenCalledTimes(1);

    rerender(
      <CockpitContainer active={true} onBootComplete={onBootComplete}>
        <div>Content</div>
      </CockpitContainer>,
    );

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(onBootComplete).toHaveBeenCalledTimes(1);
  });

  it("[1.4-UNIT-008][P2] Given custom className, When rendered, Then className is merged", () => {
    const { container } = render(
      <CockpitContainer className="extra">
        <div>Content</div>
      </CockpitContainer>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("extra");
  });

  it("[1.4-UNIT-009][P1] Given CockpitContainer, When axe audit runs, Then no WCAG violations", async () => {
    vi.useRealTimers();
    const { container } = render(
      <CockpitContainer>
        <div>Accessible content</div>
      </CockpitContainer>,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
